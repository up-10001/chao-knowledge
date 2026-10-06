#!/usr/bin/env python3
"""Rebuild a deterministic skill ZIP and its SHA-256 manifest (stdlib only)."""
from pathlib import Path
import hashlib
import json
import zipfile
import os
import stat

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/chao-knowledge"
VERSION = "0.3.0"


def build():
    files=[]
    for directory,dirs,names in os.walk(SKILL,followlinks=False):
        for name in dirs+names:
            p=Path(directory)/name
            if p.is_symlink() or getattr(p.lstat(),"st_file_attributes",0)&getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0x400) or p.is_file() and p.stat().st_nlink>1:
                raise ValueError("技能包不能含链接或重解析点")
            if p.is_file() and p!=SKILL/"manifest.json" and not (p.suffix==".pyc" and "__pycache__" in p.parts): files.append(p)
    files.sort(key=lambda p:p.relative_to(SKILL).as_posix())
    manifest_path=SKILL/"manifest.json"
    if manifest_path.is_symlink() or manifest_path.exists() and manifest_path.stat().st_nlink>1: raise ValueError("清单路径不安全")
    manifest = {"version": VERSION, "algorithm": "sha256", "files": {
        p.relative_to(SKILL).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (SKILL / "manifest.json").write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    dest = ROOT / "dist"
    dest.mkdir(exist_ok=True)
    zip_path = dest / ("chao-knowledge-v" + VERSION + ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as z:
        for p in files + [SKILL / "manifest.json"]:
            info = zipfile.ZipInfo("chao-knowledge/" + p.relative_to(SKILL).as_posix(), (2026, 10, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes())
    (dest / "SHA256SUMS").write_bytes((hashlib.sha256(zip_path.read_bytes()).hexdigest() + "  " + zip_path.name + "\n").encode("utf-8"))
    print(zip_path)


if __name__ == "__main__":
    build()
