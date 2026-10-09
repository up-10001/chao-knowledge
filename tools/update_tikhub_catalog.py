"""Extract read-operation parameter facts from a reviewed official OpenAPI snapshot."""
import argparse
import json
from pathlib import Path
import re

PLATFORMS = {"douyin", "tiktok", "xiaohongshu", "wechat_channels", "wechat_mp", "wechat_search",
             "bilibili", "youtube", "twitter", "instagram", "reddit", "weibo", "kuaishou",
             "zhihu", "threads", "lemon8", "linkedin"}


def build(spec, source, checked_at):
    endpoints = {}
    for path, operations in spec["paths"].items():
        parts = path.strip("/").split("/")
        if len(parts) < 5 or parts[:2] != ["api", "v1"] or parts[2] not in PLATFORMS:
            continue
        if not re.match(r"^(fetch_|get_|search_|handler_)", parts[-1]): continue
        if re.search(r"cookie|login|password|credential|captcha|access_token", parts[-1], re.I): continue
        if parts[-1].startswith("handler_") and not re.fullmatch(r"handler_user_profile(?:_v\d+)?", parts[-1]): continue
        method = "get" if "get" in operations else "post" if "post" in operations else None
        if not method: continue
        op, params = operations[method], []
        for p in op.get("parameters", []):
            if p.get("in") == "query":
                schema = p.get("schema", {})
                params.append({"name": p["name"], "required": p.get("required", False),
                               "type": schema.get("type"), "default": schema.get("default")})
        if method == "post":
            schema = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
            if "$ref" in schema: schema = spec["components"]["schemas"][schema["$ref"].split("/")[-1]]
            if not schema.get("properties"): continue
            params += [{"name": name, "required": name in schema.get("required", []),
                        "type": prop.get("type"), "default": prop.get("default")}
                       for name, prop in schema["properties"].items()]
        if any(p["required"] and re.search("cookie|token|password|secret|credential|api_key", p["name"], re.I) for p in params): continue
        endpoints[path] = {"platform": parts[2], "method": method.upper(), "parameters": params}
    return {"source": source, "api_version": spec["info"]["version"], "checked_at": checked_at,
            "scope": "Read-operation contracts only; not proof of live endpoint availability or full field/pagination mapping.",
            "endpoints": endpoints}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", required=True); p.add_argument("--source", required=True); p.add_argument("--checked-at", required=True)
    args = p.parse_args()
    output = Path(__file__).resolve().parents[1] / "skills/chao-knowledge/assets/tikhub-endpoints.json"
    result = build(json.loads(Path(args.spec).read_text(encoding="utf-8")), args.source, args.checked_at)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"contracts": len(result["endpoints"]), "output": str(output)}))
