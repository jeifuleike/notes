#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


BEGIN = "<!-- BEGIN codex-kb -->"
END = "<!-- END codex-kb -->"
PROMPT_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
DEFAULT_SKILLS = ["kb-curator", "kb-query", "codex-asset-sync"]


def setup_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def load_config(override: str | None = None) -> dict[str, Any]:
    if override:
        path = Path(override)
    else:
        path = codex_home() / "codex-assets.json"
    if not path.is_file():
        raise SystemExit(f"找不到同步配置：{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("vault"):
        raise SystemExit(f"同步配置无效：{path}")
    data["_config_path"] = str(path)
    return data


def paths(config: dict[str, Any]) -> dict[str, Path]:
    vault = Path(config["vault"])
    live = codex_home()
    return {
        "live": live,
        "live_skills": live / "skills",
        "live_agents": live / "AGENTS.md",
        "vault": vault,
        "backup_skills": vault / config.get("skills_dir", "80-Skill库/Codex备份/skills"),
        "backup_prompt": vault / config.get("prompt_backup", "90-知识系统/prompts/AGENTS.global.md"),
        "manifest": vault / "80-Skill库" / "Codex备份" / "manifest.json",
        "skill_history": live / "skill-backups",
    }


def skills_to_sync(config: dict[str, Any]) -> list[str]:
    skills = config.get("sync_skills") or DEFAULT_SKILLS
    return [str(name) for name in skills if str(name) and str(name) != ".system"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in {".git", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.name.endswith((".pyc", ".pyo")):
            continue
        result[rel] = sha256(path)
    return result


def prompt_block(text: str) -> str | None:
    match = PROMPT_RE.search(text)
    return match.group(0).strip() if match else None


def compare_tree(live: Path, backup: Path) -> dict[str, Any]:
    live_hashes = tree_hashes(live)
    backup_hashes = tree_hashes(backup)
    common = sorted(set(live_hashes) & set(backup_hashes))
    changed = [key for key in common if live_hashes[key] != backup_hashes[key]]
    return {
        "exists_live": live.is_dir(),
        "exists_backup": backup.is_dir(),
        "live_only": sorted(set(live_hashes) - set(backup_hashes)),
        "backup_only": sorted(set(backup_hashes) - set(live_hashes)),
        "changed": changed,
        "same": not (set(live_hashes) - set(backup_hashes))
        and not (set(backup_hashes) - set(live_hashes))
        and not changed,
    }


def status(config: dict[str, Any]) -> dict[str, Any]:
    p = paths(config)
    skills: dict[str, Any] = {}
    for name in skills_to_sync(config):
        skills[name] = compare_tree(p["live_skills"] / name, p["backup_skills"] / name)
    prompt: dict[str, Any] = {"exists_live": p["live_agents"].is_file(), "exists_backup": p["backup_prompt"].is_file()}
    if prompt["exists_live"] and prompt["exists_backup"]:
        live_block = prompt_block(p["live_agents"].read_text(encoding="utf-8"))
        backup_block = prompt_block(p["backup_prompt"].read_text(encoding="utf-8"))
        prompt["same"] = live_block == backup_block
        prompt["live_has_block"] = live_block is not None
        prompt["backup_has_block"] = backup_block is not None
        prompt["sha_live"] = hashlib.sha256((live_block or "").encode("utf-8")).hexdigest()[:12]
        prompt["sha_backup"] = hashlib.sha256((backup_block or "").encode("utf-8")).hexdigest()[:12]
    return {
        "codex_home": str(p["live"]),
        "vault": str(p["vault"]),
        "skills": skills,
        "prompt": prompt,
    }


def replace_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".codex-sync-", dir=destination.parent))
    try:
        staged = staging / "payload"
        shutil.copytree(source, staged)
        if destination.exists():
            old = destination.with_name(destination.name + ".old")
            if old.exists():
                shutil.rmtree(old)
            destination.rename(old)
            try:
                staged.rename(destination)
            except Exception:
                old.rename(destination)
                raise
            shutil.rmtree(old)
        else:
            staged.rename(destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def backup_skill(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    replace_tree(source, destination)


def backup_prompt(live_agents: Path, backup_prompt: Path) -> None:
    if not live_agents.is_file():
        raise FileNotFoundError(live_agents)
    block = prompt_block(live_agents.read_text(encoding="utf-8"))
    if not block:
        raise ValueError("本机 AGENTS.md 缺少 codex-kb 标记块")
    backup_prompt.parent.mkdir(parents=True, exist_ok=True)
    backup_prompt.write_text(block.rstrip() + "\n", encoding="utf-8", newline="\n")


def backup(config: dict[str, Any], selected: list[str]) -> dict[str, Any]:
    p = paths(config)
    changed: list[str] = []
    for name in selected:
        source = p["live_skills"] / name
        destination = p["backup_skills"] / name
        if source.exists():
            backup_skill(source, destination)
            changed.append(f"skills/{name}")
    backup_prompt(p["live_agents"], p["backup_prompt"])
    changed.append("prompts/AGENTS.global.md")
    write_manifest(config, changed)
    return {"action": "backup", "changed": changed, "manifest": str(p["manifest"])}


def save_live_skill(source: Path, history_root: Path, name: str, stamp: str) -> None:
    if source.exists():
        target = history_root / stamp / "skills" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)


def replace_prompt(live_agents: Path, backup_prompt: Path) -> None:
    if not backup_prompt.is_file():
        raise FileNotFoundError(backup_prompt)
    block = prompt_block(backup_prompt.read_text(encoding="utf-8"))
    if not block:
        raise ValueError("备份提示词缺少 codex-kb 标记块")
    original = live_agents.read_text(encoding="utf-8") if live_agents.is_file() else ""
    if PROMPT_RE.search(original):
        updated = PROMPT_RE.sub(lambda _: block, original, count=1)
    else:
        updated = original.rstrip() + "\n\n" + block + "\n"
    live_agents.write_text(updated, encoding="utf-8", newline="\n")


def restore(config: dict[str, Any], selected: list[str]) -> dict[str, Any]:
    p = paths(config)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    changed: list[str] = []
    for name in selected:
        source = p["backup_skills"] / name
        destination = p["live_skills"] / name
        if not source.exists():
            continue
        save_live_skill(destination, p["skill_history"], name, stamp)
        replace_tree(source, destination)
        changed.append(f"skills/{name}")
    if p["live_agents"].is_file():
        history = p["skill_history"] / stamp / "AGENTS.md"
        history.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p["live_agents"], history)
    replace_prompt(p["live_agents"], p["backup_prompt"])
    changed.append("AGENTS.md#codex-kb")
    return {"action": "restore", "changed": changed, "history": str(p["skill_history"] / stamp)}


def write_manifest(config: dict[str, Any], changed: list[str]) -> None:
    p = paths(config)
    skills = {
        name: tree_hashes(p["backup_skills"] / name)
        for name in skills_to_sync(config)
        if (p["backup_skills"] / name).is_dir()
    }
    prompt = ""
    if p["backup_prompt"].is_file():
        prompt = prompt_block(p["backup_prompt"].read_text(encoding="utf-8")) or ""
    payload = {
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "changed": changed,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if prompt
        else "",
        "skills": skills,
    }
    p["manifest"].parent.mkdir(parents=True, exist_ok=True)
    p["manifest"].write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_status(result: dict[str, Any]) -> None:
    print(f"Codex: {result['codex_home']}")
    print(f"Notes: {result['vault']}")
    print("Skills:")
    for name, item in result["skills"].items():
        if item["same"]:
            state = "一致"
        elif not item["exists_live"]:
            state = "仅备份存在"
        elif not item["exists_backup"]:
            state = "仅本机存在"
        else:
            state = "有差异"
        details = []
        if item["changed"]:
            details.append(f"修改 {len(item['changed'])}")
        if item["live_only"]:
            details.append(f"本机新增 {len(item['live_only'])}")
        if item["backup_only"]:
            details.append(f"备份独有 {len(item['backup_only'])}")
        suffix = f" ({', '.join(details)})" if details else ""
        print(f"  - {name}: {state}{suffix}")
    prompt = result["prompt"]
    if prompt.get("same"):
        print("Prompt: 一致")
    elif not prompt["exists_live"]:
        print("Prompt: 本机缺少 AGENTS.md")
    elif not prompt["exists_backup"]:
        print("Prompt: 备份缺少 AGENTS.global.md")
    elif not prompt.get("live_has_block"):
        print("Prompt: 本机 AGENTS.md 缺少 codex-kb 标记")
    elif not prompt.get("backup_has_block"):
        print("Prompt: 备份缺少 codex-kb 标记")
    else:
        print("Prompt: 有差异")


def main() -> int:
    setup_stdout()
    parser = argparse.ArgumentParser(description="Sync Codex skills and prompt block to the notes backup.")
    parser.add_argument("action", choices=["status", "backup", "restore"])
    parser.add_argument("--config", help="path to codex-assets.json")
    parser.add_argument("--skill", action="append", dest="skills", help="limit to one skill name")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--yes", action="store_true", help="confirm a write operation")
    args = parser.parse_args()

    config = load_config(args.config)
    available = skills_to_sync(config)
    selected = args.skills or available
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise SystemExit(f"不在同步清单中的 Skill：{', '.join(unknown)}")

    result = status(config)
    if args.action == "status":
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_status(result)
        return 0

    if not args.yes:
        if args.as_json:
            print(json.dumps({"action": args.action, "dry_run": True, "status": result}, ensure_ascii=False, indent=2))
        else:
            print_status(result)
            print(f"未执行 {args.action}：需要确认后加 --yes。")
        return 0

    if args.action == "backup":
        result = backup(config, selected)
    else:
        result = restore(config, selected)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"同步失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
