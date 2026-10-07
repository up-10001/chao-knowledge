#!/usr/bin/env python3
"""Real remote Skills CLI packaging check in an isolated temporary workspace."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'skills/chao-knowledge'

def main():
    expected = json.loads((SOURCE / 'manifest.json').read_text(encoding='utf-8'))
    npx = shutil.which('npx')
    if not npx:
        raise RuntimeError('npx unavailable; not a repository-format verdict')
    with tempfile.TemporaryDirectory(prefix='chao-cli-') as tmp:
        workspace = Path(tmp).resolve()
        env = dict(os.environ, CI='1', DISABLE_TELEMETRY='1')
        command = [npx, '-y', 'skills@latest', 'add', 'up-10001/chao-knowledge', '--skill', 'chao-knowledge', '-y']
        result = subprocess.run(command, cwd=workspace, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        log = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('standard CLI failed: ' + log[-2500:])
        target = workspace / '.agents/skills/chao-knowledge'
        manifest = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
        if manifest != expected:
            raise RuntimeError('remote main skill differs from CI checkout; do not claim current-source PASS')
        installed = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        if installed != manifest['files']:
            raise RuntimeError('CLI did not preserve the complete Skill package')
        roots = [p for p in REPO.rglob('SKILL.md') if '.git' not in p.parts and '.agents' not in p.parts]
        if roots != [SOURCE / 'SKILL.md']:
            raise RuntimeError('repository contains unexpected Skill discovery roots')
        if not re.search(r'^version: "' + re.escape(manifest['version']) + r'"$', (target / 'SKILL.md').read_text(encoding='utf-8'), re.M):
            raise RuntimeError('SKILL and manifest versions differ')
        script = target / 'scripts/kb.py'
        subprocess.run([sys.executable, str(script), '--help'], check=True, capture_output=True, timeout=15)
        knowledge = workspace / 'blank-knowledge'
        for operation in ['init', 'context', 'health']:
            args = [sys.executable, str(script), '--root', str(knowledge), operation]
            if operation == 'context': args += ['--task', 'CLI installation verification']
            ran = subprocess.run(args, check=True, capture_output=True, text=True, encoding='utf-8', timeout=15)
            if not json.loads(ran.stdout)['ok']: raise RuntimeError('installed script failed: ' + operation)
        print(json.dumps({'evidence':'real remote standard Skills CLI; isolated runner, not WorkBuddy GUI', 'status':'PASS', 'version':manifest['version'], 'unique_repository_skill':True, 'verified_files':len(manifest['files']), 'references_scripts_assets_complete':True, 'installed_entry_init_context_health':'PASS'}, ensure_ascii=False))

if __name__ == '__main__':
    main()
