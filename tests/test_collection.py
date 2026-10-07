"""Synthetic provider tests. No real credentials, paid requests, or client UI."""
import contextlib
import copy
import datetime as dt
import io
import json
import os
from pathlib import Path
from unittest.mock import patch
import urllib.error

from test_kb import WorkspaceCase, SCRIPT, REPO, module

c = module("collector_tests", SCRIPT.with_name("collect.py"))
KEY = "synthetic-test-key-never-real"


def video(vid="123456789", desc="合成视频简介", **more):
    return dict(aweme_id=vid, desc=desc, author={"nickname": "外部作者"},
                statistics={"digg_count": 0, "comment_count": 7}, **more)


def response(payload):
    raw = json.dumps(payload).encode()
    return {"payload": payload, "wire_sha256": c.kb.digest(raw), "bytes": len(raw), "redacted": False}


class CollectionTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.init()
        self.key = patch.dict(os.environ, {"TIKHUB_API_KEY": KEY})
        self.key.start()
        self.addCleanup(self.key.stop)
        self.sleep = patch.object(c.time, "sleep")
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def plan(self, preset="douyin-video", targets=None, **options):
        defaults = dict(unit_price="0.01", budget="1", price_source="https://docs.tikhub.io/",
                        price_checked_at=c.kb.now())
        defaults.update(options)
        return c.create_plan(self.root, preset, targets or ["https://www.douyin.com/video/123456789"], **defaults)

    def run_plan(self, plan, payloads, phase="sample"):
        calls = []
        def send(endpoint, params, key):
            calls.append((endpoint, copy.deepcopy(params)))
            self.assertEqual(key, KEY)
            item = payloads[len(calls)-1]
            if isinstance(item, Exception): raise item
            return response(item)
        result = c.run(self.root, plan["job_id"], plan["plan_hash"], "确认本次范围及预算", phase, request_fn=send)
        return result, calls

    def job(self, plan):
        return c.load_job(self.root, plan["job_id"])[2]

    def test_plan_is_offline_and_reuses_identical_job(self):
        with patch.object(c.api, "request", side_effect=AssertionError("network")):
            planned = self.plan(targets=["123456789", "123456789"])
            again = self.plan(targets=["123456789", "123456789"],
                              price_checked_at=planned["plan"]["price_checked_at"])
        self.assertEqual(planned["job_id"], again["job_id"])
        self.assertEqual(len(planned["plan"]["items"]), 1)
        self.assertEqual(self.job(planned)["attempts"], 0)

    def test_batch_requires_real_sample_and_reviewed_plan_hash(self):
        p = self.plan(preset="douyin-posts", targets=["MS4Example"], max_pages=2)
        with self.assertRaisesRegex(c.Error, "先采样"):
            self.run_plan(p, [], "batch")
        with self.assertRaisesRegex(c.Error, "计划"):
            c.run(self.root, p["job_id"], "different", "确认", request_fn=lambda *_: self.fail("network"))
        self.assertEqual(self.job(p)["attempts"], 0)

    def test_unknown_or_stale_price_stops_before_request(self):
        p = self.plan(unit_price=None, price_source=None, price_checked_at=None)
        with self.assertRaisesRegex(c.Error, "单价"): self.run_plan(p, [])
        with self.assertRaisesRegex(c.Error, "超过 24"):
            self.plan(price_checked_at="2020-01-01T00:00:00+00:00")
        with self.assertRaises(c.Error): self.plan(unit_price="NaN")
        with self.assertRaises(c.Error): self.plan(budget="0.001")

    def test_sample_batch_pagination_deduplication_and_done_replay(self):
        p = self.plan(preset="douyin-posts", targets=["MS4Example"], max_pages=2)
        first = {"code": 200, "data": {"aweme_list": [video("111"), video("111")], "has_more": 1, "max_cursor": 10}}
        result, calls = self.run_plan(p, [first])
        self.assertEqual(result["status"], "sample_ready")
        self.assertEqual(result["records"], 1)
        second = {"code": 200, "data": {"aweme_list": [video("111"), video("222")], "has_more": 0, "max_cursor": 20}}
        result, calls = self.run_plan(p, [second], "batch")
        self.assertEqual(calls[0][1]["max_cursor"], 10)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["records"], 2)
        result, calls = self.run_plan(p, [], "batch")
        self.assertEqual(calls, [])
        self.assertEqual(result["requests_sent"], 2)

    def test_page_limit_is_reported_as_scope_limit_not_all_history(self):
        p = self.plan(preset="douyin-posts", targets=["MS4Example"], max_pages=1)
        result, _ = self.run_plan(p, [{"code": 200, "data": {"aweme_list": [video()], "has_more": 1, "max_cursor": 20}}])
        self.assertEqual(result["status"], "completed")
        self.assertIn("不代表采集了账号全部", Path(result["report"]).read_text(encoding="utf-8"))

    def test_request_budget_cannot_be_reset_by_retry(self):
        p = self.plan()
        result, calls = self.run_plan(p, [c.api.ProviderError("TikHub HTTP 402")])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["requests_sent"], 1)
        self.assertEqual(result["estimated_attempt_cost_usd"], "0.01")
        self.assertIsNone(result["actual_cost_usd"])
        with self.assertRaisesRegex(c.Error, "预算已用完"): c.retry(self.root, p["job_id"], "重试")
        self.assertEqual(self.job(p)["attempts"], 1)
        _, calls = self.run_plan(p, [])
        self.assertEqual(calls, [])

    def test_ambiguous_timeout_never_automatically_resends(self):
        p = self.plan(max_requests=2)
        result, _ = self.run_plan(p, [c.api.AmbiguousRequest("请求结果不明")])
        self.assertEqual(result["status"], "uncertain")
        _, calls = self.run_plan(p, [])
        self.assertFalse(calls)
        c.retry(self.root, p["job_id"], "已核对，允许在原预算内重试这一次")
        result, calls = self.run_plan(p, [{"code": 200, "data": {"aweme_detail": video()}}])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["requests_sent"], 2)

    def test_crash_after_receipt_is_recovered_without_second_api_call(self):
        p = self.plan()
        original = c.api.page
        with patch.object(c.api, "page", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_plan(p, [{"code": 200, "data": {"aweme_detail": video()}}])
        with patch.object(c.api, "page", original):
            result, calls = self.run_plan(p, [])
        self.assertEqual(calls, [])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["requests_sent"], 1)

    def test_tampered_receipt_is_not_trusted_after_crash(self):
        p = self.plan()
        with patch.object(c.api, "page", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_plan(p, [{"code": 200, "data": {"aweme_detail": video()}}])
        _, output, _ = c.load_job(self.root, p["job_id"])
        path = output / "raw/request-0001.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj["payload"]["data"]["aweme_detail"]["desc"] = "被手改的内容"
        path.write_bytes(c.encode(obj))
        result, calls = self.run_plan(p, [])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(calls, [])
        self.assertEqual(result["records"], 0)

    def test_repeated_cursor_or_missing_shape_stops_paid_loop(self):
        for payload in [
            {"code": 200, "data": {"aweme_list": [video()], "has_more": 1, "max_cursor": 0}},
            {"code": 200, "data": {"unexpected": []}},
            {"code": 200, "data": {"aweme_list": [video()]}}
        ]:
            with self.subTest(payload=payload):
                p = self.plan(preset="douyin-posts", targets=["MS4Example"+str(len(str(payload)))], max_pages=2)
                result, calls = self.run_plan(p, [payload])
                self.assertEqual(result["status"], "needs_review")
                self.assertEqual(len(calls), 1)

    def test_billed_business_error_is_not_success(self):
        p = self.plan(preset="xiaohongshu-note", targets=["699916e6000000001d0253da"])
        result, _ = self.run_plan(p, [{"code": 200, "data": {"success": False, "msg": "服务异常"}}])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["records"], 0)
        self.assertEqual(result["requests_sent"], 1)

    def test_description_is_never_promoted_to_transcript(self):
        p = self.plan()
        result, _ = self.run_plan(p, [{"code": 200, "data": {"aweme_detail": video(desc="一段视频简介，不是逐字稿")}}])
        record = c.all_records(self.job(p))[0]
        self.assertIsNone(record["transcript"])
        self.assertEqual(record["metrics"]["likes"], 0)
        self.assertIsNone(record["metrics"]["views"])
        self.assertIn("尚无逐字稿", record["reading_status"])
        c.import_records(self.root, p["job_id"], "把这次采集放进知识库")
        materials = c.kb.load(self.root)["materials"]
        self.assertEqual(len(materials), 1)
        self.assertEqual(next(iter(materials.values()))["status"], "link_only")
        c.import_records(self.root, p["job_id"], "继续归档")
        self.assertEqual(len(c.kb.load(self.root)["materials"]), 1)

    def test_explicit_subtitles_import_as_external_unverified_extraction(self):
        p = self.plan()
        self.run_plan(p, [{"code": 200, "data": {"aweme_detail": video(subtitles=[{"start": 0, "text": "外部作者原话"}])}}])
        result = c.import_records(self.root, p["job_id"], "确认归档字幕，保留外部来源")
        material = c.kb.load(self.root)["materials"][result["materials"][0]["material_id"]]
        self.assertEqual(material["provenance"], "external")
        self.assertEqual(material["status"], "extracted_unverified")
        self.assertFalse(material["extraction"]["complete"])
        self.assertEqual(c.kb.load(self.root)["profile"], {})

    def test_key_and_signed_urls_never_enter_export_or_receipt(self):
        p = self.plan()
        row = video(desc="回显：" + KEY)
        row.update(token=KEY, download_url="https://cdn.example.com/a?sign=private-value&format=mp4")
        self.run_plan(p, [{"code": 200, "cache_url": "https://example.com/private", "data": {"aweme_detail": row}}])
        directory, output, job = c.load_job(self.root, p["job_id"])
        for path in list(directory.rglob("*.json")) + list(output.rglob("*")):
            if path.is_file():
                data = path.read_text(encoding="utf-8")
                self.assertNotIn(KEY, data)
                self.assertNotIn("private-value", data)
        self.assertIn("已脱敏", (output / "raw/request-0001.json").read_text(encoding="utf-8"))

    def test_csv_formula_injection_and_manual_export_edit_are_preserved(self):
        p = self.plan()
        result, _ = self.run_plan(p, [{"code": 200, "data": {"aweme_detail": video(desc="=HYPERLINK(恶意公式)")}}])
        _, output, _ = c.load_job(self.root, p["job_id"])
        self.assertIn("'=HYPERLINK", (output / "records.csv").read_text(encoding="utf-8"))
        (output / "采集报告.md").write_text("用户的修改", encoding="utf-8")
        with self.assertRaisesRegex(c.Error, "手工修改"): self.run_plan(p, [])
        self.assertEqual((output / "采集报告.md").read_text(encoding="utf-8"), "用户的修改")

    def test_plan_tamper_and_contract_changes_stop_before_network(self):
        p = self.plan()
        directory, _, job = c.load_job(self.root, p["job_id"])
        job["plan"]["budget_usd"] = "999"
        c.save_job(directory, job)
        with self.assertRaisesRegex(c.Error, "计划发生变化"): self.run_plan(p, [])
        p = self.plan(targets=["987654321"])
        with patch.dict(c.api.ROUTES["douyin-video"], {"endpoint": "/api/v1/douyin/web/fetch_one_video"}):
            with self.assertRaisesRegex(c.Error, "契约"): self.run_plan(p, [])

    def test_key_config_has_no_network_and_rejects_skill_directory(self):
        path = self.base / "config/tikhub.key"
        stream = io.StringIO()
        with patch.object(c.sys, "stdin", io.StringIO(KEY)), contextlib.redirect_stdout(stream), patch.object(c.api, "request", side_effect=AssertionError("network")):
            code = c.main(["configure", "--key-file", str(path), "--stdin"])
        self.assertEqual(code, 0)
        self.assertNotIn(KEY, stream.getvalue())
        self.assertEqual(path.read_text().strip(), KEY)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = c.main(["configure", "--key-file", str(SCRIPT.parent / "secret.key"), "--stdin"])
        self.assertEqual(code, 2)

    def test_public_targets_and_private_inputs(self):
        for url in ["http://127.0.0.1/a", "http://localhost/a", "https://user:pw@example.com", "file:///etc/passwd"]:
            with self.assertRaises(c.Error): c.api.public_url(url)
        with self.assertRaises(c.Error): self.plan(targets=["https://example.com/not-douyin"])
        with self.assertRaises(c.Error): c.api.raw_route("/api/v1/tikhub/user/delete_account")
        with self.assertRaises(c.Error): c.api.raw_route("/api/v1/douyin/web/fetch_douyin_web_guest_cookie")
        with self.assertRaises(c.Error): c.api.raw_route("/api/v1/douyin/web/handler_shorten_url")
        endpoint = "/api/v1/douyin/web/fetch_one_video"
        with self.assertRaises(c.Error): c.api.validate_params(endpoint, {"aweme_id": "123", "cookie": "private"})

    def test_generic_api_catalog_is_not_claimed_as_normalized_material(self):
        endpoint = "/api/v1/douyin/web/fetch_one_video"
        p = c.create_plan(self.root, None, [], unit_price="0.01", budget="1",
            price_source="https://docs.tikhub.io", price_checked_at=c.kb.now(),
            endpoint=endpoint, params={"aweme_id": "123456789"}, source_url="https://www.douyin.com/video/123456789")
        result, _ = self.run_plan(p, [{"code": 200, "data": {"anything": "合成原始接口数据"}}])
        self.assertEqual(result["status"], "completed")
        self.assertIn("尚待宿主核对", c.all_records(self.job(p))[0]["reading_status"])
        with self.assertRaisesRegex(c.Error, "不能把接口 JSON 当正文"):
            c.import_records(self.root, p["job_id"], "归档")
        self.assertEqual(c.kb.load(self.root)["materials"], {})

    def test_presets_match_official_parameter_catalog(self):
        for preset, route in c.api.ROUTES.items():
            with self.subTest(preset=preset):
                self.assertIn(route["endpoint"], c.api.catalog()["endpoints"])
                params, _ = c.api.target_params(preset, "123456789")
                c.api.validate_params(route["endpoint"], params)

    def test_get_and_readonly_post_use_official_method_and_do_not_follow_redirects(self):
        captured = []
        class Result:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return b'{"code":200,"data":{"text":"sample"}}'
        class Client:
            def open(self, request, timeout):
                captured.append(request)
                return Result()
        with patch.object(c.api.urllib.request, "build_opener", return_value=Client()):
            c.api.request("/api/v1/douyin/web/fetch_one_video", {"aweme_id": "123456789"}, KEY)
            c.api.request("/api/v1/wechat_mp/v2/fetch_article_detail", {"url": "https://mp.weixin.qq.com/s/example"}, KEY)
        self.assertEqual(captured[0].get_method(), "GET")
        self.assertIn("aweme_id=123456789", captured[0].full_url)
        self.assertEqual(captured[1].get_method(), "POST")
        self.assertEqual(json.loads(captured[1].data)["url"], "https://mp.weixin.qq.com/s/example")
        self.assertNotIn(KEY, captured[1].full_url)
        with self.assertRaisesRegex(c.Error, "重定向"):
            c.api.NoRedirect().redirect_request(captured[0], None, 302, "", {}, "https://evil.example/")

    def test_provider_http_body_and_key_are_not_echoed(self):
        class Client:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(request.full_url, 401, KEY, {}, io.BytesIO(KEY.encode()))
        with patch.object(c.api.urllib.request, "build_opener", return_value=Client()):
            with self.assertRaises(c.Error) as error:
                c.api.request("/api/v1/douyin/web/fetch_one_video", {"aweme_id": "123456789"}, KEY)
        self.assertIn("401", str(error.exception))
        self.assertNotIn(KEY, str(error.exception))

    def test_wrong_video_identity_is_not_imported(self):
        p = self.plan()
        result, _ = self.run_plan(p, [{"code": 200, "data": {"aweme_detail": video("999999999")}}])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["records"], 0)

    def test_xiaohongshu_notes_use_documented_last_id_cursor(self):
        route = c.api.ROUTES["xiaohongshu-posts"]
        payload = {"code": 200, "data": {"data": {"notes": [
            {"id": "699916e6000000001d0253da", "note_card": {"display_title": "合成笔记", "desc": "原文", "type": "normal"}}
        ], "has_more": True}}}
        rows, more, cursor = c.api.page(payload, route, "https://www.xiaohongshu.com/user/profile/example", c.kb.now())
        self.assertTrue(more)
        self.assertEqual(rows[0]["title"], "合成笔记")
        self.assertEqual(cursor["cursor"], rows[-1]["id"])

    def test_public_profile_signature_survives_credential_redaction(self):
        payload = {"code": 200, "data": {"user": {"uid": "123456789", "nickname": "公开作者",
                    "signature": "公开个人简介", "access_token": "private"}}}
        data = c.api.redact(payload, KEY)
        self.assertEqual(data["data"]["user"]["signature"], "公开个人简介")
        self.assertEqual(data["data"]["user"]["access_token"], "[已脱敏]")

    def test_unknown_note_type_does_not_become_readable_video_body(self):
        p = self.plan(preset="xiaohongshu-note", targets=["699916e6000000001d0253da"])
        self.run_plan(p, [{"code": 200, "data": {"note": {"note_id": "699916e6000000001d0253da", "desc": "可能只是简介"}}}])
        row = c.all_records(self.job(p))[0]
        self.assertEqual(row["body_kind"], "unknown_description")
        result = c.import_records(self.root, p["job_id"], "保留链接归档")
        material = c.kb.load(self.root)["materials"][result["materials"][0]["material_id"]]
        self.assertEqual(material["status"], "link_only")

    def test_cli_stopped_request_is_nonzero_and_keeps_report(self):
        p = self.plan()
        out = io.StringIO()
        with patch.object(c.api, "request", side_effect=c.api.ProviderError("TikHub HTTP 429")), contextlib.redirect_stdout(out):
            code = c.main(["--root", str(self.root), "run", "--job", p["job_id"],
                          "--plan-hash", p["plan_hash"], "--confirm", "按范围预算采样"])
        self.assertEqual(code, 2)
        result = json.loads(out.getvalue())
        self.assertFalse(result["ok"])
        self.assertTrue(Path(result["result"]["report"]).exists())

    def test_packaging_rejects_a_private_key_before_creating_archive(self):
        pack = module("collection_pack_test", REPO / "tools/package.py")
        base = self.base / "package"
        skill = base / "skills/chao-knowledge"
        skill.mkdir(parents=True)
        (skill / "tikhub.key").write_text(KEY)
        with patch.object(pack, "ROOT", base), patch.object(pack, "SKILL", skill):
            with self.assertRaisesRegex(ValueError, "私有 Key"): pack.build()
        self.assertFalse((base / "dist").exists())

    def test_existing_job_lock_prevents_any_paid_request(self):
        p = self.plan()
        directory, _, _ = c.load_job(self.root, p["job_id"])
        with c.kb.file_lock(self.root, (directory / "LOCK").relative_to(self.root).as_posix()):
            with self.assertRaisesRegex(c.kb.KBError, "锁等待超时"):
                self.run_plan(p, [])
        self.assertEqual(self.job(p)["attempts"], 0)

    def test_invalid_official_parameter_type_is_rejected_before_planning(self):
        with self.assertRaisesRegex(c.Error, "参数类型"):
            c.create_plan(self.root, None, [], unit_price="0.01", budget="1",
                price_source="https://docs.tikhub.io", price_checked_at=c.kb.now(),
                endpoint="/api/v1/douyin/app/v3/fetch_video_comments",
                params={"aweme_id": "123456789", "cursor": "not-a-number"},
                source_url="https://www.douyin.com/video/123456789")
