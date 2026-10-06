"""Deterministic unit/integration tests; no model, real client, or real user data."""
from __future__ import annotations
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/chao-knowledge/scripts/kb.py"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


kb = module("kb_test", SCRIPT)
installer = module("installer_test", REPO / "tools/install.py")


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="chao-tests-")
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "中文 工作区"
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def call(self, *args):
        return kb.execute(kb.build_parser().parse_args(["--root", str(self.root), *args]))

    def init(self):
        return self.call("init")

    def put(self, name="00-待整理/source.md", content="知识库整理资料。AI helps organize personal notes."):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def material(self, title="知识库资料", content="知识库整理资料。AI helps organize personal notes."):
        self.put(content=content)
        return self.call("ingest", "--title", title, "--file", "00-待整理/source.md")["material"]

    def proposal(self, *extra):
        return self.call("remember", "--key", "表达难度", "--text", "少用术语，多举例", *extra)["rule"]

    def activate(self, rule):
        return self.call("confirm", "--id", rule["id"], "--quote", "确认按这个范围保存")

    def output(self):
        self.put("00-待整理/draft.md", "这是虚构演示草稿，不含真实成绩。")
        return self.call("save", "--title", "演示稿", "--file", "00-待整理/draft.md")["output"]

    def metrics(self, changes=None):
        data = {"observed_at": "2026-10-06T12:00:00+08:00", "window_hours": 24,
                "views": 1000, "likes": 30, "saves": 20, "shares": None}
        data.update(changes or {})
        self.put("00-待整理/metrics.json", json.dumps(data, ensure_ascii=False))
        return "00-待整理/metrics.json"

    def symlink(self, target, path):
        try:
            path.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError):
            self.skipTest("OS does not allow creating symlinks")


class InitTests(WorkspaceCase):
    def test_initialize_creates_workspace(self):
        self.assertEqual(self.init()["status"], "initialized")
        self.assertTrue((self.root / ".chao/state.json").is_file())
        self.assertTrue((self.root / "开始使用.md").is_file())

    def test_repeat_init_keeps_existing_state(self):
        self.init()
        self.call("profile", "--field", "身份", "--value", "虚构演示者", "--quote", "我的演示身份")
        before = (self.root / ".chao/state.json").read_bytes()
        self.assertEqual(self.init()["status"], "already_initialized")
        self.assertEqual(before, (self.root / ".chao/state.json").read_bytes())

    def test_preserves_agents_and_gitignore(self):
        self.put("AGENTS.md", "# 原有规则\n请保留。\n")
        self.put(".gitignore", "old-private/\n")
        self.init()
        self.assertTrue((self.root / "AGENTS.md").read_text(encoding="utf-8").startswith("# 原有规则"))
        self.assertIn("old-private/", (self.root / ".gitignore").read_text(encoding="utf-8"))
        self.assertTrue((self.root / ".chao/backups/AGENTS_md.original.txt").exists())

    def test_existing_business_directory_is_not_changed(self):
        self.put("01-资料/important.txt", "不能改变")
        with self.assertRaises(kb.KBError): self.init()
        self.assertEqual((self.root / "01-资料/important.txt").read_text(encoding="utf-8"), "不能改变")
        self.assertFalse((self.root / ".chao").exists())

    def test_root_and_home_are_rejected(self):
        for value in (Path.home(), Path(Path.cwd().anchor)):
            with self.assertRaises(kb.KBError): kb.root_path(value)

    def test_symlink_root_is_rejected(self):
        link = self.base / "linked"
        self.symlink(self.root, link)
        with self.assertRaises(kb.KBError): kb.root_path(link)

    def test_symlink_agents_is_rejected_before_writes(self):
        outside = self.base / "external.md"
        outside.write_text("unchanged")
        self.symlink(outside, self.root / "AGENTS.md")
        with self.assertRaises(kb.KBError): self.init()
        self.assertEqual(outside.read_text(), "unchanged")
        self.assertFalse((self.root / ".chao").exists())

    def test_traversal_is_rejected(self):
        for path in ("../outside", "/outside", "dir\\outside"):
            with self.assertRaises(kb.KBError): kb.inside(self.root, path)

    def test_existing_lock_blocks_operation(self):
        self.init()
        (self.root / ".chao/LOCK").mkdir()
        with self.assertRaises(kb.KBError): self.call("health")
        self.assertTrue((self.root / ".chao/LOCK").exists())

    def test_lock_released_after_error(self):
        self.init()
        with self.assertRaises(kb.KBError): self.call("confirm", "--id", "missing", "--quote", "确认")
        self.assertFalse((self.root / ".chao/LOCK").exists())

    def test_corrupt_state_not_overwritten(self):
        self.init()
        p = self.root / ".chao/state.json"
        p.write_text("broken")
        with self.assertRaises(kb.KBError): self.call("health")
        self.assertEqual(p.read_text(), "broken")

    def test_source_repository_is_not_workspace(self):
        self.put("skills/chao-knowledge/SKILL.md", "source")
        with self.assertRaises(kb.KBError): self.init()

    def test_profile_keeps_source(self):
        self.init()
        r = self.call("profile", "--field", "身份", "--value", "虚构创作者", "--quote", "我使用虚构创作者身份演示")
        self.assertEqual(r["profile"]["source"], "user_statement")

    def test_hardlinked_config_is_rejected(self):
        p = self.base / "other.txt"; p.write_text("keep")
        try: os.link(p, self.root / "AGENTS.md")
        except OSError: self.skipTest("hardlinks unavailable")
        with self.assertRaises(kb.KBError): self.init()
        self.assertEqual(p.read_text(), "keep")


