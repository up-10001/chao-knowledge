"""Offline regressions for discoverability and scope-independent startup."""
from pathlib import PurePosixPath
from unittest.mock import patch
from urllib.parse import unquote
import re

import json
import subprocess
import sys
import zipfile
from test_kb import WorkspaceCase, kb, REPO


class NoviceTests(WorkspaceCase):
    def test_owned_legacy_entry_is_backed_up_without_changing_user_text(self):
        self.init()
        original = '# 我的其他规则\n\n' + kb.LEGACY_BOOT + '\n保留末尾说明。\n'
        path = self.root / 'AGENTS.md'
        path.write_text(original, encoding='utf-8')
        self.assertTrue(self.init()['entry_updated'])
        self.assertEqual(path.read_text(encoding='utf-8'), original.replace(kb.LEGACY_BOOT.strip(), kb.BOOT.strip()))
        backups = list((self.root / '.chao/backups').glob('entry-*/AGENTS.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding='utf-8'), original)
        self.assertFalse(self.init()['entry_updated'])

    def test_custom_entry_block_is_not_silently_replaced(self):
        self.init()
        original = kb.LEGACY_BOOT.replace('## Chao Knowledge 工作区', '## 用户修改的工作区')
        path = self.root / 'AGENTS.md'
        path.write_text(original, encoding='utf-8')
        self.assertFalse(self.init()['entry_updated'])
        self.assertEqual(path.read_text(encoding='utf-8'), original)

    def test_crlf_owned_entry_upgrade_preserves_other_bytes_and_backup(self):
        self.init()
        before = ('# 保留的用户规则\r\n  原有缩进\r\n' + kb.LEGACY_BOOT.replace('\n', '\r\n') + '\r\n用户尾注  \r\n').encode('utf-8')
        path = self.root / 'AGENTS.md'
        path.write_bytes(before)
        self.assertTrue(self.init()['entry_updated'])
        expected = before.replace(kb.LEGACY_BOOT.strip().replace('\n', '\r\n').encode('utf-8'),
                                  kb.BOOT.strip().replace('\n', '\r\n').encode('utf-8'))
        self.assertEqual(path.read_bytes(), expected)
        backups = list((self.root / '.chao/backups').glob('entry-*/AGENTS.md'))
        self.assertEqual(backups[0].read_bytes(), before)

    def test_published_v033_workspace_upgrades_without_changing_facts(self):
        old = self.base / 'released-skill'
        with zipfile.ZipFile(REPO / 'dist/chao-knowledge-v0.3.3.zip') as archive:
            archive.extractall(old)
        script = old / 'chao-knowledge/scripts/kb.py'
        for args in [('init',), ('profile', '--field', '业务', '--value', '合成业务', '--quote', '我做合成业务')]:
            subprocess.run([sys.executable, str(script), '--root', str(self.root), *args], check=True, capture_output=True)
        before = json.loads((self.root / '.chao/state.json').read_text(encoding='utf-8'))
        self.init()
        after = kb.load(self.root)
        for key in before.keys() - {'views', 'updated_at', 'version'}:
            self.assertEqual(before[key], after[key])
        self.assertTrue((self.root / '02-资料库/资料索引.md').is_file())
        self.assertTrue((self.root / '03-内容中心/作品索引.md').is_file())
        self.assertEqual(self.call('sync')['changed'], [])

    def test_user_level_install_has_no_required_project_skill_path(self):
        self.init()
        entry = (self.root / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertNotIn('先读取 `.codebuddy/skills/chao-knowledge/SKILL.md`', entry)
        self.assertIn('实际加载', entry)
        self.assertFalse((self.root / '.codebuddy').exists())

    def test_all_records_remain_reachable_beyond_recent_eight(self):
        self.init()
        rows = []
        for i in range(10):
            rows.append(self.material(title='知识资料'+str(i), content='独立资料'+str(i)))
        index = (self.root / '02-资料库/资料索引.md').read_text(encoding='utf-8')
        category = (self.root / '02-资料库/素材/资料索引.md').read_text(encoding='utf-8')
        for row in rows:
            self.assertIn(row['title'], index)
            self.assertIn(row['title'], category)
        self.assertIn('查看全部资料', (self.root / '知识库地图.md').read_text(encoding='utf-8'))
        for relative in ['02-资料库/资料索引.md', '02-资料库/素材/资料索引.md']:
            text = (self.root / relative).read_text(encoding='utf-8')
            for target in re.findall(r'\]\(([^)]+)\)', text):
                self.assertTrue((self.root / PurePosixPath(relative).parent / unquote(target)).exists())

    def test_same_second_recent_order_follows_actual_registration(self):
        self.init()
        # UUID lexical order deliberately opposes registration order.
        with patch.object(kb, 'now', return_value='2026-10-08T00:00:00+00:00'):
            for i in range(10):
                with patch.object(kb, 'uid', return_value='m-'+format(99-i, '012x')):
                    self.material(title='同秒资料'+str(i), content='知识检索资料'+str(i))
        text = (self.root / '知识库地图.md').read_text(encoding='utf-8')
        recent = text.split('## 最近资料')[1].split('## 最近作品')[0]
        self.assertIn('同秒资料9', recent)
        self.assertNotIn('同秒资料0 |', recent)
        self.assertLess(recent.index('同秒资料9'), recent.index('同秒资料8'))
        # Relevance ties must also prefer the newer record.
        result = self.call('search', '--query', '知识检索', '--limit', '1')
        self.assertEqual(result['results'][0]['title'], '同秒资料9')

    def test_catalog_manual_edits_are_preserved_before_any_record_write(self):
        self.init()
        path = self.root / '02-资料库/资料索引.md'
        path.write_text('我的手工索引，不能覆盖', encoding='utf-8')
        before = (self.root / '.chao/state.json').read_bytes()
        with self.assertRaisesRegex(kb.KBError, '手工改动'):
            self.material()
        self.assertEqual(path.read_text(encoding='utf-8'), '我的手工索引，不能覆盖')
        self.assertEqual((self.root / '.chao/state.json').read_bytes(), before)

    def test_output_catalog_shows_branch_heads_and_retains_all_versions(self):
        self.init()
        old = self.output()
        self.put('00-收件箱/new.md', '修改后的合成稿')
        new = self.call('save', '--title', '用户二稿', '--file', '00-收件箱/new.md', '--parent', old['id'])['output']
        text = (self.root / '03-内容中心/作品索引.md').read_text(encoding='utf-8')
        self.assertIn('演示稿', text)
        self.assertIn('用户二稿', text)
        self.assertIn('历史版本', text)
        self.assertIn('当前分支末版', text)
        for row in [old, new]:
            self.assertIn(row['path'].removeprefix('03-内容中心/'), text)

    def test_rule_view_uses_human_names_without_machine_ids(self):
        self.init()
        rule = self.proposal('--scope', 'task=口播')
        self.activate(rule)
        text = (self.root / '05-经验与规则/我的长期要求.md').read_text(encoding='utf-8')
        self.assertIn('少用术语，多举例', text)
        self.assertIn('任务：口播', text)
        self.assertNotIn(rule['id'], text)
        self.call('revoke', '--id', rule['id'], '--quote', '撤销测试要求')
        text = (self.root / '05-经验与规则/我的长期要求.md').read_text(encoding='utf-8')
        self.assertIn('已撤销', text)
        self.assertNotIn(rule['id'], text)
