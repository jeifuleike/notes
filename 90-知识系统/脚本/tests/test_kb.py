from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SYSTEM_ROOT = Path(__file__).resolve().parents[2]
KB = SYSTEM_ROOT / "脚本" / "kb.py"


def run_kb(vault: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(KB), "--vault", str(vault), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


class KbTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        (self.vault / "90-知识系统").mkdir(parents=True)
        (self.vault / "90-知识系统" / "模板").mkdir(parents=True)
        (self.vault / "00-Inbox" / "审核").mkdir(parents=True)
        (self.vault / "00-Inbox" / "已归档").mkdir(parents=True)
        (self.vault / "20-后端" / "NestJS").mkdir(parents=True)
        for name in ("每日成长-任务时长模板.md", "休息日-任务时长模板.md"):
            (self.vault / "90-知识系统" / "模板" / name).write_text(
                (SYSTEM_ROOT / "模板" / name).read_text(encoding="utf-8"), encoding="utf-8"
            )
        config = SYSTEM_ROOT / "config.json"
        (self.vault / "90-知识系统" / "config.json").write_text(
            config.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (self.vault / "00-Inbox" / "00-收集箱.md").write_text(
            "---\ntype: dashboard\n---\n\n# 收集箱\n", encoding="utf-8"
        )
        self.note = self.vault / "20-后端" / "NestJS" / "01-Provider依赖注入与作用域.md"
        self.note.write_text(
            "---\ntitle: Provider 依赖注入与作用域\ntype: knowledge\ntags: [nestjs, 依赖注入]\n"
            "---\n\n# Provider 依赖注入与作用域\n\nREQUEST scope 会向上传染，整条依赖链变成请求级实例。\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_capture_writes_inbox_item(self) -> None:
        result = run_kb(
            self.vault, "capture", "--title", "Provider 作用域踩坑", "--reason", "gotcha",
            "--content", "REQUEST scope 会向上传染，整条依赖链变成请求级实例。",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.vault / result.stdout.strip()
        self.assertTrue(target.is_file())
        text = target.read_text(encoding="utf-8")
        self.assertIn("type: inbox", text)
        self.assertIn("capture_reason: gotcha", text)

    def test_inbox_skips_dashboard(self) -> None:
        run_kb(self.vault, "capture", "--title", "一条收集", "--content", "普通收集内容。")
        result = run_kb(self.vault, "inbox")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("共 1 条", result.stdout)
        self.assertNotIn("收集箱", result.stdout)

    def test_review_generates_report_with_candidates(self) -> None:
        run_kb(
            self.vault, "capture", "--title", "Provider 作用域踩坑", "--reason", "gotcha",
            "--content", "REQUEST scope 会向上传染，整条依赖链变成请求级实例。",
        )
        result = run_kb(self.vault, "review")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.vault / result.stdout.strip()
        self.assertTrue(report.is_file())
        text = report.read_text(encoding="utf-8")
        self.assertIn("type: review-report", text)
        self.assertIn("20-后端/NestJS/01-Provider依赖注入与作用域", text)
        self.assertIn("待确认", text)
        log = (self.vault / "90-知识系统" / "处理日志.md").read_text(encoding="utf-8")
        self.assertIn("| review |", log)

    def test_review_dry_run_writes_nothing(self) -> None:
        run_kb(self.vault, "capture", "--title", "一条收集", "--content", "普通收集内容。")
        result = run_kb(self.vault, "review", "--dry-run")
        self.assertIn("# 临时区审核报告", result.stdout)
        self.assertEqual(list((self.vault / "00-Inbox" / "审核").glob("*.md")), [])

    def test_archive_moves_and_marks(self) -> None:
        captured = run_kb(self.vault, "capture", "--title", "待归档", "--content", "待归档内容。")
        source = captured.stdout.strip()
        result = run_kb(self.vault, "archive", source)
        self.assertEqual(result.returncode, 0, result.stderr)
        destination = self.vault / result.stdout.strip()
        self.assertTrue(destination.is_file())
        self.assertIn("已归档", destination.as_posix())
        self.assertIn("status: archived", destination.read_text(encoding="utf-8"))
        self.assertFalse((self.vault / source).exists())

    def test_lint_detects_broken_link(self) -> None:
        (self.vault / "20-后端" / "断链.md").write_text(
            "---\ntitle: 断链\n---\n\n# 断链\n\n见 [[不存在的笔记]]。\n", encoding="utf-8"
        )
        result = run_kb(self.vault, "lint")
        self.assertEqual(result.returncode, 1)
        self.assertIn("断链", result.stdout)

    def test_lint_ignores_links_in_code(self) -> None:
        (self.vault / "20-后端" / "代码示例.md").write_text(
            "---\ntitle: 代码示例\n---\n\n"
            "# 代码示例\n\n"
            "行内示例：`[[wiki-link]]`。\n\n"
            "```markdown\n[[代码块占位符]]\n```\n",
            encoding="utf-8",
        )
        result = run_kb(self.vault, "lint")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("代码块占位符", result.stdout)

    def test_search_reports_path_and_line(self) -> None:
        result = run_kb(self.vault, "search", "依赖注入", "--limit", "5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("20-后端/NestJS/01-Provider依赖注入与作用域.md:", result.stdout)

    def test_index_writes_home_and_is_idempotent(self) -> None:
        result = run_kb(self.vault, "index")
        self.assertEqual(result.returncode, 0, result.stderr)
        home = self.vault / "00-知识库首页.md"
        text = home.read_text(encoding="utf-8")
        self.assertIn("<!-- BEGIN kb-index -->", text)
        self.assertIn("20-后端/NestJS/01-Provider依赖注入与作用域", text)
        run_kb(self.vault, "index")
        again = home.read_text(encoding="utf-8")
        self.assertEqual(again.count("<!-- BEGIN kb-index -->"), 1)

    def test_audit_writes_monthly_report(self) -> None:
        result = run_kb(self.vault, "audit")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.vault / result.stdout.splitlines()[0].strip()
        text = report.read_text(encoding="utf-8")
        self.assertIn("type: audit-report", text)
        self.assertIn("笔记总数", text)

    def test_export_writes_jsonl(self) -> None:
        result = run_kb(self.vault, "export")
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.vault / "90-知识系统" / "导出" / "qmd.jsonl"
        self.assertTrue(target.is_file())
        lines = [line for line in target.read_text(encoding="utf-8").splitlines() if line]
        self.assertGreaterEqual(len(lines), 1)
        self.assertIn("Provider", "\n".join(lines))

    def test_daily_workday_uses_work_template(self) -> None:
        result = run_kb(self.vault, "daily", "--date", "2026-11-18")
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.vault / result.stdout.strip()
        text = target.read_text(encoding="utf-8")
        self.assertIn("# 🌙 工作日成长", text)
        self.assertIn("date: '2026-11-18'", text)

    def test_daily_weekend_uses_rest_template(self) -> None:
        result = run_kb(self.vault, "daily", "--date", "2026-11-21")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.vault / result.stdout.strip()).read_text(encoding="utf-8")
        self.assertIn("day_type: 休息日", text)

    def test_daily_respects_explicit_rest_day(self) -> None:
        config_path = self.vault / "90-知识系统" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["daily"]["rest_days"] = ["2026-11-18"]
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        result = run_kb(self.vault, "daily", "--date", "2026-11-18")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.vault / result.stdout.strip()).read_text(encoding="utf-8")
        self.assertIn("day_type: 休息日", text)

    def test_daily_does_not_overwrite_existing(self) -> None:
        target = self.vault / "50-每日自律" / "日报" / "2026-11" / "2026-11-18.md"
        target.parent.mkdir(parents=True)
        target.write_text("already here", encoding="utf-8")
        result = run_kb(self.vault, "daily", "--date", "2026-11-18")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("已存在", result.stdout)
        self.assertEqual(target.read_text(encoding="utf-8"), "already here")

    def test_hook_prompt_requires_what_and_why(self) -> None:
        config_path = self.vault / "hook-config.json"
        config_path.write_text(
            json.dumps({
                "enabled": True,
                "vault": str(self.vault),
                "scope": "all-projects",
                "cooldown_minutes": 20,
                "min_chars": 40,
            }),
            encoding="utf-8",
        )
        payload = {
            "cwd": str(self.vault),
            "stop_hook_active": False,
            "permission_mode": "default",
            "last_assistant_message": (
                "这次排障的根因是 provider scope 向上传染，决定以后默认不用 REQUEST scope，"
                "修复了性能问题，验证通过。下次遇到类似问题先检查依赖链。"
            ),
            "session_id": "test",
            "turn_id": "test",
        }
        env = dict(os.environ)
        env["KB_CAPTURE_CONFIG"] = str(config_path)
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, str(SYSTEM_ROOT / "安装" / "kb-capture-ask.py")],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"decision": "block"', result.stdout)
        self.assertIn("要存什么", result.stdout)
        self.assertIn("为什么值得存", result.stdout)
        self.assertIn("单次小修复", result.stdout)


if __name__ == "__main__":
    unittest.main()
