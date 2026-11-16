#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml


SCRIPT_PATH = Path(__file__).resolve()
SYSTEM_DIR = SCRIPT_PATH.parent.parent
DEFAULT_VAULT = SYSTEM_DIR.parent

DEFAULT_CONFIG: dict[str, Any] = {
    "vault": str(DEFAULT_VAULT),
    "inbox": "00-Inbox",
    "ai_root": "70-AI知识资产",
    "skill_library": "80-Skill库",
    "system_root": "90-知识系统",
    "routing": {
        "前端": "10-前端",
        "后端": "20-后端",
        "AI与Agent": "30-AI与Agent",
        "读书": "40-读书笔记",
        "每日自律": "50-每日自律",
        "股市": "60-股市",
    },
    "inbox_stale_days": 14,
    "ai_card_max_lines": 100,
    "review_stale_days": 180,
    "duplicate_title_scope": [
        "00-Inbox",
        "70-AI知识资产",
        "80-Skill库",
    ],
    "exclude_from_analysis": [
        ".git",
        ".obsidian",
        ".trash",
        "node_modules",
        "90-知识系统/模板",
        "90-知识系统/安装",
        "80-Skill库",
    ],
    "daily": {
        "dir": "50-每日自律/日报",
        "work_template": "90-知识系统/模板/每日成长-任务时长模板.md",
        "rest_template": "90-知识系统/模板/休息日-任务时长模板.md",
        "weekend_is_rest": True,
        "rest_days": [],
        "work_days": [],
    },
}

WIKILINK_RE = re.compile(r"!?\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
FENCED_CODE_START_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)")
FRONTMATTER_RE = re.compile(r"^\ufeff?---\r?\n(.*?)\r?\n---\r?\n?", re.S)
STRONG_SIGNALS = (
    "根因",
    "踩坑",
    "决定",
    "方案定为",
    "以后都",
    "下次",
    "验证通过",
    "修复了",
    "教训",
    "规范",
    "root cause",
    "gotcha",
    "decision",
    "workflow",
    "lesson",
)


def setup_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def rel(path: Path, vault: Path) -> str:
    try:
        return path.relative_to(vault).as_posix()
    except ValueError:
        return path.as_posix()


def load_config(vault: Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    config_path = vault / "90-知识系统" / "config.json"
    if config_path.is_file():
        data = json.loads(read_text(config_path))
        if isinstance(data, dict):
            config.update(data)
    config["vault"] = str(vault)
    return config


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str, int]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text, 1
    raw = match.group(1)
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    body = text[match.end():]
    start_line = text[:match.end()].count("\n") + 1
    return data, body, start_line


def note_title(path: Path, meta: dict[str, Any], body: str) -> str:
    title = meta.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem


def iter_markdown(vault: Path, config: dict[str, Any], include_excluded: bool = False) -> list[Path]:
    excluded = [] if include_excluded else config.get("exclude_from_analysis", [])
    paths = []
    for path in vault.rglob("*.md"):
        relative = rel(path, vault)
        if not include_excluded and any(relative == item or relative.startswith(item.rstrip("/") + "/") for item in excluded):
            continue
        if any(part.startswith(".") for part in path.relative_to(vault).parts):
            continue
        paths.append(path)
    return sorted(paths)


def build_indexes(vault: Path) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    stem_index: dict[str, list[Path]] = {}
    name_index: dict[str, list[Path]] = {}
    for path in vault.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(vault).parts
        if any(part in {".git", ".obsidian", ".trash", "node_modules"} for part in relative_parts):
            continue
        stem_index.setdefault(path.stem.lower(), []).append(path)
        name_index.setdefault(path.name.lower(), []).append(path)
    return stem_index, name_index


def resolve_link(target: str, vault: Path, stem_index: dict[str, list[Path]], name_index: dict[str, list[Path]]) -> bool:
    target = target.strip().replace("\\", "/")
    if not target or target.startswith(("http://", "https://", "mailto:", "tel:")):
        return True
    target = target.lstrip("/")
    direct = vault / target
    candidates = [direct]
    if direct.suffix == "":
        candidates.extend([
            direct.with_suffix(".md"),
            direct.with_suffix(".canvas"),
            direct.with_suffix(".png"),
            direct.with_suffix(".jpg"),
            direct.with_suffix(".jpeg"),
            direct.with_suffix(".webp"),
            direct.with_suffix(".pdf"),
        ])
    if any(path.exists() for path in candidates):
        return True
    name = Path(target).name.lower()
    if name in name_index:
        return True
    stem = Path(target).stem.lower()
    return stem in stem_index


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(value.strip()[:19], fmt).date()
            except ValueError:
                continue
    return None


