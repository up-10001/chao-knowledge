#!/usr/bin/env python3
"""Install or update one workspace; no network, dependencies or personal-data scan."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import uuid

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "skills/chao-knowledge"


def load_kb():
    spec = importlib.util.spec_from_file_location("chao_kb", SOURCE / "scripts/kb.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(source):
    for p in [source]+list(source.parents):
        if p.is_symlink() or p.exists() and getattr(p.lstat(),"st_file_attributes",0)&getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0x400):
            raise ValueError("技能来源不能包含链接或目录联接")
    rows = {}
    for directory, dirs, files in os.walk(source, followlinks=False):
        for name in dirs + files:
            p = Path(directory) / name
            info = p.lstat()
            if p.is_symlink() or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise ValueError("技能包不能包含链接或目录联接")
            if p.is_file():
                if info.st_nlink > 1: raise ValueError("技能包不能包含硬链接")
                rel = p.relative_to(source).as_posix()
                if p.name == "manifest.json" and p.parent == source: continue
                if p.suffix == ".pyc" and "__pycache__" in p.parts: continue
                rows[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return rows


def checked_manifest(source):
    path = source / "manifest.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink > 1 or path.stat().st_size > 1024 * 1024:
        raise ValueError("技能清单不安全或缺失；停止安装")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("algorithm") != "sha256" or not re.fullmatch(r"\d+\.\d+\.\d+", str(obj.get("version", ""))):
        raise ValueError("技能清单版本或算法无效")
    actual = inventory(source)
    if obj.get("files") != actual or "SKILL.md" not in actual or "scripts/kb.py" not in actual:
        raise ValueError("技能包与清单不一致或曾被修改；为保护自定义内容不覆盖")
    return obj, actual


def copy_stage(source, parent, files):
    stage = Path(tempfile.mkdtemp(prefix=".chao-install-", dir=str(parent)))
    try:
        for name in list(files) + ["manifest.json"]:
            src = source / name
            dest = stage / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        checked_manifest(stage)
        return stage
    except BaseException:
        shutil.rmtree(stage)
        raise


def install(workspace, initialize=False, update=False, rollback=None, restore_migration=False, quote=None):
    expected, actual = checked_manifest(SOURCE)
    kb = load_kb()
    kb.no_symlinks(SOURCE)
    root = kb.root_path(workspace)
    if root == REPO: raise ValueError("请另选私人工作区，不要把知识库建在源码仓库里")
    root.mkdir(parents=True, exist_ok=True)
    guard = kb.inside(root, ".chao-install-lock")
    try: guard.mkdir()
    except FileExistsError: raise ValueError("另一个任务正在安装或更新；请稍后重试，不强制解锁")
    try:
        target = kb.inside(root, ".codebuddy/skills/chao-knowledge")
        if target.exists() and not target.is_dir(): raise ValueError("技能目标路径不是文件夹；停止安装")
        source = SOURCE
        restore_state = False
        if restore_migration and not rollback: raise ValueError("--restore-migration 仅用于明确回滚技能时")
        if rollback:
            if initialize or update: raise ValueError("回滚技能不能同时升级状态；状态恢复另按备份说明处理")
            source = kb.inside(root, rollback)
            if source.parent != kb.inside(root, ".codebuddy/skill-backups"):
                raise ValueError("只接受本工作区 skill-backups 中的完整备份")
            expected, actual = checked_manifest(source)
            schema_match=re.search(r"^SCHEMA = (\d+)$",(source/"scripts/kb.py").read_text(encoding="utf-8"),re.M)
            if not schema_match: raise ValueError("备份技能 schema 无法确认")
            if kb.inside(root,".chao/state.json").exists():
                with kb.lock(root):
                    state=kb.load(root)
                    if state["schema"]>int(schema_match[1]):
                        if not restore_migration: raise ValueError("旧技能无法读取新状态；需确认 --restore-migration 恢复升级前状态，升级后已有新数据则禁止覆盖")
                        kb.check_text(quote,"回滚确认",1000)
                        kb.rollback_migration(root,state)
                        restore_state=True
        current = None
        if target.exists(): current, current_files = checked_manifest(target)
        if current and current_files == actual and current == expected:
            result = {"status":"already_installed", "path":str(target), "version":expected["version"]}
            if initialize: result["workspace"] = kb.initialize(root)
            return result
        if current and not (update or rollback):
            raise ValueError("已有不同版本；未覆盖。更新请使用 --update，自定义文件须先核对")
        target.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        stage = copy_stage(source, target.parent, actual)
        try:
            if current:
                backup_root = kb.inside(root, ".codebuddy/skill-backups")
                backup_root.mkdir(parents=True, exist_ok=True)
                backup = kb.inside(root, ".codebuddy/skill-backups/chao-knowledge-v" + current["version"] + "-" + uuid.uuid4().hex[:12])
                target.rename(backup)
            try:
                stage.rename(target)
                result = {"status":"rolled_back" if rollback else "updated" if backup else "installed", "path":str(target), "version":expected["version"]}
                if initialize: result["workspace"] = kb.initialize(root)
                if restore_state:
                    with kb.lock(root),kb.transaction(root): result["workspace"]=kb.rollback_migration(root,kb.load(root),True,quote)
            except BaseException:
                if target.exists(): shutil.rmtree(target)
                if backup: backup.rename(target)
                raise
            if backup: result["backup"] = str(backup)
        finally:
            if stage.exists(): shutil.rmtree(stage)
        result["next"] = "同一工作区新建对话调用 chao-knowledge，先完成一个真实任务"
        return result
    except kb.KBError as exc:
        raise ValueError(str(exc)) from exc
    finally:
        guard.rmdir()


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", required=True)
    p.add_argument("--init", action="store_true")
    p.add_argument("--update", action="store_true", help="仅替换完整未改动的旧 Skill，保留备份与用户知识库")
    p.add_argument("--rollback", help="回滚到本工作区 .codebuddy/skill-backups 中指定的相对路径；不回滚知识库状态")
    p.add_argument("--restore-migration",action="store_true",help="仅在升级后没有新数据修改时，与技能回滚一起恢复旧状态")
    p.add_argument("--quote",help="实际用户给出的回滚确认")
    a = p.parse_args()
    try:
        print(json.dumps({"ok":True,"result":install(a.workspace,a.init,a.update,a.rollback,a.restore_migration,a.quote)},ensure_ascii=False,indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok":False,"error":str(e)},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__ == "__main__": sys.exit(main())