class IngestTests(WorkspaceCase):
    def setUp(self):
        super().setUp(); self.init()

    def test_text_import_preserves_original(self):
        p = self.put(content="标题\n原文不应改变。\n")
        before = p.read_bytes()
        r = self.material(content="标题\n原文不应改变。\n")
        self.assertEqual(before, p.read_bytes())
        self.assertEqual((self.root / r["original"]).read_bytes(), before)
        self.assertEqual(r["status"], "text_available")

    def test_duplicate_content_does_not_duplicate_material(self):
        first = self.material()
        self.put("00-待整理/second.md")
        result = self.call("ingest", "--title", "第二个标题", "--file", "00-待整理/second.md")
        self.assertEqual(result["status"], "duplicate")
        self.assertEqual(first["id"], result["material"]["id"])
        self.assertEqual(len(result["material"]["sources"]), 2)

    def test_utf8_bom_supported(self):
        p = self.root / "00-待整理/bom.txt"; p.write_bytes(b"\xef\xbb\xbf" + "知识库".encode())
        r = self.call("ingest", "--title", "BOM", "--file", str(p))["material"]
        self.assertEqual((self.root / r["text_path"]).read_text(encoding="utf-8"), "知识库")

    def test_non_utf8_rejected(self):
        p = self.root / "00-待整理/gbk.txt"; p.write_bytes("知识库".encode("gbk"))
        with self.assertRaises(kb.KBError): self.call("ingest", "--title", "bad", "--file", str(p))

    def test_secret_pattern_rejected(self):
        self.put(content="token: " + "ghp_" + "x" * 30)
        with self.assertRaises(kb.KBError): self.call("ingest", "--title", "secret", "--file", "00-待整理/source.md")
        self.assertFalse(kb.load(self.root)["materials"])

    def test_environment_file_rejected(self):
        self.put("00-待整理/.env.txt", "ordinary text")
        with self.assertRaises(kb.KBError): self.call("ingest", "--title", "env", "--file", "00-待整理/.env.txt")

    def test_binary_marked_needs_extraction(self):
        p = self.root / "00-待整理/sample.mp4"; p.write_bytes(b"FAKE TEST MEDIA NOT A REAL VIDEO")
        r = self.call("ingest", "--title", "fake media", "--file", str(p))["material"]
        self.assertEqual(r["status"], "needs_extraction")
        self.assertIsNone(r["text_path"])

    def test_url_is_link_only(self):
        r = self.call("ingest", "--title", "link", "--url", "https://example.com/a")["material"]
        self.assertEqual(r["status"], "link_only")
        self.assertIsNone(r["text_path"])

    def test_duplicate_url(self):
        args = ("ingest", "--title", "link", "--url", "https://example.com/a")
        self.call(*args)
        self.assertEqual(self.call(*args)["status"], "duplicate")

    def test_unsafe_urls_rejected(self):
        for url in ("file:///etc/passwd", "https://u:p@example.com", "https://example.com/?token=private"):
            with self.subTest(url=url), self.assertRaises(kb.KBError):
                self.call("ingest", "--title", "link", "--url", url)

    def test_external_file_requires_explicit_flag(self):
        p = self.base / "external.txt"; p.write_text("用户明确提供的虚构文件", encoding="utf-8")
        with self.assertRaises(kb.KBError): self.call("ingest", "--title", "external", "--file", str(p))
        r = self.call("ingest", "--title", "external", "--file", str(p), "--allow-external")
        self.assertEqual(r["status"], "saved")
        self.assertNotIn(str(self.base), json.dumps(r, ensure_ascii=False))

    def test_symlink_input_is_rejected(self):
        source = self.put()
        self.symlink(source, self.root / "00-待整理/link.txt")
        with self.assertRaises(kb.KBError): self.call("ingest", "--title", "link", "--file", "00-待整理/link.txt")

    def test_extraction_keeps_unverified_state(self):
        r = self.call("ingest", "--title", "link", "--url", "https://example.com/a")["material"]
        self.put("00-待整理/extracted.txt", "实际读取结果的测试替身，不是真实抓取。")
        out = self.call("extract", "--id", r["id"], "--file", "00-待整理/extracted.txt", "--method", "测试夹具")
        self.assertEqual(out["material"]["status"], "extracted_unverified")
        self.assertFalse(out["material"]["extraction"]["complete"])
        self.assertFalse(out["material"]["extraction"]["verified"])

    def test_extraction_cannot_overwrite_readable_content(self):
        r = self.material()
        with self.assertRaises(kb.KBError): self.call("extract", "--id", r["id"], "--file", "00-待整理/source.md", "--method", "test")

    def test_empty_text_rejected(self):
        self.put(content="   \n")
        with self.assertRaises(kb.KBError): self.call("ingest", "--title", "empty", "--file", "00-待整理/source.md")

    def test_unsupported_extension_rejected(self):
        self.put("00-待整理/code.sh", "echo hi")
        with self.assertRaises(kb.KBError): self.call("ingest", "--title", "shell", "--file", "00-待整理/code.sh")

    def test_invalid_tag_does_not_leave_material_files(self):
        self.put()
        with self.assertRaises(kb.KBError):
            self.call("ingest", "--title", "bad tag", "--file", "00-待整理/source.md", "--tag", "")
        self.assertFalse(list((self.root / "01-资料").iterdir()))

    def test_text_size_limit(self):
        with self.assertRaises(kb.KBError): kb.decode(b"a" * (kb.MAX_TEXT + 1))


