"""TikHub transport and public-data adapters. No platform login or browser cookies."""
from __future__ import annotations

import datetime as dt
import hashlib
import functools
import ipaddress
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.tikhub.io"
MAX_RESPONSE = 4 * 1024 * 1024
SPEC_SOURCE = "https://api.tikhub.io/openapi.json"
CHECKED_AT = "2026-10-08"


class CollectionError(ValueError):
    pass


class AmbiguousRequest(CollectionError):
    """The request may have reached the provider; never retry automatically."""


class ProviderError(CollectionError):
    pass


def route(platform, kind, endpoint, parameter, **extra):
    return dict(platform=platform, kind=kind, endpoint=endpoint, parameter=parameter,
                method="GET", defaults={}, cursor=None, **extra)


# API contracts, not claims of live-provider acceptance. See collection.md sources.
ROUTES = {
    "douyin-video": route("douyin", "video", "/api/v1/douyin/app/v3/fetch_one_video_by_share_url", "share_url"),
    "douyin-account": route("douyin", "account", "/api/v1/douyin/app/v3/handler_user_profile", "sec_user_id"),
    "douyin-posts": route("douyin", "posts", "/api/v1/douyin/app/v3/fetch_user_post_videos", "sec_user_id"),
    "douyin-comments": route("douyin", "comments", "/api/v1/douyin/app/v3/fetch_video_comments", "aweme_id"),
    "xiaohongshu-note": route("xiaohongshu", "note", "/api/v1/xiaohongshu/app_v2/get_image_note_detail", "note_id"),
    "xiaohongshu-video": route("xiaohongshu", "video", "/api/v1/xiaohongshu/app_v2/get_video_note_detail", "note_id"),
    "xiaohongshu-account": route("xiaohongshu", "account", "/api/v1/xiaohongshu/app_v2/get_user_info", "user_id"),
    "xiaohongshu-posts": route("xiaohongshu", "posts", "/api/v1/xiaohongshu/app_v2/get_user_posted_notes", "user_id"),
    "xiaohongshu-comments": route("xiaohongshu", "comments", "/api/v1/xiaohongshu/app_v2/get_note_comments", "note_id"),
}
ROUTES["douyin-posts"].update(cursor="max_cursor", defaults={"max_cursor": 0, "count": 20})
ROUTES["douyin-comments"].update(cursor="cursor", defaults={"cursor": 0, "count": 20})
ROUTES["xiaohongshu-posts"].update(cursor="cursor", defaults={"cursor": ""})
ROUTES["xiaohongshu-comments"].update(cursor="cursor", defaults={"cursor": "", "index": 0, "pageArea": "UNFOLDED"})

SECRET_KEYS = re.compile(r"(?i)authorization|cookie|(?:^|_)(?:token|key|secret|signature|password|credential)(?:$|_)|xsec|a_bogus|mstoken|cache_url|decode_key")
SECRET_TEXT = re.compile(r"(?i)(?:Bearer\s+)[A-Za-z0-9._~+/-]+|\b(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{20,}")
URL_SECRET = re.compile(r"(?i)token|key|secret|signature|(?:^|[_-])sign(?:$|[_-])|auth|credential|xsec|a_bogus|mstoken|policy")
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


@functools.lru_cache(maxsize=1)
def catalog():
    return json.loads((Path(__file__).resolve().parents[1] / "assets/tikhub-endpoints.json").read_text(encoding="utf-8"))


def raw_route(endpoint):
    if endpoint not in catalog()["endpoints"]: raise CollectionError("端点不在已核对的读取接口目录中")
    result = route(catalog()["endpoints"][endpoint]["platform"], "api_response", endpoint, None)
    result["method"] = catalog()["endpoints"][endpoint]["method"]
    return result


