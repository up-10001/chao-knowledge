#!/usr/bin/env python3
"""Install the audited local skill into one workspace. No network or pip needed."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "skills/chao-knowledge"


def load_kb():
    spec = importlib.util.spec_from_file_location("chao_kb", SOURCE / "scripts/kb.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(source):
    rows = {}
    for p in sorted(source.rglob("*")):
        if p.is_symlink():
            raise ValueError("技能包不能包含符号链接")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc" and p.name != "manifest.json":
            rows[p.relative_to(source).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return rows


def install(workspace, initialize=False):
    # Manifest integrity is a consistency check, not a signature or proof of trust.
    expected = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    actual = inventory(SOURCE)
    if expected.get("files") != actual:
        raise ValueError("技能包与清单不一致；停止安装，请重新获取并审查来源")
    kb = load_kb()
    root = kb.root_path(workspace)
    if root == REPO:
        raise ValueError("请另选私人工作区，不要把知识库建在源码仓库里")
    root.mkdir(parents=True, exist_ok=True)
    target = kb.inside(root, ".codebuddy/skills/chao-knowledge")
    if target.exists():
        if not target.is_dir() or inventory(target) != actual:
            raise ValueError("已安装版本不同或曾被修改；未覆盖。请先备份，再由用户选择更新方式")
        result = {"status": "already_installed", "path": str(target)}
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".chao-install-", dir=str(target.parent)))
        try:
            for name in list(actual) + ["manifest.json"]:
                src = SOURCE / name
                dest = stage / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
            # mkdir is the ownership claim; never replace another installation.
            target.mkdir()
            try:
                for child in stage.iterdir():
                    shutil.move(str(child), str(target / child.name))
            except Exception:
                shutil.rmtree(target)
                raise
        finally:
            shutil.rmtree(stage)
        result = {"status": "installed", "path": str(target), "version": expected["version"]}
    if initialize:
        result["workspace"] = kb.initialize(root)
    result["next"] = "在同一工作区新建对话，明确调用 chao-knowledge，带用户做第一个任务"
    return result


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", required=True)
    p.add_argument("--init", action="store_true")
    a = p.parse_args()
    try:
        print(json.dumps({"ok": True, "result": install(a.workspace, a.init)}, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