class SearchTests(WorkspaceCase):
    def setUp(self):
        super().setUp(); self.init()

    def test_chinese_search_has_line_evidence(self):
        row = self.material(content="开头\n知识库帮助找资料。\n结尾")
        result = self.call("search", "--query", "知识库")["results"][0]
        self.assertEqual(result["id"], row["id"])
        self.assertGreaterEqual(result["line_start"], 1)
        self.assertTrue(result["excerpt_only"])

    def test_english_search(self):
        self.material()
        self.assertTrue(self.call("search", "--query", "personal notes")["results"])

    def test_no_matches_is_not_fabricated(self):
        self.material()
        self.assertFalse(self.call("search", "--query", "quantum-entanglement")["results"])

    def test_changed_text_is_skipped(self):
        row = self.material()
        (self.root / row["text_path"]).write_text("被改变的知识库正文", encoding="utf-8")
        result = self.call("search", "--query", "知识库")
        self.assertFalse(result["results"])
        self.assertTrue(result["warnings"])

    def test_health_flags_missing_original(self):
        row = self.material()
        (self.root / row["original"]).unlink()
        self.assertTrue(any(r["kind"] == "missing" for r in self.call("health")["findings"]))

    def test_invalid_limit_rejected(self):
        with self.assertRaises(kb.KBError): self.call("search", "--query", "test", "--limit", "99")

    def test_link_only_not_returned_as_read_text(self):
        self.call("ingest", "--title", "知识库", "--url", "https://example.com")
        self.assertFalse(self.call("search", "--query", "知识库")["results"])

    def test_profile_budget_is_explicit(self):
        for field in ("身份", "受众", "当前目标"):
            self.call("profile", "--field", field, "--value", "长" * 1999, "--quote", "用户明确提供")
        result = self.call("context", "--task", "写口播")
        self.assertGreater(result["profile_omitted"], 0)