def validate_params(endpoint, params):
    if not isinstance(params, dict) or len(params) > 50: raise CollectionError("接口参数必须是小型对象")
    schema = {p["name"]: p for p in catalog()["endpoints"][endpoint]["parameters"]}
    if set(params) - set(schema): raise CollectionError("存在官方契约未列出的参数")
    for name, definition in schema.items():
        if definition["required"] and (name not in params or params[name] in (None, "")):
            raise CollectionError("缺少必需接口参数：" + name)
    for key, value in params.items():
        if SECRET_KEYS.search(key): raise CollectionError("不接受平台 Cookie 或登录凭证参数")
        if type(value) not in (str, int, float, bool) or len(str(value)) > 4000:
            raise CollectionError("参数类型或长度不支持")
        expected = schema[key]["type"]
        if (expected == "integer" and type(value) is not int or
                expected == "boolean" and type(value) is not bool or
                expected == "string" and not isinstance(value, str) or
                expected == "number" and type(value) not in (int, float)):
            raise CollectionError("接口参数类型不匹配：" + key)
        if isinstance(value, str) and value.startswith(("http://", "https://")) and public_url(value) != value:
            raise CollectionError("链接参数含临时凭据，请先去除或改用公开对象 ID")
    return dict(params)


def public_url(value):
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise CollectionError("请提供不含账号口令的公开链接")
    if parsed.port not in (None, 80, 443) or any(c in value for c in "\r\n\x00"):
        raise CollectionError("链接格式不适合公开采集")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".localhost", ".local")):
        raise CollectionError("不采集本机或内网链接")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global: raise CollectionError("不采集本机或内网链接")
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query) if not URL_SECRET.search(k)]
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), ""))


