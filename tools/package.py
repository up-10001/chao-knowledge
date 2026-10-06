#!/usr/bin/env python3
"""Rebuild a deterministic skill ZIP and its SHA-256 manifest (stdlib only)."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/chao-knowledge"
VERSION = "0.1.0"


def build():
    files = sorted(p for p in SKILL.rglob("*") if p.is_file() and not p.is_symlink()
                   and "__pycache__" not in p.parts and p.suffix != ".pyc" and p.name != "manifest.json")
    manifest = {"version": VERSION, "algorithm": "sha256", "files": {
        p.relative_to(SKILL).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (SKILL / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dest = ROOT / "dist"
    dest.mkdir(exist_ok=True)
    zip_path = dest / ("chao-knowledge-v" + VERSION + ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files + [SKILL / "manifest.json"]:
            info = zipfile.ZipInfo("chao-knowledge/" + p.relative_to(SKILL).as_posix(), (2026, 10, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes())
    (dest / "SHA256SUMS").write_text(hashlib.sha256(zip_path.read_bytes()).hexdigest() + "  " + zip_path.name + "\n", encoding="utf-8")
    print(zip_path)


if __name__ == "__main__":
    build()