class RuleTests(WorkspaceCase):
    def setUp(self):
        super().setUp(); self.init()

    def test_proposed_rule_is_not_active(self):
        self.proposal()
        self.assertFalse(self.call("context", "--task", "写口播")["rules"])

    def test_confirmed_rule_is_active(self):
        row = self.proposal(); self.activate(row)
        self.assertEqual(self.call("context", "--task", "写口播")["rules"][0]["id"], row["id"])

    def test_confirmation_requires_nonempty_quote(self):
        row = self.proposal()
        with self.assertRaises(kb.KBError): self.call("confirm", "--id", row["id"], "--quote", "")

    def test_scoped_rule_only_matches_its_context(self):
        row = self.proposal("--scope", "task=口播", "--scope", "audience=AI初学者"); self.activate(row)
        self.assertFalse(self.call("context", "--task", "技术方案", "--scope", "task=报告")["rules"])
        self.assertFalse(self.call("context", "--task", "普通任务")["rules"])
        self.assertTrue(self.call("context", "--task", "写稿", "--scope", "task=口播", "--scope", "audience=AI初学者")["rules"])

    def test_specific_scope_precedes_global(self):
        broad = self.proposal(); self.activate(broad)
        narrow = self.call("remember", "--key", "表达难度", "--text", "技术报告保留术语", "--scope", "task=报告")["rule"]
        self.activate(narrow)
        rules = self.call("context", "--task", "技术报告", "--scope", "task=报告")["rules"]
        self.assertEqual(rules[0]["id"], narrow["id"])

    def test_conflict_requires_explicit_replacement(self):
        old = self.proposal(); self.activate(old)
        new = self.call("remember", "--key", "表达难度", "--text", "保持术语")["rule"]
        with self.assertRaises(kb.KBError): self.activate(new)
        self.call("confirm", "--id", new["id"], "--quote", "确认替换旧规则", "--replaces", old["id"])
        active = self.call("context", "--task", "写稿")["rules"]
        self.assertEqual([r["id"] for r in active], [new["id"]])

    def test_wrong_replacement_rejected(self):
        row = self.proposal()
        with self.assertRaises(kb.KBError): self.call("confirm", "--id", row["id"], "--quote", "确认", "--replaces", "wrong")

    def test_revoke_stops_retrieval(self):
        row = self.proposal(); self.activate(row)
        self.call("revoke", "--id", row["id"], "--quote", "撤销")
        self.assertFalse(self.call("context", "--task", "写稿")["rules"])
        self.assertEqual(self.call("rules")["rules"][0]["status"], "revoked")

    def test_forget_removes_current_rule_text(self):
        row = self.proposal(); self.activate(row)
        self.call("forget", "--id", row["id"], "--quote", "删除记录")
        self.assertNotIn("少用术语，多举例", (self.root / ".chao/state.json").read_text(encoding="utf-8"))

    def test_expired_rule_excluded(self):
        row = self.proposal(); self.activate(row)
        state = kb.load(self.root); state["rules"][row["id"]]["expires_on"] = "2000-01-01"; kb.save_state(self.root, state)
        self.assertFalse(self.call("context", "--task", "写稿")["rules"])
        self.assertTrue(any(x["kind"] == "expired_rule" for x in self.call("health")["findings"]))

    def test_past_expiry_and_invalid_scope_rejected(self):
        for extras in (("--expires", "2000-01-01"), ("--scope", "unknown=yes"), ("--scope", "task=a", "--scope", "task=b")):
            with self.subTest(extras=extras), self.assertRaises(kb.KBError): self.proposal(*extras)

    def test_rule_duplicate_is_idempotent(self):
        first = self.proposal()
        self.assertEqual(first["id"], self.proposal()["id"])

    def test_revoked_rule_cannot_be_reconfirmed(self):
        row = self.proposal(); self.activate(row)
        self.call("revoke", "--id", row["id"], "--quote", "撤销")
        with self.assertRaises(kb.KBError): self.activate(row)

    def test_disk_persistence_across_real_subprocesses_not_gui(self):
        row = self.proposal("--scope", "task=口播"); self.activate(row)
        env = dict(os.environ, PYTHONUTF8="1")
        r = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), "context", "--task", "写口播", "--scope", "task=口播"], capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["result"]["rules"][0]["id"], row["id"])