def redact(value, key=""):
    if isinstance(value, dict):
        is_public_profile = any(k in value for k in ("uid", "sec_uid", "user_id")) and any(k in value for k in ("nickname", "nick_name"))
        return {k: ("[已脱敏]" if SECRET_KEYS.search(k) and not (k == "signature" and is_public_profile) else redact(v, key)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    if isinstance(value, str):
        if key: value = value.replace(key, "[已脱敏]")
        value = SECRET_TEXT.sub("[已脱敏]", value)
        def clean(match):
            try: return public_url(match.group())
            except (ValueError, CollectionError): return "[不可公开的链接]"
        return URL_PATTERN.sub(clean, value)
    return value


def key_path():
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData/Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "chao-knowledge/tikhub.key"


def resolve_key(kb, explicit=None):
    # Only one designated config file; never scan user directories.
    value = os.environ.get("TIKHUB_API_KEY", "") if explicit is None else ""
    source = "环境变量" if value else "配置文件"
    if not value:
        path = kb.no_symlinks(Path(explicit).expanduser() if explicit else key_path())
        if not path.exists(): raise CollectionError("尚未配置 TikHub Key；先用 configure 保存自己的 Key")
        if not path.is_file() or path.stat().st_nlink != 1 or path.stat().st_size > 4096:
            raise CollectionError("Key 文件不是安全的普通小文件")
        value = path.read_text(encoding="utf-8").strip()
    value = value.strip()
    if not value or len(value) > 4096 or re.search(r"\s", value):
        raise CollectionError("Key 应只包含令牌本身，不要包含 Bearer 或空白")
    return value, source


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError("TikHub 返回重定向；未向其他地址发送 Key")


def request(endpoint, params, key):
    if not re.fullmatch(r"/api/v1/[a-z0-9_/]+", endpoint):
        raise CollectionError("端点路径无效")
    # The caller chooses from reviewed read-only routes or the price endpoint.
    allowed = set(catalog()["endpoints"]) | {r["endpoint"] for r in ROUTES.values()} | {"/api/v1/tikhub/user/calculate_price"}
    if endpoint not in allowed: raise CollectionError("未支持的采集端点，停止付费请求")
    if any(SECRET_KEYS.search(k) for k in params): raise CollectionError("参数不能包含 Cookie 或其他凭证")
    method = catalog()["endpoints"].get(endpoint, {}).get("method", "GET")
    url = API + endpoint + ("?" + urllib.parse.urlencode(params) if method == "GET" else "")
    body = json.dumps(params, ensure_ascii=False, allow_nan=False).encode("utf-8") if method == "POST" else None
    req = urllib.request.Request(url, data=body, method=method,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": "ChaoKnowledge-Collector/0.4"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=45) as response:
            raw = response.read(MAX_RESPONSE + 1)
    except urllib.error.HTTPError as exc:
        # Do not log the body, request URL, headers or provider echo of credentials.
        raise ProviderError("TikHub HTTP %d；未自动重试，请核对权限、余额或限速" % exc.code) from None
    except (TimeoutError, OSError, urllib.error.URLError):
        raise AmbiguousRequest("请求结果不明，可能已扣费；保留断点，不自动重发") from None
    if len(raw) > MAX_RESPONSE: raise ProviderError("响应超过 4 MiB；已停止，需缩小范围")
    try:
        payload = json.loads(raw.decode("utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, ValueError, RecursionError):
        raise ProviderError("接口返回的不是有效 JSON；未自动重试") from None
    return {"payload": redact(payload, key), "wire_sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "redacted": True}


def target_params(name, target):
    r = ROUTES[name]
    target = target.strip()
    if not target or len(target) > 2000 or any(c in target for c in "\r\n\x00"):
        raise CollectionError("采集对象为空或无效")
    params = dict(r["defaults"])
    source = None
    if target.startswith(("https://", "http://")):
        source = public_url(target)
        host = urllib.parse.urlsplit(source).hostname.lower()
        domains = ("douyin.com", "iesdouyin.com") if r["platform"] == "douyin" else ("xiaohongshu.com", "xhslink.com", "xhslink.cn")
        if not any(host == d or host.endswith("." + d) for d in domains):
            raise CollectionError("链接平台与采集模式不一致")
        path = urllib.parse.urlsplit(source).path
        if r["platform"] == "xiaohongshu":
            # Provider accepts share_text; no login token is persisted or required.
            params["share_text"] = source
            return params, source
        if r["parameter"] == "share_url":
            params["share_url"] = source
            return params, source
        pattern = r"/user/([^/?]+)" if r["parameter"] == "sec_user_id" else r"/video/(\d+)"
        match = re.search(pattern, path)
        if not match: raise CollectionError("此模式需要账号主页长链接或公开 ID；短视频链接请用 douyin-video")
        target = match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,180}", target): raise CollectionError("公开 ID 格式无效")
    if r["parameter"] == "share_url":
        if not target.isdigit(): raise CollectionError("请提供抖音视频链接或数字作品 ID")
        target = "https://www.douyin.com/video/" + target
    params[r["parameter"]] = target
    if not source:
        if r["platform"] == "douyin": source = target if target.startswith("https:") else "https://www.douyin.com/" + ("user/" if r["parameter"] == "sec_user_id" else "video/") + target
        else: source = "https://www.xiaohongshu.com/" + ("user/profile/" if r["parameter"] == "user_id" else "explore/") + target
    return params, source


def envelopes(payload):
    if not isinstance(payload, dict) or payload.get("code") not in (200, "200"):
        raise ProviderError("接口业务状态未成功；请求可能计费，请先核对")
    result, data = [], payload.get("data")
    for _ in range(5):
        if not isinstance(data, dict): break
        if data.get("success") is False or ("code" in data and data["code"] not in (0, 200, "0", "200")) or ("status_code" in data and data["status_code"] not in (0, "0")):
            raise ProviderError("上游数据未成功；不能把计费响应当采集成功")
        result.append(data)
        data = data.get("data")
    if not result: raise ProviderError("接口没有有效数据，停止本轮采集")
    return result


def integer(value):
    if type(value) is int and value >= 0: return value
    if isinstance(value, str) and value.isdecimal(): return int(value)
    return None


def first(row, *keys):
    for key in keys:
        value = row.get(key)
        if value is not None and value != "": return value
    return None


def text(value, limit=20000):
    return value[:limit] if isinstance(value, str) else ""


def transcript(row):
    # Deliberately exclude desc/caption/title: they are not spoken words.
    for key in ("subtitle_text", "transcript_text"):
        if isinstance(row.get(key), str) and row[key].strip(): return text(row[key])
    for key in ("subtitles", "transcript"):
        lines = row.get(key)
        if isinstance(lines, list) and lines and all(isinstance(x, dict) and isinstance(x.get("text"), str) and ("start" in x or "start_time" in x) for x in lines):
            return text("\n".join(x["text"] for x in lines))
    return ""


def normalize(row, r, source, collected_at):
    if not isinstance(row, dict): raise ProviderError("记录字段结构改变，停止批量并保留证据")
    for key in ("note_card", "aweme_detail", "note"):
        if isinstance(row.get(key), dict): row = dict(row, **row[key])
    kind = r["kind"]
    if kind == "account":
        rid = first(row, "sec_uid", "sec_user_id", "user_id", "uid", "id")
        author = first(row, "nickname", "nick_name", "name")
        body = text(first(row, "signature", "desc", "bio"))
        title = text(author, 300)
        counts = {"followers": integer(first(row, "follower_count", "fans", "fans_count"))}
        body_kind = "account_profile"
    elif kind == "comments":
        rid = first(row, "cid", "comment_id", "id")
        author = None  # Avoid exporting unrelated commenter identity fields.
        body = text(first(row, "text", "content", "comment_text"))
        title = "评论：" + body[:60]
        counts = {"likes": integer(first(row, "digg_count", "like_count", "likes"))}
        body_kind = "comment"
    else:
        rid = first(row, "aweme_id", "note_id", "id")
        who = first(row, "author", "user")
        author = first(who, "nickname", "nick_name", "name") if isinstance(who, dict) else None
        body = text(first(row, "desc", "description", "content", "caption"))
        title = text(first(row, "title", "display_title", "desc", "description"), 300) or "未提供标题"
        stats = first(row, "statistics", "interact_info") or row
        if not isinstance(stats, dict): raise ProviderError("互动字段结构改变，停止批量")
        counts = {"views": integer(first(stats, "play_count", "view_count", "views")),
                  "likes": integer(first(stats, "digg_count", "liked_count", "like_count")),
                  "comments": integer(first(stats, "comment_count", "comments_count")),
                  "favorites": integer(first(stats, "collect_count", "collected_count")),
                  "shares": integer(first(stats, "share_count", "shared_count"))}
        is_video = r["platform"] == "douyin" or kind == "video" or row.get("type") == "video" or isinstance(row.get("video"), dict)
        body_kind = "video_description" if is_video else "note_text" if row.get("type") in ("normal", "image", "text", "article") else "unknown_description"
        source = ("https://www.douyin.com/video/" if r["platform"] == "douyin" else "https://www.xiaohongshu.com/explore/") + str(rid)
    if rid is None or not re.fullmatch(r"[A-Za-z0-9_-]{1,180}", str(rid)):
        raise ProviderError("缺少可核对的记录 ID，不能宣称采集成功")
    if kind == "comments" and not body: raise ProviderError("评论缺少正文，停止批量")
    words = transcript(row) if body_kind == "video_description" else ""
    return {"platform": r["platform"], "kind": kind, "id": str(rid), "title": title,
            "source_url": source, "author_name": text(author, 200) or None,
            "published_at_raw": first(row, "create_time", "time", "publish_time"),
            "collected_at": collected_at, "body": body, "body_kind": body_kind,
            "transcript": words or None, "transcript_source": "TikHub 返回的字幕字段（未人工核对）" if words else None,
            "reading_status": "字幕待核对" if words else "仅简介，尚无逐字稿" if body_kind == "video_description" else "内容类型待核对，仅保存元数据" if body_kind == "unknown_description" else "接口文本，未核实完整性" if body else "仅元数据，未获取正文",
            "metrics": counts, "provenance": "external"}


def page(payload, r, source, collected_at):
    if r["kind"] == "api_response" and isinstance(payload, dict) and payload.get("code") in (200, "200") and isinstance(payload.get("data"), (list, str)):
        chain = [{"data": payload["data"]}]
    else:
        chain = envelopes(payload)
    kind, rows, owner = r["kind"], None, chain[-1]
    if kind == "api_response":
        record = {"platform": r["platform"], "kind": kind, "id": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20],
                  "title": r["endpoint"].rsplit("/", 1)[-1], "source_url": source, "author_name": None,
                  "collected_at": collected_at, "body": "", "body_kind": "api_response", "transcript": None,
                  "transcript_source": None, "metrics": {}, "provenance": "external",
                  "reading_status": "原始接口数据；字段与分页尚待宿主核对"}
        return [record], False, {}
    if kind in ("posts", "comments"):
        names = ("comments", "comment_list") if kind == "comments" else ("aweme_list", "notes", "items", "note_list")
        for obj in reversed(chain):
            for key in names:
                if key in obj:
                    if not isinstance(obj[key], list): raise ProviderError("分页记录不是列表，停止批量")
                    rows, owner = obj[key], obj
                    break
            if rows is not None: break
        if rows is None: raise ProviderError("未找到预期分页字段，请先更新适配器")
    else:
        for obj in reversed(chain):
            names = ("user", "user_info") if kind == "account" else ("aweme_detail", "note", "note_card", "aweme_details", "items", "notes")
            for key in names:
                if isinstance(obj.get(key), (dict, list)):
                    rows = obj[key] if isinstance(obj[key], list) else [obj[key]]
                    owner = obj
                    break
            if rows is not None: break
        if rows is None: rows = [chain[-1]]
    if len(rows) > 500: raise ProviderError("单页记录异常过多，停止批量")
    normalized = [normalize(x, r, source, collected_at) for x in rows]
    if kind in ("video", "note"):
        path = urllib.parse.urlsplit(source).path
        expected = re.search(r"/(?:video|explore|discovery/item)/([A-Za-z0-9_-]+)", path)
        if expected and (len(normalized) != 1 or normalized[0]["id"] != expected.group(1)):
            raise ProviderError("返回的作品与请求链接不一致，停止而非导入错误对象")
    more = first(owner, "has_more", "hasMore")
    if more is None:
        for obj in reversed(chain):
            more = first(obj, "has_more", "hasMore")
            if more is not None: break
    if r["cursor"] and more not in (0, 1, False, True, "0", "1"):
        raise ProviderError("分页结束标记缺失，不能猜测已采集完整")
    has_more = more in (1, True, "1") if r["cursor"] else False
    continuation = {}
    if has_more:
        for obj in reversed(chain):
            if r["cursor"] in obj:
                continuation[r["cursor"]] = obj[r["cursor"]]
                if r["platform"] == "xiaohongshu" and kind == "comments":
                    for key in ("index", "pageArea"):
                        if key not in obj: raise ProviderError("小红书评论分页字段不全，停止而非猜页码")
                        continuation[key] = obj[key]
                break
        if not continuation and r["platform"] == "xiaohongshu" and kind == "posts" and normalized:
            # Official App V2 contract: next cursor can be the final note_id.
            continuation = {"cursor": normalized[-1]["id"]}
        if not continuation or not normalized: raise ProviderError("分页游标缺失或空页仍声称有下一页，停止批量")
        if any(not isinstance(v, (str, int)) or isinstance(v, bool) or len(str(v)) > 2000 for v in continuation.values()):
            raise ProviderError("分页游标结构改变，停止批量")
    return normalized, has_more, continuation
