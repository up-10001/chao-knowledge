#!/usr/bin/env python3
"""Explicit, budgeted TikHub collection; kb.py remains an offline record engine."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
from decimal import Decimal, InvalidOperation
import getpass
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import time


def sibling(name):
    spec = importlib.util.spec_from_file_location("chao_" + name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


kb = sibling("kb")
api = sibling("tikhub")
Error = api.CollectionError
JOB_LIMIT = 16 * 1024 * 1024
STORAGE_LIMIT = 64 * 1024 * 1024


def encode(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def sha(obj):
    return hashlib.sha256(encode(obj)).hexdigest()


def money(value, positive=False):
    if len(str(value)) > 40: raise Error("金额过长")
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise Error("金额必须是有限的十进制数字") from None
    if not amount.is_finite() or amount < 0 or amount > 1000000 or amount.as_tuple().exponent < -8 or (positive and amount == 0):
        raise Error("金额必须非负，接口单价必须大于零")
    return amount


def read_json(path):
    if not path.is_file() or path.stat().st_size > JOB_LIMIT or path.stat().st_nlink != 1:
        raise Error("采集记录缺失、过大或不是独立普通文件")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=kb.strict_pairs, parse_constant=kb.invalid_constant)


def root_for(value):
    root = kb.root_path(value)
    kb.load(root)  # Require an initialized, user-selected KB; never create one implicitly.
    return root


def job_paths(root, job_id):
    if not re.fullmatch(r"c-[a-f0-9]{20}", job_id): raise Error("采集任务编号无效")
    directory = kb.inside(root, ".chao/collection/" + job_id)
    return directory, kb.inside(root, "00-收件箱/采集-" + job_id[2:])


def save_job(directory, job):
    data = encode(job)
    if len(data) > JOB_LIMIT: raise Error("任务记录超过上限，请分批采集；不会继续请求")
    kb._atomic(directory / "state.json", data)


def load_job(root, job_id):
    directory, output = job_paths(root, job_id)
    job = read_json(kb.inside(root, (directory / "state.json").relative_to(root).as_posix()))
    if job.get("format") != 1 or job.get("plan_hash") != sha(job.get("plan")) or job_id != "c-" + job["plan_hash"][:20]:
        raise Error("采集计划发生变化；停止，不使用旧授权")
    return directory, output, job


def validate_price(plan):
    if plan["unit_price_usd"] is None: raise Error("尚无已核对单价；先查价并重新生成费用计划")
    money(plan["unit_price_usd"], True)
    checked = dt.datetime.fromisoformat(plan["price_checked_at"])
    if checked.tzinfo is None: raise Error("价格查询时间必须带时区")
    age = (dt.datetime.now(dt.timezone.utc) - checked).total_seconds()
    if not -300 <= age <= 86400: raise Error("单价超过 24 小时或时间异常；先重新查价")


def create_plan(root, preset, targets, max_pages=1, max_items=100, max_requests=None,
                unit_price=None, budget="0", price_source=None, price_checked_at=None,
                endpoint=None, params=None, source_url=None):
    if preset not in api.ROUTES and endpoint is None: raise Error("暂不支持此模式")
    if not 1 <= max_pages <= 50 or not 1 <= max_items <= 1000: raise Error("页数为 1–50，单对象条数为 1–1000")
    route = api.raw_route(endpoint) if endpoint else api.ROUTES[preset]
    if endpoint:
        if not source_url: raise Error("通用接口采集必须提供原对象的公开来源链接")
        source = api.public_url(source_url)
        items = [{"params": api.validate_params(endpoint, params), "source_url": source}]
        targets = []
    else:
        if not targets or len(targets) > 100: raise Error("每批提供 1–100 个明确对象")
        items = []
    if not route["cursor"] and max_pages != 1: raise Error("详情和账号模式只接受一页")
    seen = set()
    for target in targets:
        params, source = api.target_params(preset, target)
        identity = sha(params)
        if identity not in seen:
            seen.add(identity)
            items.append({"params": params, "source_url": source})
    nominal = len(items) * max_pages
    cap = max_requests if max_requests is not None else nominal
    if not 1 <= cap <= 500: raise Error("单任务最多 500 次请求；更大任务请分批")
    price = str(money(unit_price, True)) if unit_price is not None else None
    ceiling = str(money(budget))
    if price:
        if not price_source or not price_checked_at: raise Error("单价必须附查询来源与带时区的查询时间")
        price_source = api.public_url(price_source)
    plan = {"preset": preset or "api", "route": route, "endpoint": route["endpoint"], "items": items, "max_pages": max_pages,
            "max_items_per_target": max_items, "max_requests": cap, "unit_price_usd": price,
            "budget_usd": ceiling, "price_source": price_source, "price_checked_at": price_checked_at,
            "estimated_ceiling_usd": str(money(price) * cap) if price else None,
            "contract_checked_at": api.CHECKED_AT, "transcription": "仅接受明确字幕字段；不把简介当逐字稿"}
    if price:
        validate_price(plan)
        if money(plan["estimated_ceiling_usd"]) > money(ceiling): raise Error("请求上限对应的费用预估超过预算，请缩小范围")
    digest = sha(plan)
    job_id = "c-" + digest[:20]
    directory, output = job_paths(root, job_id)
    directory.mkdir(parents=True, exist_ok=True)
    with kb.file_lock(root, (directory / "LOCK").relative_to(root).as_posix(), 2):
        if (directory / "state.json").exists():
            _, _, job = load_job(root, job_id)
        else:
            job = {"format": 1, "id": job_id, "plan": plan, "plan_hash": digest, "created_at": kb.now(),
                   "status": "planned", "attempts": 0, "bytes": 0, "inflight": None,
                   "sample_passed": False, "authorizations": [], "events": [], "exports": {}, "imported": {},
                   "targets": [dict(item, pages=0, records=[], done=False, scope_limited=False, cursors=[]) for item in items]}
            save_job(directory, job)
        return preview(job)


def preview(job):
    return {"job_id": job["id"], "plan_hash": job["plan_hash"], "status": job["status"], "plan": job["plan"],
            "next": "先确认范围与费用，再运行 sample；核对真实样本后再 batch。已有完成记录不会重复请求。",
            "billing": "费用仅为按所提供单价计算的上限预估，所有已发请求均占用预算；实付以 TikHub 账单为准。"}


def csv_cell(value):
    value = "" if value is None else str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r")) else value


def all_records(job):
    result, seen = [], set()
    for target in job["targets"]:
        for row in target["records"]:
            identity = (row["platform"], row["kind"], row["id"])
            if identity not in seen:
                seen.add(identity)
                result.append(row)
    return result


def report(root, directory, output, job):
    records = all_records(job)
    fields = ["platform", "kind", "id", "title", "source_url", "author_name", "collected_at", "reading_status",
              "views", "likes", "comments", "favorites", "shares", "followers", "source_file"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fields)
    writer.writeheader()
    for row in records:
        flattened = dict(row, **row["metrics"])
        writer.writerow({f: csv_cell(flattened.get(f)) for f in fields})
    attempted_cost = str(money(job["plan"]["unit_price_usd"] or "0") * job["attempts"])
    labels = {"completed": "本次范围已完成", "sample_ready": "样本已取回，核对后可继续批量", "needs_review": "已暂停，需核对",
              "uncertain": "请求结果不明，未自动重试", "planned": "计划已准备", "running": "处理中"}
    quantity = "- 接口响应：" + str(len(records)) + " 份（不是作品条数）" if job["plan"]["preset"] == "api" else "- 记录：" + str(len(records)) + " 条"
    lines = ["# 采集报告", "", "- 状态：" + labels.get(job["status"], job["status"]), quantity,
             "- 已发请求：" + str(job["attempts"]) + " 次（包含失败和结果不明请求）",
             "- 已发请求费用预估：" + attempted_cost + " USD；不是实际账单",
             "- 预算：" + job["plan"]["budget_usd"] + " USD", "- 实际费用：未核实，以 TikHub 账单为准",
             "- 视频简介不等于逐字稿；无字幕时仅保存链接和元数据。", "",
             "| 内容 | 来源 | 读取状态 |", "|---|---|---|"]
    for row in records:
        lines.append("| %s | %s | %s |" % (kb.navigation_cell(row["title"]), kb.navigation_link("原始链接", row["source_url"]), row["reading_status"]))
    if any(t["scope_limited"] for t in job["targets"]): lines += ["", "达到本次页数/条数范围；不代表采集了账号全部历史数据。"]
    if job.get("error"): lines += ["", "## 本轮停止原因", "", job["error"]]
    lines += ["", "原始响应保存为脱敏副本，并记录收到字节的 SHA256。原始字段和 AI 分析分开；本脚本不生成调研结论。"]
    files = {"records.json": encode(records), "records.csv": ("\ufeff" + stream.getvalue()).encode("utf-8"),
             "采集报告.md": ("\n".join(lines) + "\n").encode("utf-8")}
    for name, data in files.items():
        path = kb.inside(root, (output / name).relative_to(root).as_posix())
        if path.exists() and kb.digest(path.read_bytes()) != job["exports"].get(name):
            if path.read_bytes() != data: raise Error("导出文件被手工修改，已保留：" + name)
        kb._atomic(path, data)
        job["exports"][name] = kb.digest(data)
    save_job(directory, job)
    return {"job_id": job["id"], "status": job["status"], "records": len(records), "requests_sent": job["attempts"],
            "estimated_attempt_cost_usd": attempted_cost, "actual_cost_usd": None,
            "report": str(output / "采集报告.md"), "error": job.get("error")}


def run(root, job_id, plan_hash, confirmation, phase="sample", key_file=None, request_fn=None):
    if phase not in {"sample", "batch"}: raise Error("采集阶段必须为 sample 或 batch")
    directory, output, job = load_job(root, job_id)
    with kb.file_lock(root, (directory / "LOCK").relative_to(root).as_posix(), 2):
        directory, output, job = load_job(root, job_id)
        if plan_hash != job["plan_hash"]: raise Error("执行的计划与已展示计划不同")
        if job["status"] == "completed": return report(root, directory, output, job)
        if job["status"] in {"needs_review", "uncertain"}:
            return report(root, directory, output, job)
        kb.check_text(confirmation, "采集范围和费用授权原话", 1000)
        validate_price(job["plan"])
        current_route = api.raw_route(job["plan"]["endpoint"]) if job["plan"]["preset"] == "api" else api.ROUTES[job["plan"]["preset"]]
        if current_route != job["plan"]["route"]: raise Error("端点契约已经改变；请重新预览计划")
        if phase == "batch" and not job["sample_passed"]: raise Error("先采样并核对结果，再运行批量")
        if phase == "sample" and job["sample_passed"]: return report(root, directory, output, job)
        key, _ = api.resolve_key(kb, key_file)
        send = request_fn or api.request
        job["authorizations"].append({"phase": phase, "quote": api.redact(confirmation, key), "at": kb.now()})
        job["status"] = "running"
        save_job(directory, job)
        completed_this_run = 0
        route = job["plan"]["route"]
        while True:
            target_index = next((i for i, t in enumerate(job["targets"]) if not t["done"]), None)
            if target_index is None:
                job["status"] = "completed"
                break
            target = job["targets"][target_index]
            if not job["inflight"]:
                next_cost = money(job["plan"]["unit_price_usd"]) * (job["attempts"] + 1)
                if job["attempts"] >= job["plan"]["max_requests"] or next_cost > money(job["plan"]["budget_usd"]):
                    job.update(status="needs_review", error="达到已确认请求或费用上限；不会继续扣费")
                    break
                if job["bytes"] + api.MAX_RESPONSE > STORAGE_LIMIT:
                    job.update(status="needs_review", error="达到本批证据存储上限，请分批处理")
                    break
                job["attempts"] += 1
                request_id = "request-%04d" % job["attempts"]
                job["inflight"] = {"id": request_id, "target": target_index, "params": dict(target["params"]),
                                   "request_hash": sha({"endpoint": route["endpoint"], "params": target["params"]}),
                                   "at": kb.now(), "dispatched": False}
                save_job(directory, job)
            active = job["inflight"]
            receipt_path = kb.inside(root, (output / "raw" / (active["id"] + ".json")).relative_to(root).as_posix())
            try:
                if receipt_path.exists():
                    receipt = read_json(receipt_path)
                    if receipt.get("request_hash") != active["request_hash"] or kb.digest(receipt_path.read_bytes()) != active.get("receipt_sha256"):
                        raise Error("断点响应与请求不匹配或已被修改")
                elif active["dispatched"]:
                    job.update(status="uncertain", error="上次请求可能已发出但没有可恢复响应；请先核对账单或显式处理断点")
                    break
                else:
                    active["dispatched"] = True
                    save_job(directory, job)  # Persist the reservation BEFORE the external request.
                    response = send(route["endpoint"], active["params"], key)
                    receipt = dict(response, request_hash=active["request_hash"], endpoint=route["endpoint"],
                                   method=route["method"], received_at=kb.now())
                    # Defense in depth for provider echoes, including custom transports.
                    receipt = api.redact(receipt, key)
                    receipt["redacted"] = True
                    active["receipt_sha256"] = kb.digest(encode(receipt))
                    save_job(directory, job)
                    kb._atomic(receipt_path, encode(receipt))
                rows, more, continuation = api.page(receipt["payload"], route, target["source_url"], receipt["received_at"])
                cursor_key = sha(continuation) if continuation else None
                if more and (cursor_key in target["cursors"] or all(target["params"].get(k) == v for k, v in continuation.items())):
                    raise api.ProviderError("分页游标重复，停止，避免循环扣费")
                old_ids = {r["id"] for r in target["records"]}
                fresh = []
                for row in rows:
                    if row["id"] not in old_ids:
                        fresh.append(row)
                        old_ids.add(row["id"])
                if more and rows and not fresh: raise api.ProviderError("翻页未返回新记录，停止重复采集")
                room = job["plan"]["max_items_per_target"] - len(target["records"])
                for row in fresh[:room]:
                    row["source_file"] = receipt_path.relative_to(root).as_posix()
                    row["response_sha256"] = kb.digest(receipt_path.read_bytes())
                    target["records"].append(row)
                target["pages"] += 1
                target["scope_limited"] = len(fresh) > room or (more and (target["pages"] >= job["plan"]["max_pages"] or len(target["records"]) >= job["plan"]["max_items_per_target"]))
                target["done"] = not more or target["scope_limited"]
                target["params"].update(continuation)
                if cursor_key: target["cursors"].append(cursor_key)
                job["bytes"] += receipt["bytes"]
                job["events"].append({"request": active["id"], "status": "received", "records": len(rows)})
                job["inflight"] = None
                job["sample_passed"] = True
                job.pop("error", None)
                completed_this_run += 1
                save_job(directory, job)
            except api.AmbiguousRequest as exc:
                job.update(status="uncertain", error=str(exc))
                break
            except (api.ProviderError, Error, OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
                job.update(status="needs_review", error=api.redact(str(exc), key))
                break
            if phase == "sample" and completed_this_run >= 1:
                job["status"] = "completed" if all(t["done"] for t in job["targets"]) else "sample_ready"
                break
            time.sleep(0.2)
        save_job(directory, job)
        return report(root, directory, output, job)


def retry(root, job_id, confirmation):
    directory, _, job = load_job(root, job_id)
    with kb.file_lock(root, (directory / "LOCK").relative_to(root).as_posix(), 2):
        directory, _, job = load_job(root, job_id)
        kb.check_text(confirmation, "结果不明或失败请求的重试授权", 1000)
        if job["status"] not in {"uncertain", "needs_review"}: raise Error("当前任务不需要重试")
        if job["attempts"] >= job["plan"]["max_requests"]: raise Error("原请求预算已用完；需明确的新计划，不能重置已发请求计数")
        job["events"].append({"status": "retry_authorized", "quote": confirmation, "at": kb.now(),
                              "previous_request": job["inflight"]})
        job.update(inflight=None, status="sample_ready" if job["sample_passed"] else "planned")
        job.pop("error", None)
        save_job(directory, job)
        return preview(job)


def import_records(root, job_id, confirmation):
    directory, output, job = load_job(root, job_id)
    with kb.file_lock(root, (directory / "LOCK").relative_to(root).as_posix(), 2):
        directory, output, job = load_job(root, job_id)
        kb.check_text(confirmation, "将已采集资料归档的授权原话", 1000)
        if job["plan"]["preset"] == "api":
            raise Error("通用接口响应先由宿主核对真实字段与正文，再通过 kb.py 归档；不能把接口 JSON 当正文")
        imported = []
        for row in all_records(job):
            record_key = row["platform"] + ":" + row["kind"] + ":" + row["id"]
            if record_key in job["imported"]:
                imported.append(job["imported"][record_key])
                continue
            receipt = kb.inside(root, row["source_file"])
            if not receipt.is_file() or kb.digest(receipt.read_bytes()) != row["response_sha256"]:
                raise Error("原始响应证据发生变化，停止入库")
            title = row["title"][:150] or "采集内容"
            collection = "用户反馈" if row["kind"] == "comments" else "对标内容"
            args = ["ingest", "--title", title, "--collection", collection, "--provenance", "external",
                    "--source-url", row["source_url"], "--tag", "TikHub采集"]
            if row["author_name"]: args += ["--author", row["author_name"]]
            content = row["transcript"] or (row["body"] if row["body_kind"] in {"note_text", "comment", "account_profile"} else "")
            body_path = kb.inside(root, (output / "readable" / (sha(record_key)[:20] + ".txt")).relative_to(root).as_posix())
            if row["kind"] == "comments" or row["kind"] == "account":
                content = "来源：" + row["source_url"] + "\n采集时间：" + row["collected_at"] + "\n类型：" + row["body_kind"] + "\n\n" + content
                kb._atomic(body_path, content)
                args += ["--file", str(body_path)]
            else:
                args += ["--url", row["source_url"]]
            result = kb.execute(kb.build_parser().parse_args(["--root", str(root), *args]))
            material = result["material"]
            if material["provenance"] != "external": raise Error("已有资料归属不同，保留原记录，请核对后再处理")
            if content and row["kind"] not in ("comments", "account"):
                kb._atomic(body_path, content)
                if material["text_path"]:
                    if material["text_sha256"] != kb.digest(content.encode("utf-8")):
                        raise Error("已有正文不同，未覆盖；请按资料新版本流程确认保存")
                else:
                    kb.execute(kb.build_parser().parse_args(["--root", str(root), "extract", "--id", material["id"],
                        "--file", str(body_path), "--method", "TikHub 字幕字段" if row["transcript"] else "TikHub 返回文本，未核实完整性"]))
            job["imported"][record_key] = {"title": title, "material_id": material["id"], "source_url": row["source_url"]}
            imported.append(job["imported"][record_key])
            save_job(directory, job)
        return {"status": "imported", "materials": imported, "collection_status": job["status"],
                "scope_complete": job["status"] == "completed", "collection_error": job.get("error"),
                "note": "外部归属保留；无字幕视频只存链接，不冒充逐字稿。部分结果归档不代表全部采集完成。"}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", help="已初始化的当前知识库，不能是 Skill 源码或安装目录")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("routes", help="查看已实现适配器及官方端点")
    c.add_argument("--platform"); c.add_argument("--match", default="")
    c = sub.add_parser("configure"); c.add_argument("--key-file"); c.add_argument("--stdin", action="store_true"); c.add_argument("--replace", action="store_true")
    c = sub.add_parser("check-config"); c.add_argument("--key-file")
    c = sub.add_parser("quote")
    g = c.add_mutually_exclusive_group(required=True); g.add_argument("--preset", choices=api.ROUTES); g.add_argument("--endpoint")
    c.add_argument("--requests", type=int, required=True); c.add_argument("--key-file")
    c = sub.add_parser("plan")
    g = c.add_mutually_exclusive_group(required=True); g.add_argument("--preset", choices=api.ROUTES); g.add_argument("--endpoint")
    c.add_argument("--params-file"); c.add_argument("--source-url"); c.add_argument("--target", action="append", default=[])
    c.add_argument("--targets-file"); c.add_argument("--max-pages", type=int, default=1); c.add_argument("--max-items", type=int, default=100)
    c.add_argument("--max-requests", type=int); c.add_argument("--unit-price"); c.add_argument("--budget", default="0"); c.add_argument("--price-source"); c.add_argument("--price-checked-at")
    for name in ("run", "status", "retry", "import"):
        c = sub.add_parser(name); c.add_argument("--job", required=True)
        if name != "status": c.add_argument("--confirm", required=True)
        if name == "run":
            c.add_argument("--plan-hash", required=True); c.add_argument("--phase", choices=["sample", "batch"], default="sample"); c.add_argument("--key-file")
    return p


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == "routes":
            result = {"provider": "TikHub", "routes": api.ROUTES, "contract_checked_at": api.CHECKED_AT,
                      "validation": "文档契约适配；实际账号/付费请求以用户小样本验证为准"}
            if args.platform:
                result["read_only_api_catalog"] = {path: data for path, data in api.catalog()["endpoints"].items()
                    if data["platform"] == args.platform and args.match.lower() in path.lower()}
                result["catalog_source"] = api.catalog()["source"]
        elif args.command == "configure":
            path = kb.no_symlinks(Path(args.key_file).expanduser() if args.key_file else api.key_path())
            skill = Path(__file__).resolve().parents[1]
            if path == skill or skill in path.parents or any(part in {".chao", "00-收件箱", "02-资料库"} for part in path.parts):
                raise Error("Key 保存在知识库和 Skill 发行目录之外，更新时才能保留且不会被资料检索")
            if path.exists() and not args.replace: raise Error("Key 文件已存在；确认更换后才使用 --replace")
            value = (sys.stdin.read(4097) if args.stdin else getpass.getpass("TikHub Key: ")).strip()
            if not value or len(value) > 4096 or re.search(r"\s", value): raise Error("Key 格式无效")
            kb._atomic(path, value + "\n")
            result = {"configured": True, "path": str(path), "network_requests": 0}
        elif args.command == "check-config":
            _, source = api.resolve_key(kb, args.key_file)
            result = {"configured": True, "source": source, "network_requests": 0}
        elif args.command == "quote":
            if not 1 <= args.requests <= 500: raise Error("请求数必须为 1–500")
            key, _ = api.resolve_key(kb, args.key_file)
            route = api.raw_route(args.endpoint) if args.endpoint else api.ROUTES[args.preset]
            result = api.request("/api/v1/tikhub/user/calculate_price",
                {"endpoint": route["endpoint"], "request_per_day": args.requests}, key)
            result.update(price_source=api.API + "/api/v1/tikhub/user/calculate_price", price_checked_at=kb.now(),
                          note="请核对返回的基础单价，不把折扣预测当实际账单", api_calls=1)
        else:
            if not args.root: raise Error("请指定当前已初始化知识库 --root")
            root = root_for(args.root)
            if args.command == "plan":
                targets = list(args.target)
                if args.targets_file:
                    _, data = kb.input_file(root, args.targets_file)
                    targets += [line.strip() for line in kb.decode(data).splitlines() if line.strip()]
                params = None
                if args.endpoint:
                    if not args.params_file: raise Error("通用接口计划需要 --params-file")
                    _, data = kb.input_file(root, args.params_file)
                    params = json.loads(kb.decode(data), object_pairs_hook=kb.strict_pairs, parse_constant=kb.invalid_constant)
                result = create_plan(root, args.preset, targets, args.max_pages, args.max_items, args.max_requests,
                                     args.unit_price, args.budget, args.price_source, args.price_checked_at,
                                     args.endpoint, params, args.source_url)
            elif args.command == "run": result = run(root, args.job, args.plan_hash, args.confirm, args.phase, args.key_file)
            elif args.command == "retry": result = retry(root, args.job, args.confirm)
            elif args.command == "import": result = import_records(root, args.job, args.confirm)
            else:
                directory, output, job = load_job(root, args.job)
                result = dict(preview(job), requests_sent=job["attempts"], records=len(all_records(job)), error=job.get("error"))
        ok = result.get("status") not in {"needs_review", "uncertain"}
        print(json.dumps({"ok": ok, "result": result}, ensure_ascii=False, allow_nan=False, indent=2))
        return 0 if ok else 2
    except (Error, kb.KBError, OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
