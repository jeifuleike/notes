#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


HOME = Path.home()
CONFIG_PATH = Path(os.environ.get("KB_CAPTURE_CONFIG", HOME / ".codex" / "kb-capture.json"))
STATE_PATH = CONFIG_PATH.with_name("kb-capture-state.json")
LOG_PATH = CONFIG_PATH.with_name("kb-capture.log")

STRONG_SIGNALS = (
    "根因",
    "踩坑",
    "方案定为",
    "以后都",
    "验证通过",
    "修复了",
    "教训",
    "root cause",
    "gotcha",
    "decision",
    "workflow",
    "lesson",
)

SECONDARY_SIGNALS = (
    "决定",
    "结论",
    "流程",
    "规范",
    "下次",
    "注意",
    "always",
    "never",
    "fixed by",
)

ASK_MARKERS = (
    "建议沉淀",
    "值得沉淀",
    "要存什么",
    "要沉淀",
    "沉淀到",
    "要记到",
    "记到 00-Inbox",
    "KB-CAPTURE-ASK",
)


def setup_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def load_config() -> dict[str, Any] | None:
    if not CONFIG_PATH.is_file():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def append_log(message: str) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")
    except OSError:
        pass


def is_inside(path: str, root: str) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except (ValueError, OSError):
        return False


def already_asked(text: str) -> bool:
    return any(marker in text for marker in ASK_MARKERS)


def should_ask(text: str, min_chars: int) -> bool:
    if len(text) < min_chars:
        return False
    lowered = text.lower()
    strong = sum(1 for signal in STRONG_SIGNALS if signal in lowered)
    secondary = sum(1 for signal in SECONDARY_SIGNALS if signal in lowered)
    return strong >= 2 or (strong >= 1 and secondary >= 1)


def cooldown_active(config: dict[str, Any]) -> bool:
    if not STATE_PATH.is_file():
        return False
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    last = state.get("last_asked_at")
    if not isinstance(last, str):
        return False
    try:
        last_time = datetime.fromisoformat(last)
    except ValueError:
        return False
    minutes = int(config.get("cooldown_minutes", 20))
    return datetime.now() - last_time < timedelta(minutes=minutes)


def save_state(payload: dict[str, Any]) -> None:
    state = {
        "last_asked_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": payload.get("session_id"),
        "turn_id": payload.get("turn_id"),
    }
    try:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def decide(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any] | None:
    if not config.get("enabled", True):
        return None
    if payload.get("stop_hook_active"):
        return None
    if payload.get("permission_mode") == "plan":
        return None
    if config.get("scope", "all-projects") == "vault-only":
        vault = config.get("vault")
        cwd = payload.get("cwd")
        if not isinstance(vault, str) or not isinstance(cwd, str) or not is_inside(cwd, vault):
            return None
    text = payload.get("last_assistant_message") or ""
    if not isinstance(text, str) or already_asked(text):
        return None
    if cooldown_active(config):
        return None
    if not should_ask(text, int(config.get("min_chars", 80))):
        return None
    save_state(payload)
    return {
        "decision": "block",
        "reason": (
            "先判断是否值得提议：只有通用知识（原理、方法、模式、决策框架、边界）"
            "或提效资产（可复用流程、脚本、模板、检查清单）才提议；"
            "单次小修复、偶发环境问题、一次性命令直接跳过。"
            "值得提议时，先用三行说明：要存什么（标题 + 最多 3 条要点）、"
            "为什么值得存（未来什么场景会用）、去向 00-Inbox，"
            "然后只问一句是否记到 00-Inbox。不要写文件，等用户回答。"
        ),
    }


def selftest() -> int:
    config = load_config()
    if config is None:
        print(f"config missing: {CONFIG_PATH}")
        return 1
    print(f"config: {CONFIG_PATH}")
    print(f"enabled: {config.get('enabled', True)}")
    print(f"vault: {config.get('vault', '')}")
    print(f"scope: {config.get('scope', 'all-projects')}")
    return 0


def simulate(text: str, cwd: str) -> int:
    config = load_config()
    if config is None:
        print(json.dumps({"decision": "allow", "reason": "config missing"}, ensure_ascii=False))
        return 0
    payload = {
        "cwd": cwd,
        "stop_hook_active": False,
        "permission_mode": "default",
        "last_assistant_message": text,
        "session_id": "simulate",
        "turn_id": "simulate",
    }
    result = decide(payload, config)
    print(json.dumps(result or {"decision": "allow"}, ensure_ascii=False))
    return 0


def main() -> int:
    setup_stdout()
    if "--selftest" in sys.argv:
        return selftest()
    if "--simulate" in sys.argv:
        index = sys.argv.index("--simulate")
        text = sys.argv[index + 1] if index + 1 < len(sys.argv) else ""
        cwd = str(Path.cwd())
        return simulate(text, cwd)

    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace").lstrip("\ufeff")
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        append_log("invalid json input")
        return 0
    config = load_config()
    if config is None:
        return 0
    if config.get("debug"):
        append_log(
            f"invoke chars={len(raw)} session={payload.get('session_id')} "
            f"active={payload.get('stop_hook_active')}"
        )
    result = decide(payload, config)
    if result is not None:
        append_log(f"ask session={payload.get('session_id')} turn={payload.get('turn_id')}")
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        append_log(f"error {type(exc).__name__}: {exc}")
        raise SystemExit(0)