def slugify(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|#^\[\]\x00-\x1f]', "", value)
    value = re.sub(r"\s+", " ", value).strip().strip(".")
    return value[:60] or "未命名"


def next_available(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法为 {path} 找到可用文件名")


def make_finding(level: str, path: Path, vault: Path, message: str) -> dict[str, str]:
    return {
        "level": level,
        "path": rel(path, vault),
        "message": message,
    }


def iter_inbox_entries(vault: Path, config: dict[str, Any]):
    inbox = vault / config["inbox"]
    if not inbox.is_dir():
        return
    skip = {"审核", "已归档", "附件"}
    for entry in sorted(inbox.iterdir()):
        if entry.name.startswith(".") or (entry.is_dir() and entry.name in skip):
            continue
        if entry.is_dir():
            meta_path = entry / "_meta.md"
            meta = parse_frontmatter(read_text(meta_path))[0] if meta_path.is_file() else {}
            yield entry, meta, "", "folder"
        elif entry.suffix.lower() == ".md":
            meta, body, _ = parse_frontmatter(read_text(entry))
            if meta.get("type") not in (None, "", "inbox"):
                continue
            yield entry, meta, body, "note"


def similarity_score(title: str, relative: str, meta: dict[str, Any], body: str, terms: list[str]) -> int:
    title_lower = title.lower()
    path_lower = relative.lower()
    tags = " ".join(str(item) for item in (meta.get("tags") or [])).lower()
    headings = "\n".join(line.lower() for line in body.splitlines() if line.startswith("#"))
    body_lower = body.lower()
    score = 0
    for term in terms:
        if term == title_lower:
            score += 30
        elif term in title_lower:
            score += 12
        if term in path_lower:
            score += 6
        if term in tags:
            score += 10
        if term in headings:
            score += 6
        score += min(body_lower.count(term), 8)
    return score


def find_similar(
    vault: Path,
    config: dict[str, Any],
    title: str,
    body: str,
    exclude: Path,
    limit: int = 3,
) -> list[dict[str, Any]]:
    terms = search_terms(title)
    inbox_prefix = config["inbox"].rstrip("/") + "/"
    matches: list[dict[str, Any]] = []
    for path in iter_markdown(vault, config):
        relative = rel(path, vault)
        if path == exclude or relative.startswith(inbox_prefix):
            continue
        text = read_text(path)
        meta, candidate_body, _ = parse_frontmatter(text)
        candidate_title = note_title(path, meta, candidate_body)
        score = similarity_score(candidate_title, relative, meta, candidate_body, terms)
        if score < 8:
            continue
        matches.append({
            "path": relative,
            "title": candidate_title,
            "score": score,
        })
    matches.sort(key=lambda item: (-item["score"], item["path"]))
    return matches[:limit]


def lint_vault(vault: Path, config: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    notes = iter_markdown(vault, config)
    stem_index, name_index = build_indexes(vault)
    titles: dict[str, list[Path]] = {}
    today = date.today()

    for path in notes:
        text = read_text(path)
        meta, body, _ = parse_frontmatter(text)
        title = note_title(path, meta, body)
        relative = rel(path, vault)
        if any(relative == prefix or relative.startswith(prefix.rstrip("/") + "/") for prefix in config.get("duplicate_title_scope", [])):
            titles.setdefault(title.casefold(), []).append(path)

        for match in WIKILINK_RE.finditer(strip_markdown_code(body)):
            target = match.group(1).strip()
            if not resolve_link(target, vault, stem_index, name_index):
                findings.append(make_finding("ERROR", path, vault, f"断链：[[{target}]]"))

        note_type = meta.get("type")
        if note_type == "ai-card":
            for key in ("status", "scope", "audience", "reviewed", "sources"):
                if key not in meta:
                    findings.append(make_finding("ERROR", path, vault, f"AI 卡缺少字段：{key}"))
            sources = meta.get("sources") or []
            if not isinstance(sources, list) or not sources:
                findings.append(make_finding("ERROR", path, vault, "AI 卡没有 sources"))
            else:
                for source in sources:
                    source_text = str(source)
                    link = WIKILINK_RE.search(source_text)
                    target = link.group(1) if link else source_text
                    if not resolve_link(target, vault, stem_index, name_index):
                        findings.append(make_finding("ERROR", path, vault, f"AI 卡来源不存在：{source_text}"))
            if len(text.splitlines()) > int(config.get("ai_card_max_lines", 100)):
                findings.append(make_finding("WARN", path, vault, "AI 卡超过 100 行"))
            reviewed = parse_date(meta.get("reviewed"))
            if reviewed and (today - reviewed).days > int(config.get("review_stale_days", 180)):
                findings.append(make_finding("WARN", path, vault, f"AI 卡已 {((today - reviewed).days)} 天未复核"))

        if note_type == "ai-workflow":
            for key in ("status", "scope", "audience", "version", "reviewed"):
                if key not in meta:
                    findings.append(make_finding("ERROR", path, vault, f"工作流规范缺少字段：{key}"))

        if path.is_relative_to(vault / config["inbox"]):
            if meta.get("status") == "new":
                captured = parse_date(meta.get("captured")) or parse_date(meta.get("date"))
                if captured and (today - captured).days > int(config.get("inbox_stale_days", 14)):
                    findings.append(make_finding("WARN", path, vault, f"Inbox 已积压 {(today - captured).days} 天"))

    for title, paths in titles.items():
        if title and len(paths) > 1:
            for path in paths:
                others = ", ".join(rel(item, vault) for item in paths if item != path)
                findings.append(make_finding("WARN", path, vault, f"标题重复：{title}（另有 {others}）"))

    return findings


def strip_markdown_code(text: str) -> str:
    lines: list[str] = []
    fence_char = ""
    fence_length = 0
    for line in text.splitlines():
        fence = FENCED_CODE_START_RE.match(line)
        if fence:
            marker = fence.group(1)
            if not fence_char:
                fence_char = marker[0]
                fence_length = len(marker)
                lines.append("")
                continue
            if marker[0] == fence_char and len(marker) >= fence_length and not line.strip()[len(marker):].strip():
                fence_char = ""
                fence_length = 0
                lines.append("")
                continue
        if fence_char:
            lines.append("")
        else:
            lines.append(INLINE_CODE_RE.sub("", line))
    return "\n".join(lines)


def cmd_config(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    checks: list[dict[str, str]] = []

    def check(level: str, name: str, message: str) -> None:
        checks.append({"level": level, "name": name, "message": message})

    check("OK", "vault", str(vault))
    for key in ("inbox", "ai_root", "skill_library", "system_root"):
        target = vault / config[key]
        check("OK" if target.is_dir() else "ERROR", key, str(target))

    required_templates = [
        "收集.md",
        "人读笔记.md",
        "AI操作卡.md",
        "审核报告.md",
        "Skill评估.md",
        "工作流规范.md",
    ]
    for name in required_templates:
        target = vault / "90-知识系统" / "模板" / name
        check("OK" if target.is_file() else "ERROR", f"模板/{name}", str(target))

    for name in ("kb-curator", "kb-query", "codex-asset-sync"):
        target = vault / "80-Skill库" / "Codex备份" / "skills" / name / "SKILL.md"
        check("OK" if target.is_file() else "ERROR", f"skill/{name}", str(target))

    for name in ("install-codex-kb.ps1", "kb-capture-ask.py"):
        target = vault / "90-知识系统" / "安装" / name
        check("OK" if target.is_file() else "ERROR", f"安装/{name}", str(target))
    prompt_target = vault / "90-知识系统" / "prompts" / "AGENTS.global.md"
    check("OK" if prompt_target.is_file() else "ERROR", "prompts/AGENTS.global.md", str(prompt_target))

    findings = lint_vault(vault, config)
    errors = [item for item in findings if item["level"] == "ERROR"]
    warnings = [item for item in findings if item["level"] == "WARN"]
    check("OK" if not errors else "WARN", "lint", f"{len(errors)} 个错误，{len(warnings)} 个警告")

    notes = iter_markdown(vault, config, include_excluded=True)
    check("OK", "notes", f"{len(notes)} 篇 Markdown")

    if args.json:
        print(json.dumps({"checks": checks, "findings": findings}, ensure_ascii=False, indent=2))
    else:
        for item in checks:
            print(f"[{item['level']}] {item['name']}: {item['message']}")
        for item in findings[:80]:
            print(f"[{item['level']}] {item['path']}: {item['message']}")
        if len(findings) > 80:
            print(f"... 还有 {len(findings) - 80} 条")

    system_errors = [item for item in checks if item["level"] == "ERROR"]
    if args.strict:
        return 1 if system_errors or errors else 0
    return 1 if system_errors else 0


def cmd_inbox(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    inbox = vault / config["inbox"]
    items: list[dict[str, Any]] = []
    if not inbox.is_dir():
        print(f"Inbox 不存在：{inbox}", file=sys.stderr)
        return 1

    for entry, meta, body, entry_type in iter_inbox_entries(vault, config):
        items.append({
            "title": note_title(entry, meta, body) if entry_type == "note" else entry.name,
            "path": rel(entry, vault),
            "status": meta.get("status", "new"),
            "kind": meta.get("kind", "folder" if entry_type == "folder" else ""),
            "captured": meta.get("captured", ""),
            "type": entry_type,
        })

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0

    if not items:
        print("Inbox 是空的。")
        return 0
    for item in items:
        print(f"[{item['status']}] {item['title']}  ({item['kind']})  {item['path']}")
    print(f"\n共 {len(items)} 条")
    return 0


def build_review_report(entries: list[dict[str, Any]], generated_at: datetime) -> str:
    lines = [
        "---",
        "type: review-report",
        "status: proposed",
        f"created: {generated_at.strftime('%Y-%m-%dT%H:%M')}",
        "mode: propose",
        f"items: {len(entries)}",
        "---",
        "",
        f"# 临时区审核报告 {generated_at.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 概览",
        "",
        "| # | 条目 | 判断 | 建议目标 | 动作 |",
        "|---|---|---|---|---|",
    ]
    for index, item in enumerate(entries, start=1):
        target = item["candidates"][0]["path"] if item["candidates"] else "待判断"
        lines.append(f"| {index} | {item['title']} | 待判断 | {target} | 待判断 |")

    lines.extend(["", "## 逐条建议", ""])
    for index, item in enumerate(entries, start=1):
        lines.append(f"### {index}. {item['title']}")
        lines.append("")
        lines.append(f"- 当前路径：`{item['path']}`")
        lines.append(f"- 收集原因：{item['reason'] or '未标注'}；类型：{item['kind'] or '未标注'}")
        if item["candidates"]:
            lines.append("- 重复候选：")
            for candidate in item["candidates"]:
                lines.append(f"  - `{candidate['path']}`（{candidate['title']}，分数 {candidate['score']}）")
        else:
            lines.append("- 重复候选：无（未命中同主题笔记，仍需人工确认）")
        lines.append("- 价值判断：L1 / L2 / L3 / L4（由 Codex 判断后填写）")
        lines.append("- 建议目标：待判断，可参考重复候选所在目录")
        lines.append("- 建议动作：合并 / 新建 / 只记录 / 淘汰")
        lines.append("- 将创建或修改：待填写")
        lines.append("- 影响范围：待填写（涉及文件数、是否移动目录、是否改双链）")
        lines.append("- 风险与不确定：待填写")
        lines.append("")

    lines.extend([
        "## 待确认",
        "",
    ])
    for index, item in enumerate(entries, start=1):
        lines.append(f"- [ ] 第 {index} 条：{item['title']}")
    lines.extend([
        "",
        "## 批准方式",
        "",
        "回复“执行 1、3”或“全部执行”；未列出的条目保持不动。",
        "",
    ])
    return "\n".join(lines)


def cmd_review(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    now = datetime.now()
    entries: list[dict[str, Any]] = []
    for entry, meta, body, entry_type in iter_inbox_entries(vault, config):
        if entry_type != "note":
            continue
        if meta.get("status") in {"archived", "done", "published"}:
            continue
        title = note_title(entry, meta, body)
        entries.append({
            "path": rel(entry, vault),
            "title": title,
            "kind": meta.get("kind", ""),
            "reason": meta.get("capture_reason", ""),
            "candidates": find_similar(vault, config, title, body, entry, limit=3),
        })
        if args.limit and len(entries) >= args.limit:
            break

    if args.json:
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return 0
    if not entries:
        print("Inbox 是空的，无需审核。")
        return 0
    report = build_review_report(entries, now)
    if args.dry_run:
        print(report)
        return 0

    review_dir = vault / config["inbox"] / "审核"
    target = next_available(review_dir / f"{now.strftime('%Y-%m-%d-%H%M')}-审核报告.md")
    write_text(target, report)
    append_log(vault, "review", str(len(entries)), rel(target, vault))
    print(rel(target, vault))
    return 0


INDEX_BEGIN = "<!-- BEGIN kb-index -->"
INDEX_END = "<!-- END kb-index -->"


def scan_groups(vault: Path, config: dict[str, Any]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    system_root = config["system_root"]
    skip = {".git", ".obsidian", ".trash", "node_modules"}
    for path in vault.rglob("*.md"):
        parts = path.relative_to(vault).parts
        if any(part in skip or part.startswith(".") for part in parts):
            continue
        if len(parts) < 2:
            continue
        top = parts[0]
        if top == system_root:
            continue
        groups.setdefault(top, []).append(path)
    for paths in groups.values():
        paths.sort()
    return groups


def group_sort_key(name: str) -> tuple[int, str]:
    prefix = name.split("-")[0]
    number = int(prefix) if prefix.isdigit() else 999
    return (number, name)


def link_to(path: Path, vault: Path) -> str:
    meta, body, _ = parse_frontmatter(read_text(path))
    target = rel(path, vault)[:-3]
    return f"[[{target}|{note_title(path, meta, body)}]]"


def build_index_block(vault: Path, config: dict[str, Any]) -> str:
    groups = scan_groups(vault, config)
    today = date.today().isoformat()
    lines = [
        INDEX_BEGIN,
        "",
        f"> 由 `kb.py index` 于 {today} 生成。手写内容放在标记之外，重跑只替换标记内区块。",
        "",
    ]
    for name in sorted(groups, key=group_sort_key):
        paths = groups[name]
        lines.append(f"### {name}（{len(paths)} 篇）")
        lines.append("")
        navs = [path for path in paths if path.name.startswith("00-")]
        for path in navs:
            lines.append(f"- {link_to(path, vault)}")
        if name.startswith(config["inbox"]):
            lines.append("")
            continue
        rest = [path for path in paths if path not in navs]
        if len(paths) > 30:
            by_dir: dict[str, int] = {}
            for path in rest:
                parent = path.parent.relative_to(vault / name).as_posix()
                key = parent if parent != "." else "根目录"
                by_dir[key] = by_dir.get(key, 0) + 1
            for key in sorted(by_dir):
                lines.append(f"- {key}：{by_dir[key]} 篇")
            lines.append("")
            continue
        buckets: dict[str, list[Path]] = {}
        for path in rest:
            parent = path.parent.relative_to(vault / name).as_posix()
            key = "" if parent == "." else parent
            buckets.setdefault(key, []).append(path)
        for key in sorted(buckets):
            if key:
                lines.append(f"- {key}")
                prefix = "  - "
            else:
                prefix = "- "
            for path in buckets[key]:
                lines.append(f"{prefix}{link_to(path, vault)}")
        lines.append("")

    lines.extend([
        f"### {config['system_root']}（系统）",
        "",
        f"- [[{config['system_root']}/设计|系统设计]]",
        f"- [[{config['system_root']}/使用说明|使用说明]]",
        f"- [[{config['system_root']}/处理日志|处理日志]]",
        "",
        INDEX_END,
    ])
    return "\n".join(lines)


def cmd_index(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    block = build_index_block(vault, config)
    target = vault / "00-知识库首页.md"
    header = (
        "---\n"
        "type: dashboard\n"
        "title: 知识库首页\n"
        f"updated: {date.today().isoformat()}\n"
        "---\n\n"
        "# 知识库首页\n\n"
        f"收集箱：[[{config['inbox']}/00-收集箱|待处理]] ｜ "
        f"AI 资产：[[{config['ai_root']}/00-入口|入口]] ｜ "
        f"Skill：[[{config['skill_library']}/00-索引|索引]]\n\n"
    )
    if target.is_file():
        text = read_text(target)
        pattern = re.compile(
            re.escape(INDEX_BEGIN) + r".*?" + re.escape(INDEX_END),
            re.S,
        )
        if pattern.search(text):
            updated = pattern.sub(block, text)
        else:
            updated = text.rstrip() + "\n\n" + block + "\n"
    else:
        updated = header + block + "\n"
    if args.dry_run:
        print(updated)
        return 0
    write_text(target, updated)
    print(rel(target, vault))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    now = datetime.now()
    findings = lint_vault(vault, config)
    groups = scan_groups(vault, config)
    notes = iter_markdown(vault, config)
    inbox_items = [item for item in iter_inbox_entries(vault, config) if item[3] == "note"]
    review_dir = vault / config["inbox"] / "审核"
    reviews = sorted(review_dir.glob("*.md")) if review_dir.is_dir() else []
    ai_cards = 0
    workflows = 0
    for path in notes:
        meta = parse_frontmatter(read_text(path))[0]
        if meta.get("type") == "ai-card":
            ai_cards += 1
        elif meta.get("type") == "ai-workflow":
            workflows += 1
    errors = [item for item in findings if item["level"] == "ERROR"]
    warnings = [item for item in findings if item["level"] == "WARN"]

    lines = [
        "---",
        "type: audit-report",
        f"month: {now.strftime('%Y-%m')}",
        f"created: {now.strftime('%Y-%m-%dT%H:%M')}",
        f"errors: {len(errors)}",
        f"warnings: {len(warnings)}",
        "---",
        "",
        f"# 月度审计 {now.strftime('%Y-%m')}",
        "",
        "## 概况",
        "",
        f"- 笔记总数（不含系统层与根文件）：{sum(len(paths) for paths in groups.values())}",
        f"- Inbox 待处理：{len(inbox_items)}",
        f"- 审核报告：{len(reviews)} 份；最近一次：{reviews[-1].stem if reviews else '无'}",
        f"- AI 操作卡：{ai_cards}；工作流规范：{workflows}",
        "",
        "| 领域 | 篇数 |",
        "|---|---|",
    ]
    for name in sorted(groups, key=group_sort_key):
        lines.append(f"| {name} | {len(groups[name])} |")
    lines.extend(["", "## 发现", ""])
    if not findings:
        lines.append("- 无。")
    for item in findings:
        message = item["message"].replace("[[", r"\[\[").replace("]]", r"\]\]")
        lines.append(f"- [{item['level']}] `{item['path']}`：{message}")
    lines.extend(["", "## 建议", ""])
    if not inbox_items:
        lines.append("- Inbox 为空，无需整理。")
    elif len(inbox_items) > 8:
        lines.append(f"- Inbox 有 {len(inbox_items)} 条待处理，建议本周运行一次 `kb.py review`。")
    else:
        lines.append(f"- Inbox 有 {len(inbox_items)} 条待处理，可在下次整理时一并处理。")
    if errors:
        lines.append(f"- 有 {len(errors)} 个错误，先修断链和缺字段，再发布新内容。")
    if warnings:
        lines.append(f"- 有 {len(warnings)} 个警告，多为标题重复或卡片过期，按月处理即可。")
    if not reviews:
        lines.append("- 还没有审核报告，说明临时区尚未跑过完整闭环。")
    lines.append("")
    report = "\n".join(lines)

    if args.dry_run:
        print(report)
        return 1 if errors else 0
    target = vault / config["system_root"] / "审计" / f"{now.strftime('%Y-%m')}.md"
    write_text(target, report)
    append_log(vault, "audit", str(len(notes)), rel(target, vault))
    print(rel(target, vault))
    print(f"errors={len(errors)} warnings={len(warnings)} inbox={len(inbox_items)}")
    return 1 if errors else 0


def cmd_export(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    records = []
    for path in iter_markdown(vault, config):
        if len(path.relative_to(vault).parts) < 2:
            continue
        text = read_text(path)
        meta, body, _ = parse_frontmatter(text)
        records.append({
            "id": rel(path, vault)[:-3],
            "path": rel(path, vault),
            "title": note_title(path, meta, body),
            "type": meta.get("type", ""),
            "tags": meta.get("tags") or [],
            "updated": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d"),
            "text": body.strip(),
        })
    if args.format == "jsonl":
        output = "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"
    else:
        output = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    if args.dry_run:
        print(f"records={len(records)} format={args.format}")
        return 0
    target = Path(args.out) if args.out else vault / config["system_root"] / "导出" / "qmd.jsonl"
    if not target.is_absolute():
        target = vault / target
    write_text(target, output)
    print(f"{rel(target, vault)}  records={len(records)}")
    return 0


def resolve_day_type(day: date, daily: dict[str, Any]) -> str:
    iso = day.isoformat()
    if iso in set(daily.get("work_days") or []):
        return "work"
    if iso in set(daily.get("rest_days") or []):
        return "rest"
    if daily.get("weekend_is_rest", True) and day.weekday() >= 5:
        return "rest"
    return "work"


def render_daily_template(text: str, day: date) -> str:
    text = re.sub(r"(?m)^date:.*$", f"date: '{day.isoformat()}'", text, count=1)
    return text.replace('<% tp.date.now("YYYY-MM-DD") %>', day.isoformat())


def cmd_daily(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    daily = config.get("daily") or {}
    if args.date:
        try:
            day = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("日期格式应为 YYYY-MM-DD", file=sys.stderr)
            return 1
    else:
        day = date.today()
    day_type = resolve_day_type(day, daily)
    template_path = vault / (daily.get("work_template") if day_type == "work" else daily.get("rest_template"))
    if not template_path.is_file():
        print(f"模板不存在：{template_path}", file=sys.stderr)
        return 1
    target = vault / daily.get("dir", "50-每日自律/日报") / day.strftime("%Y-%m") / f"{day.isoformat()}.md"
    if target.exists() and not args.force and read_text(target).strip():
        result = {
            "path": rel(target, vault),
            "day_type": day_type,
            "created": False,
            "reason": "already exists",
        }
        print(json.dumps(result, ensure_ascii=False) if args.json else f"已存在：{result['path']}")
        return 0
    content = render_daily_template(read_text(template_path), day)
    if args.dry_run:
        print(f"{target}\ntype={day_type}")
        return 0
    write_text(target, content)
    result = {
        "path": rel(target, vault),
        "day_type": day_type,
        "created": True,
        "template": rel(template_path, vault),
    }
    print(json.dumps(result, ensure_ascii=False) if args.json else result["path"])
    return 0


def search_terms(query: str) -> list[str]:
    normalized = query.strip().lower()
    terms = [normalized]
    terms.extend(part for part in re.split(r"\s+", normalized) if part)
    if any("\u4e00" <= char <= "\u9fff" for char in normalized) and len(normalized) >= 4:
        terms.extend(normalized[index:index + 2] for index in range(len(normalized) - 1))
    seen = set()
    result = []
    for term in terms:
        if term and term not in seen:
            seen.add(term)
            result.append(term)
    return result


def cmd_search(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    query = args.query.strip()
    if not query:
        print("查询不能为空", file=sys.stderr)
        return 1
    terms = search_terms(query)
    results: list[dict[str, Any]] = []

    for path in iter_markdown(vault, config):
        relative = rel(path, vault)
        if args.scope and not relative.startswith(args.scope.strip("/")):
            continue
        text = read_text(path)
        meta, body, start_line = parse_frontmatter(text)
        title = note_title(path, meta, body)
        title_lower = title.lower()
        path_lower = relative.lower()
        tags = " ".join(str(item) for item in (meta.get("tags") or [])).lower()
        headings = "\n".join(line.lower() for line in body.splitlines() if line.startswith("#"))
        body_lower = body.lower()
        score = 0
        first_index = -1
        for term in terms:
            if term == title_lower:
                score += 30
            elif term in title_lower:
                score += 12
            if term in path_lower:
                score += 6
            if term in tags:
                score += 10
            if term in headings:
                score += 6
            count = body_lower.count(term)
            if count:
                score += min(count, 8)
                index = body_lower.find(term)
                if first_index < 0 or index < first_index:
                    first_index = index
        if score <= 0:
            continue
        line_number = start_line
        snippet = ""
        if first_index >= 0:
            line_number = start_line + body_lower[:first_index].count("\n")
            match_line = body.splitlines()[line_number - start_line] if line_number - start_line < len(body.splitlines()) else ""
            snippet = match_line.strip()[:160]
        results.append({
            "path": relative,
            "line": line_number,
            "title": title,
            "score": score,
            "snippet": snippet,
        })

    results.sort(key=lambda item: (-item["score"], item["path"]))
    results = results[: args.limit]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if not results:
        print("没有找到相关内容。")
        return 0
    for item in results:
        print(f"{item['path']}:{item['line']}  [{item['score']}]")
        if item["snippet"]:
            print(f"  {item['snippet']}")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    findings = lint_vault(vault, config)
    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("没有发现问题。")
        for item in findings:
            print(f"[{item['level']}] {item['path']}: {item['message']}")
        errors = sum(1 for item in findings if item["level"] == "ERROR")
        warnings = sum(1 for item in findings if item["level"] == "WARN")
        print(f"\n{errors} 个错误，{warnings} 个警告")
    return 1 if any(item["level"] == "ERROR" for item in findings) else 0


def cmd_capture(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    content = args.content or ""
    if not content and not sys.stdin.isatty():
        content = sys.stdin.read()
    content = content.strip()
    if not content:
        print("内容不能为空", file=sys.stderr)
        return 1
    title = args.title.strip() if args.title else ""
    if not title:
        for line in content.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                title = stripped
                break
    title = title or "未命名收集"
    meta = {
        "type": "inbox",
        "status": "new",
        "captured": datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "source": args.source or "",
        "kind": args.kind,
        "capture_reason": args.reason,
        "value": "unknown",
        "tags": [item.strip() for item in (args.tags or "").split(",") if item.strip()],
    }
    frontmatter = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    body = f"# {title}\n\n{content}\n"
    filename = f"{date.today().isoformat()}-{slugify(title)}.md"
    target = next_available(vault / config["inbox"] / filename)
    output = f"---\n{frontmatter}\n---\n\n{body}"
    if args.dry_run:
        print(output)
        return 0
    write_text(target, output)
    if args.json:
        print(json.dumps({"path": rel(target, vault)}, ensure_ascii=False))
    else:
        print(rel(target, vault))
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    config = load_config(vault)
    inbox = (vault / config["inbox"]).resolve()
    source = Path(args.path)
    if not source.is_absolute():
        source = (vault / source).resolve()
    if not source.exists():
        print(f"路径不存在：{source}", file=sys.stderr)
        return 1
    if not source.is_relative_to(inbox):
        print(f"只能归档 Inbox 内路径：{source}", file=sys.stderr)
        return 1
    month = args.month or date.today().strftime("%Y-%m")
    destination_dir = inbox / "已归档" / month
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = next_available(destination_dir / source.name)
    shutil.move(str(source), str(destination))
    if destination.is_file() and destination.suffix.lower() == ".md":
        text = read_text(destination)
        meta, body, _ = parse_frontmatter(text)
        meta["status"] = "archived"
        meta["archived"] = date.today().isoformat()
        frontmatter = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
        write_text(destination, f"---\n{frontmatter}\n---\n\n{body}")
    if args.json:
        print(json.dumps({"path": rel(destination, vault)}, ensure_ascii=False))
    else:
        print(rel(destination, vault))
    return 0


def append_log(vault: Path, mode: str, items: str, summary: str) -> str:
    log_path = vault / "90-知识系统" / "处理日志.md"
    if not log_path.is_file():
        write_text(log_path, "# 处理日志\n\n- 每次收集、整理、发布、审计追加一行。\n\n")
    line = f"- {datetime.now().strftime('%Y-%m-%d %H:%M')} | {mode} | {items} | {summary}\n"
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
    return line.strip()


def cmd_log(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    print(append_log(vault, args.mode, args.items, args.summary))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="知识库确定性工具")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT), help="Vault 根目录")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("config")
    config_parser.set_defaults(func=cmd_config)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--json", action="store_true")
    doctor_parser.add_argument("--strict", action="store_true")
    doctor_parser.set_defaults(func=cmd_doctor)

    inbox_parser = subparsers.add_parser("inbox")
    inbox_parser.add_argument("--json", action="store_true")
    inbox_parser.set_defaults(func=cmd_inbox)

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--limit", type=int, default=0)
    review_parser.add_argument("--dry-run", action="store_true")
    review_parser.add_argument("--json", action="store_true")
    review_parser.set_defaults(func=cmd_review)

    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("--dry-run", action="store_true")
    index_parser.set_defaults(func=cmd_index)

    daily_parser = subparsers.add_parser("daily")
    daily_parser.add_argument("--date", default="")
    daily_parser.add_argument("--force", action="store_true")
    daily_parser.add_argument("--dry-run", action="store_true")
    daily_parser.add_argument("--json", action="store_true")
    daily_parser.set_defaults(func=cmd_daily)

    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--dry-run", action="store_true")
    audit_parser.set_defaults(func=cmd_audit)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--format", choices=["jsonl", "json"], default="jsonl")
    export_parser.add_argument("--out", default="")
    export_parser.add_argument("--dry-run", action="store_true")
    export_parser.set_defaults(func=cmd_export)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--scope", default="")
    search_parser.add_argument("--json", action="store_true")
    search_parser.set_defaults(func=cmd_search)

    lint_parser = subparsers.add_parser("lint")
    lint_parser.add_argument("--json", action="store_true")
    lint_parser.set_defaults(func=cmd_lint)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--title", default="")
    capture_parser.add_argument("--content", default="")
    capture_parser.add_argument("--source", default="")
    capture_parser.add_argument("--kind", default="idea")
    capture_parser.add_argument("--reason", default="manual")
    capture_parser.add_argument("--tags", default="")
    capture_parser.add_argument("--dry-run", action="store_true")
    capture_parser.add_argument("--json", action="store_true")
    capture_parser.set_defaults(func=cmd_capture)

    archive_parser = subparsers.add_parser("archive")
    archive_parser.add_argument("path")
    archive_parser.add_argument("--month", default="")
    archive_parser.add_argument("--json", action="store_true")
    archive_parser.set_defaults(func=cmd_archive)

    log_parser = subparsers.add_parser("log")
    log_parser.add_argument("--mode", required=True)
    log_parser.add_argument("--items", default="0")
    log_parser.add_argument("--summary", default="")
    log_parser.set_defaults(func=cmd_log)

    return parser


def main() -> int:
    setup_stdout()
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