class OutputFeedbackTests(WorkspaceCase):
    def setUp(self):
        super().setUp(); self.init()

    def test_output_starts_as_draft(self):
        row = self.output()
        self.assertEqual(row["status"], "draft")
        self.assertTrue((self.root / ("02-作品/" + row["id"] + ".sources.json")).is_file())

    def test_readable_source_attached(self):
        source = self.material(); self.put("00-待整理/draft.md", "知识库草稿")
        row = self.call("save", "--title", "稿", "--file", "00-待整理/draft.md", "--source", source["id"])["output"]
        self.assertEqual(row["sources"][0]["id"], source["id"])

    def test_link_only_cannot_be_used_as_read_source(self):
        source = self.call("ingest", "--title", "link", "--url", "https://example.com")["material"]
        self.put("00-待整理/draft.md", "草稿")
        with self.assertRaises(kb.KBError): self.call("save", "--title", "稿", "--file", "00-待整理/draft.md", "--source", source["id"])

    def test_versions_do_not_overwrite(self):
        old = self.output()
        self.put("00-待整理/draft.md", "新版本")
        new = self.call("save", "--title", "新稿", "--file", "00-待整理/draft.md", "--parent", old["id"])["output"]
        self.assertNotEqual(old["id"], new["id"])
        self.assertEqual(new["parent"], old["id"])
        self.assertIn("虚构", (self.root / old["path"]).read_text(encoding="utf-8"))

    def test_approval_requires_unchanged_draft(self):
        row = self.output()
        (self.root / row["path"]).write_text("外部修改", encoding="utf-8")
        with self.assertRaises(kb.KBError): self.call("approve", "--id", row["id"], "--quote", "核对通过")

    def test_changed_source_blocks_approval(self):
        source = self.material()
        self.put("00-待整理/draft.md", "基于资料的草稿")
        row = self.call("save", "--title", "稿", "--file", "00-待整理/draft.md", "--source", source["id"])["output"]
        (self.root / source["text_path"]).write_text("被改变的来源", encoding="utf-8")
        with self.assertRaises(kb.KBError):
            self.call("approve", "--id", row["id"], "--quote", "确认")

    def test_approved_does_not_mean_published(self):
        row = self.output()
        out = self.call("approve", "--id", row["id"], "--quote", "我已核对")
        self.assertEqual(out["output"]["status"], "approved")
        self.assertIn("不等于已发布", out["warning"])

    def test_feedback_rates(self):
        row = self.output()
        out = self.call("feedback", "--id", row["id"], "--file", self.metrics())
        self.assertEqual(out["rates"]["likes_rate"], 0.03)
        self.assertIsNone(out["rates"]["shares_rate"])
        self.assertFalse(kb.load(self.root)["rules"])

    def test_unknown_or_zero_denominator_yields_null(self):
        row = self.output()
        for views in (None, 0):
            out = self.call("feedback", "--id", row["id"], "--file", self.metrics({"views": views}))
            self.assertIsNone(out["rates"]["likes_rate"])

    def test_invalid_metrics_rejected(self):
        row = self.output()
        for change in ({"likes": -1}, {"views": True}, {"likes": 1.2}, {"window_hours": 0}, {"window_hours": float("nan")}, {"observed_at": "2026-01-01T00:00:00"}, {"unsupported": 3}):
            with self.subTest(change=change), self.assertRaises(kb.KBError):
                self.call("feedback", "--id", row["id"], "--file", self.metrics(change))

    def test_feedback_preserves_snapshots(self):
        row = self.output()
        self.call("feedback", "--id", row["id"], "--file", self.metrics())
        self.call("feedback", "--id", row["id"], "--file", self.metrics({"window_hours": 72, "views": 2000}))
        self.assertEqual(len(kb.load(self.root)["feedback"]), 2)

    def test_count_inconsistency_warns(self):
        row = self.output()
        out = self.call("feedback", "--id", row["id"], "--file", self.metrics({"likes": 2000}))
        self.assertGreater(len(out["warnings"]), 1)


