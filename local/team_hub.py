#!/usr/bin/env python3
"""Team work-log hub — CLI for the 5-profile fleet (pm/dev/infra/qa/ops).

Subcommands:
  log      - record a work-log entry for today (or a given date).
  view     - print all entries for a date (default: today).
  timeline - grouped timeline view across roles for a date.
  report   - daily EOD summary report (markdown) across all roles.
  reset    - (dev tool) clear entries for a date.

Data: JSONL at <team_hub_pkg>/data/activities.jsonl
Roles: pm, dev, infra, qa, ops  (matches fleet.json + discord mention-map)
"""
from __future__ import annotations

import sys
from pathlib import Path

_PKG = Path(__file__).resolve().parent / "team_hub"
sys.path.insert(0, str(_PKG))
from model import (  # noqa: E402
    ROLES,
    ROLE_BADGE,
    ACTIONS,
    append_activity,
    load_activities,
    latest_date,
)

from datetime import datetime  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

KST = ZoneInfo("Asia/Seoul")


# ---------------------------------------------------------------------------
# Argument parser (shared by view + log to fix index-based flag bugs)
# ---------------------------------------------------------------------------

def _parse_flags(args: list[str], spec: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    """Single-pass flag parser. spec maps flag-> 'str'|'bool'.
    Returns (positionals, {flag: value})."""
    pos: list[str] = []
    flags: dict[str, str] = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--") and a in spec:
            kind = spec[a]
            if kind == "bool":
                flags[a] = "1"
                i += 1
            else:
                if i + 1 >= len(args):
                    print(f"error: {a} expects a value", file=sys.stderr)
                    i += 1
                    continue
                flags[a] = args[i + 1]
                i += 2
        elif a.startswith("@") or not a.startswith("-"):
            pos.append(a)
            i += 1
        else:
            # unknown flag — treat as positional to avoid silent drops
            pos.append(a)
            i += 1
    return pos, flags


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _fmt_entry(row: dict, show_ts: bool = False) -> str:
    badge = ROLE_BADGE.get(row.get("role", "?"), "[?]")
    action = row.get("action", "log")
    a = f"[{action.upper()}]" if action not in ("log", "") else ""
    card = row.get("card_id") or ""
    c = f" {card}" if card else ""
    ts = f" ({row.get('ts', '')[:19]})" if show_ts else ""
    summary = row.get("summary", "")
    line = f"{badge} {a}{c} {summary}{ts}".strip()
    if row.get("detail"):
        line += f"\n      ↳ {row['detail']}"
    return line


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_log(args: list[str]) -> int:
    """log <role> <summary> [--date YYYY-MM-DD] [--card t_xxx] [--action X] [--detail Y] [--tag t1,t2]"""
    pos, flags = _parse_flags(args, {
        "--date": "str", "--card": "str", "--action": "str",
        "--detail": "str", "--tag": "str",
    })
    if len(pos) < 2:
        print("usage: team_hub.py log <role> <summary> [--date D] [--card ID] [--action A] [--detail T] [--tag t1,t2]")
        return 2
    role = pos[0]
    if role not in ROLES:
        print(f"invalid role '{role}'. choices: {', '.join(ROLES)}")
        return 2
    summary = pos[1]
    if len(summary) > 80:
        print("warn: summary trimmed to 80 chars", file=sys.stderr)
        summary = summary[:80]
    date = flags.get("--date")
    card_id = flags.get("--card")
    action = flags.get("--action", "log")
    detail = flags.get("--detail", "")
    tags = [t for t in flags.get("--tag", "").split(",") if t]
    row = {
        "role": role, "summary": summary, "action": action,
        "detail": detail, "tags": tags, "card_id": card_id,
    }
    if date:
        row["date"] = date
        row["time"] = "00:00"
    append_activity(row)
    badge = ROLE_BADGE[role]
    d = date or latest_date()
    print(f"OK {badge} {summary}  ({d})")
    if card_id:
        print(f"  card: {card_id}")
    return 0


def cmd_view(args: list[str]) -> int:
    """view [YYYY-MM-DD] [--role X] [--card t_xxx] [--ts]"""
    pos, flags = _parse_flags(args, {"--role": "str", "--card": "str", "--ts": "bool"})
    date = pos[0] if pos else None
    role = flags.get("--role")
    card_id = flags.get("--card")
    show_ts = bool(flags.get("--ts"))
    if date is None:
        date = latest_date()
    if date is None:
        print("no activities logged yet.")
        return 0
    rows = load_activities(date=date, role=role, card_id=card_id)
    if not rows:
        label = ROLE_BADGE.get(role, "") if role else "전체"
        print(f"{date} {label} — 기록 없음")
        return 0
    rows.sort(key=lambda r: (r.get("time", ""), r.get("ts", "")))
    label = ROLE_BADGE.get(role, "") if role else "전체"
    print(f"# {date} {label}")
    for r in rows:
        print(f"  {_fmt_entry(r, show_ts)}")
    print(f"\n({len(rows)} entries)")
    return 0


def cmd_timeline(args: list[str]) -> int:
    """timeline [YYYY-MM-DD] — grouped per-role timeline"""
    pos, _ = _parse_flags(args, {})
    date = pos[0] if pos else latest_date()
    if date is None:
        print("no activities logged yet.")
        return 0
    rows = load_activities(date=date)
    if not rows:
        print(f"{date} — 기록 없음")
        return 0
    rows.sort(key=lambda r: (r.get("time", ""), r.get("ts", "")))
    by_role: dict[str, list[dict]] = {r: [] for r in ROLES}
    for r in rows:
        by_role.setdefault(r.get("role", "dev"), []).append(r)
    print(f"# Team Timeline — {date}")
    print()
    for role in ROLES:
        items = by_role.get(role, [])
        badge = ROLE_BADGE[role]
        print(f"{badge} {role}")
        if not items:
            print("  (활동 없음)")
            continue
        for r in items:
            t = r.get("time", "")
            card = r.get("card_id") or ""
            c = f" {card}" if card else ""
            action = r.get("action", "log")
            a = f"[{action.upper()}]" if action not in ("log", "") else ""
            print(f"  {t} {a}{c} {r.get('summary', '')}".rstrip())
        print()
    return 0


def cmd_report(args: list[str]) -> int:
    """report [YYYY-MM-DD] — EOD markdown summary"""
    pos, _ = _parse_flags(args, {})
    date = pos[0] if pos else latest_date()
    if date is None:
        date = datetime.now(KST).strftime("%Y-%m-%d")
    rows = load_activities(date=date)
    rows.sort(key=lambda r: (r.get("time", ""), r.get("ts", "")))
    today = date
    print(f"## [팀 작업일지] {today}")
    print()
    if not rows:
        print("오늘 기록된 팀 활동이 없습니다.")
        return 0
    active = sorted(set(r.get("role", "") for r in rows))
    print(f"**활성 인원** ({len(active)}/{len(ROLES)} role): "
          + ", ".join(f"{ROLE_BADGE.get(r, '?')}{r}" for r in active))
    print()
    for role in ROLES:
        items = [r for r in rows if r.get("role") == role]
        if not items:
            continue
        badge = ROLE_BADGE[role]
        print(f"### {badge} {role}")
        for r in items:
            t = r.get("time", "")
            card = r.get("card_id") or ""
            c = f" {card}" if card else ""
            action = r.get("action", "log")
            a = f"[{action.upper()}]" if action not in ("log", "") else ""
            print(f"- {t} {a}{c} {r.get('summary', '')}".rstrip())
        print()
    blocks = [r for r in rows if r.get("action") == "block"]
    if blocks:
        print("### ⚠️ 블로커")
        for r in blocks:
            card = r.get("card_id") or ""
            print(f"- {r.get('time', '')} {card} {r.get('summary', '')}")
        print()
    completes = [r for r in rows if r.get("action") == "complete"]
    if completes:
        print("### ✅ 완료")
        for r in completes:
            card = r.get("card_id") or ""
            print(f"- {r.get('time', '')} {card} {r.get('summary', '')}")
        print()
    return 0


def cmd_reset(args: list[str]) -> int:
    """reset [YYYY-MM-DD] — (dev) clear entries for a date."""
    from model import LOG_FILE
    import json as _json
    pos, _ = _parse_flags(args, {})
    date = pos[0] if pos else datetime.now(KST).strftime("%Y-%m-%d")
    if not LOG_FILE.exists():
        print("no log file — nothing to reset")
        return 0
    kept = []
    removed = 0
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = _json.loads(line)
        except Exception:
            kept.append(line); continue
        if row.get("date") == date:
            removed += 1
        else:
            kept.append(line)
    LOG_FILE.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    print(f"cleared {removed} entries for {date}")
    return 0


def cmd_help() -> None:
    print("Team work-log hub — CLI for the 5-profile fleet.")
    print("subcommands: log, view, timeline, report, reset")
    print(f"roles: {', '.join(ROLES)}")


def main(argv: list[str]) -> int:
    if not argv:
        cmd_help(); return 0
    cmd, rest = argv[0], argv[1:]
    dispatch = {
        "log": cmd_log,
        "view": cmd_view,
        "timeline": cmd_timeline,
        "report": cmd_report,
        "reset": cmd_reset,
        "--help": lambda _: (cmd_help(), 0)[1],
        "help": lambda _: (cmd_help(), 0)[1],
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"unknown subcommand: {cmd}")
        cmd_help(); return 2
    return fn(rest)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
