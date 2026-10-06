"""Check published documentation and package entry points."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self):
        for path in ROOT.rglob("*.md"):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if target.startswith(("http:", "https:", "#", "mailto:")):
                    continue
                target = target.split("#")[0]
                if target:
                    self.assertTrue((path.parent / target).exists(), (str(path), target))

    def test_versions_are_consistent(self):
        manifest = json.loads((ROOT / "skills/chao-knowledge/manifest.json").read_text(encoding="utf-8"))
        version = manifest["version"]
        for name in ["README.md", "docs/INSTALL.md", "skills/chao-knowledge/SKILL.md"]:
            self.assertIn(version, (ROOT / name).read_text(encoding="utf-8"))
        self.assertIn('VERSION = "' + version + '"', (ROOT / "skills/chao-knowledge/scripts/kb.py").read_text(encoding="utf-8"))

    def test_user_guide_covers_core_tasks(self):
        text = (ROOT / "docs/USAGE.md").read_text(encoding="utf-8")
        for term in ["第一次使用", "整理一份资料", "新对话", "撤销", "复盘"]:
            self.assertIn(term, text)

    def test_skill_example_paths_exist(self):
        skill = ROOT / "skills/chao-knowledge"
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        for name in re.findall(r"`(assets/[^`]+)`", text):
            self.assertTrue((skill / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
