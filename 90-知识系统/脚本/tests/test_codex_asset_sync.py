import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SYSTEM_ROOT = Path(__file__).resolve().parents[3]
SYNC = SYSTEM_ROOT / "80-Skill库" / "Codex备份" / "skills" / "codex-asset-sync" / "scripts" / "sync_codex_assets.py"
BEGIN = "<!-- BEGIN codex-kb -->"
END = "<!-- END codex-kb -->"


def run_sync(live: Path, config: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["CODEX_HOME"] = str(live)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SYNC), *args, "--config", str(config)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


class CodexAssetSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.live = root / "codex"
        self.vault = root / "notes"
        self.live_skill = self.live / "skills" / "demo"
        self.backup_skill = self.vault / "80-Skill库" / "Codex备份" / "skills" / "demo"
        self.live_skill.mkdir(parents=True)
        (self.live_skill / "SKILL.md").write_text("live version\n", encoding="utf-8")
        self.live_agents = self.live / "AGENTS.md"
        self.live_agents.write_text(
            "machine-local\n\n" + BEGIN + "\n## Codex 规则\nlive\n" + END + "\n",
            encoding="utf-8",
        )
        self.prompt_backup = self.vault / "90-知识系统" / "prompts" / "AGENTS.global.md"
        self.prompt_backup.parent.mkdir(parents=True)
        self.prompt_backup.write_text(BEGIN + "\n## Codex 规则\nbackup\n" + END + "\n", encoding="utf-8")
        self.config = self.live / "codex-assets.json"
        self.config.write_text(
            json.dumps({
                "vault": str(self.vault),
                "skills_dir": "80-Skill库/Codex备份/skills",
                "prompt_backup": "90-知识系统/prompts/AGENTS.global.md",
                "sync_skills": ["demo"],
            }),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_status_reports_differences(self) -> None:
        result = run_sync(self.live, self.config, "status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("demo: 仅本机存在", result.stdout)
        self.assertIn("Prompt: 有差异", result.stdout)

    def test_backup_then_restore(self) -> None:
        result = run_sync(self.live, self.config, "backup", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.backup_skill / "SKILL.md").read_text(encoding="utf-8"),
            "live version\n",
        )
        self.assertIn("live", self.prompt_backup.read_text(encoding="utf-8"))
        self.assertTrue((self.vault / "80-Skill库" / "Codex备份" / "manifest.json").is_file())

        (self.live_skill / "SKILL.md").write_text("changed locally\n", encoding="utf-8")
        result = run_sync(self.live, self.config, "restore", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.live_skill / "SKILL.md").read_text(encoding="utf-8"),
            "live version\n",
        )
        history = list((self.live / "skill-backups").glob("*/skills/demo/SKILL.md"))
        self.assertTrue(history)


if __name__ == "__main__":
    unittest.main()