class PackageTests(WorkspaceCase):
    def test_skill_metadata_and_references(self):
        skill = REPO / "skills/chao-knowledge/SKILL.md"
        text = skill.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: chao-knowledge\n"))
        self.assertIn("description:", text)
        self.assertLess(len(text.splitlines()), 500)
        import re
        for link in re.findall(r"\]\((references/[^)]+)\)", text):
            self.assertTrue((skill.parent / link).is_file(), link)

    def test_package_hashes_and_zip_layout(self):
        manifest = json.loads((installer.SOURCE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["files"], installer.inventory(installer.SOURCE))
        path = REPO / ("dist/chao-knowledge-v" + manifest["version"] + ".zip")
        with zipfile.ZipFile(path) as z:
            self.assertIn("chao-knowledge/SKILL.md", z.namelist())
            self.assertFalse(any(".." in Path(n).parts or "__pycache__" in n for n in z.namelist()))
            self.assertEqual(z.read("chao-knowledge/scripts/kb.py"), SCRIPT.read_bytes())
        recorded = (REPO / "dist/SHA256SUMS").read_text().split()[0]
        self.assertEqual(recorded, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_install_and_reinstall_are_safe(self):
        first = installer.install(str(self.root), True)
        self.assertEqual(first["status"], "installed")
        second = installer.install(str(self.root), True)
        self.assertEqual(second["status"], "already_installed")
        self.assertEqual(second["workspace"]["status"], "already_initialized")

    def test_changed_install_is_not_overwritten(self):
        installer.install(str(self.root))
        p = self.root / ".codebuddy/skills/chao-knowledge/SKILL.md"
        p.write_text("user customization")
        with self.assertRaises(ValueError): installer.install(str(self.root))
        self.assertEqual(p.read_text(), "user customization")

    def test_install_rejects_symlink_directory(self):
        external = self.base / "external"; external.mkdir()
        self.symlink(external, self.root / ".codebuddy")
        with self.assertRaises(Exception): installer.install(str(self.root))
        self.assertFalse(list(external.iterdir()))

    def test_installed_script_runs_independently(self):
        installer.install(str(self.root), True)
        script = self.root / ".codebuddy/skills/chao-knowledge/scripts/kb.py"
        result = subprocess.run([sys.executable, str(script), "--root", str(self.root), "health"], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONUTF8="1"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_public_samples_are_explicitly_fictional(self):
        sample = (installer.SOURCE / "assets/sample-source.md").read_text(encoding="utf-8")
        self.assertIn("虚构", sample)
        profile = json.loads((installer.SOURCE / "assets/sample-profile.json").read_text(encoding="utf-8"))
        self.assertIn("虚构", profile["notice"])


if __name__ == "__main__":
    unittest.main()
