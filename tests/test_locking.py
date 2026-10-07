"""OS-process and denied-deletion regressions for persistent standard-library locks."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from unittest import mock
from test_kb import WorkspaceCase, kb, installer, SCRIPT, REPO

WORKER = '''import importlib.util,sys,os
s=importlib.util.spec_from_file_location("worker_kb",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=m.root_path(sys.argv[2])
with m.lock(r):
 print("LOCKED",flush=True)
 if sys.argv[3]=="crash":os._exit(7)
 sys.stdin.readline()
'''


class PersistentLockTests(WorkspaceCase):
    def command(self,*args):
        return subprocess.run([sys.executable,str(SCRIPT),'--root',str(self.root),*args],capture_output=True,text=True,encoding='utf-8',timeout=15)

    def holder(self,mode='hold'):
        p=subprocess.Popen([sys.executable,'-u','-c',WORKER,str(SCRIPT),str(self.root),mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
        self.assertEqual(p.stdout.readline().strip(),'LOCKED')
        return p

    def test_continuous_business_and_install_succeed_when_all_deletion_is_denied(self):
        denied=PermissionError('simulated WorkBuddy safe-delete: directory/file deletion denied')
        with mock.patch.object(os,'unlink',side_effect=denied),mock.patch.object(os,'rmdir',side_effect=denied),mock.patch.object(shutil,'rmtree',side_effect=denied):
            installer.install(str(self.root),True)
            self.assertTrue((self.root/'.chao/LOCK').is_file())
            self.call('profile','--field','身份','--value','合成测试用户','--quote','这是测试身份')
            self.put('00-收件箱/source.txt','合成会议资料，决策、待办、待确认。')
            material=self.call('ingest','--title','会议资料','--file','00-收件箱/source.txt')['material']
            self.call('context','--task','会议资料')
            rule=self.call('remember','--key','用词','--text','少术语','--scope','task=口播')['rule']
            self.call('confirm','--id',rule['id'],'--quote','确认只用于口播')
            self.put('00-收件箱/draft.md','合成口播稿')
            self.call('save','--title','口播','--file','00-收件箱/draft.md','--source',material['id'])
            self.call('health')
            self.call('init')
            with kb.lock(self.root,wait_seconds=0):pass
            self.assertFalse(kb.pending_write(self.root))
            self.assertEqual(json.loads((self.root/'.chao/pending-write.json').read_text(encoding='utf-8'))['files'],[])

    def test_each_cli_command_releases_lock_for_the_next_process(self):
        def step(*args):
            p=self.command(*args);self.assertEqual(p.returncode,0,p.stderr)
            with kb.lock(self.root,wait_seconds=0):pass
            return json.loads(p.stdout)["result"]
        step('init')
        inode=(self.root/'.chao/LOCK').stat().st_ino
        step('profile','--field','身份','--value','测试用户','--quote','这是合成测试')
        self.put('00-收件箱/source.txt','合成文本资料，会议决定先完成锁回归。')
        material=step('ingest','--title','会议资料','--file','00-收件箱/source.txt')['material']
        step('context','--task','会议资料')
        rule=step('remember','--key','表达','--text','少术语','--scope','task=会议')['rule']
        step('confirm','--id',rule['id'],'--quote','确认只用于会议')
        self.put('00-收件箱/draft.md','合成会议草稿')
        step('save','--title','会议稿','--file','00-收件箱/draft.md','--source',material['id'])
        step('health')
        self.assertEqual(inode,(self.root/'.chao/LOCK').stat().st_ino)

    def test_real_process_waits_and_acquires_after_holder_exits(self):
        self.init();holder=self.holder()
        try:
            rejected=self.command('--lock-timeout','0','context','--task','写作')
            self.assertEqual(rejected.returncode,2)
            self.assertIn('超时',rejected.stderr)
            waiting=subprocess.Popen([sys.executable,str(SCRIPT),'--root',str(self.root),'--lock-timeout','5','context','--task','等待任务'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
            time.sleep(0.25);self.assertIsNone(waiting.poll())
            holder.communicate('\n',timeout=10)
            out,err=waiting.communicate(timeout=10)
            self.assertEqual(waiting.returncode,0,err);self.assertTrue(json.loads(out)['ok'])
        finally:
            if holder.poll() is None:holder.kill();holder.communicate(timeout=10)

    def test_abrupt_process_exit_and_kill_leave_no_stale_lock(self):
        self.init()
        for mode in ['crash','hold']:
            p=self.holder(mode)
            if mode=='hold':p.kill()
            p.communicate(timeout=10)
            self.assertEqual(self.command('context','--task','退出后任务').returncode,0)
            self.assertTrue((self.root/'.chao/LOCK').is_file())
            with kb.lock(self.root,wait_seconds=0):pass

    def old_workspace(self):
        source=subprocess.check_output(['git','show','v0.3.0:skills/chao-knowledge/scripts/kb.py'],cwd=REPO)
        path=self.base/'v030.py';path.write_bytes(source)
        spec=importlib.util.spec_from_file_location('old_kb',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        old.initialize(self.root)
        return old

    def test_legacy_directories_are_preserved_and_migration_is_explicit(self):
        old=self.old_workspace()
        for rel in kb.LEGACY_LOCKS:(self.root/rel).mkdir()
        original=(self.root/'.chao/state.json').read_bytes()
        with self.assertRaisesRegex(kb.KBError,'migrate-locks'):self.init()
        plan=self.call('migrate-locks');self.assertEqual(len(plan['legacy_directories']),3)
        with self.assertRaises(kb.KBError):self.call('migrate-locks','--apply')
        self.assertEqual((self.root/'.chao/state.json').read_bytes(),original)
        with mock.patch.object(os,'rmdir',side_effect=PermissionError('deny')),mock.patch.object(os,'unlink',side_effect=PermissionError('deny')):
            moved=self.call('migrate-locks','--apply','--quote','确认所有旧任务已停止，保留并迁移空目录锁')
            self.init();self.call('context','--task','升级任务')
        self.assertEqual(len(moved['preserved']),3)
        self.assertTrue(all((self.root/path).is_dir() for path in moved['preserved']))
        self.assertTrue((self.root/'.chao/LOCK').is_file())
        # The old protocol cannot acquire the retained file as a directory.
        with self.assertRaises(old.KBError):
            with old.lock(self.root):pass

    def test_nonempty_legacy_lock_is_never_moved_or_deleted(self):
        self.old_workspace();p=self.root/'.chao/LOCK';p.mkdir();(p/'unknown').write_bytes(b'keep')
        with self.assertRaises(kb.KBError):self.call('migrate-locks','--apply','--quote','确认迁移')
        self.assertEqual((p/'unknown').read_bytes(),b'keep')

    def test_lock_path_symlink_is_rejected(self):
        self.init();lock=self.root/'.chao/LOCK'
        lock.unlink();outside=self.base/'outside';outside.write_bytes(b'keep')
        self.symlink(outside,lock)
        with self.assertRaises(kb.KBError):self.call('context','--task','任务')
        self.assertEqual(outside.read_bytes(),b'keep')

    def test_corrupt_or_active_journal_still_blocks_writes(self):
        self.init();p=self.root/'.chao/pending-write.json';p.write_bytes(b'broken')
        with self.assertRaises((ValueError,kb.KBError)):self.call('profile','--field','身份','--value','不可写','--quote','不可写')
        self.assertEqual(p.read_bytes(),b'broken')

    def test_lock_path_hardlink_is_rejected(self):
        self.init();lock=self.root/'.chao/LOCK'
        lock.unlink();outside=self.base/'outside';outside.write_bytes(b'keep')
        os.link(outside,lock)
        with self.assertRaises(kb.KBError):self.call('context','--task','任务')
        self.assertEqual(outside.read_bytes(),b'keep')

    def test_runtime_has_no_implicit_delete_calls(self):
        import ast
        for path in [SCRIPT,REPO/'tools/install.py']:
            tree=ast.parse(path.read_text(encoding='utf-8'))
            calls=[node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)]
            self.assertFalse(set(calls)&{'unlink','rmdir','rmtree'},str(path))
