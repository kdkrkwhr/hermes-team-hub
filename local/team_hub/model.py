#!/usr/bin/env python3
"""Team work-log data model — shared by team_hub.py and cron scripts.

Persists activity rows (JSONL) to data/activities.jsonl under the script dir.
No external deps. One file, ~140 lines.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Fleet profiles in canonical order. Matches _agentradio-eval/fleet.json +
# discord mention-map.json.
ROLES: list[str] = ["pm", "dev", "infra", "qa", "ops"]

# Korean role badges, rendered in dashboards / cron reports.
ROLE_BADGE: dict[str, str] = {
    "pm": "[기획]",
    "dev": "[개발]",
    "infra": "[인프라]",
    "qa": "[검수]",
    "ops": "[운영]",
}

# Recognized action types for timeline coloring.
ACTIONS: list[str] = [
    "log", "heartbeat", "block", "comment", "complete",
    "claim", "review",
]

KST = ZoneInfo("Asia/Seoul")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "activities.jsonl"

# Env-file candidates (resolved by load_env, not used internally but exported
# for sibling cron scripts that need secrets).
ENV_CANDIDATES: list[Path] = [
    Path(r"D:\develop\e2e\.env.local"),
    Path(r"D:\develop\e2e\hermes\.env"),
    Path.home() / ".env.local",
]


def load_env() -> dict[str, str]:
    """Flatten .env.local-style files into a dict (process env wins)."""
    env: dict[str, str] = {}
    for p in ENV_CANDIDATES:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    import os
    for k in ("JIRA_EMAIL", "JIRA_TOKEN", "JIRA_API_TOKEN",
              "JIRA_BASE_URL", "JIRA_URL", "NOTION_TOKEN"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_activity(row: dict) -> None:
    """Validate + persist one activity row."""
    _ensure_dirs()
    row = dict(row)
    role = row.get("role") or "dev"
    if role not in ROLE_BADGE:
        raise ValueError(f"unknown role: {role!r}; choices: {ROLES}")
    row["role"] = role
    row.setdefault("action", "log")
    row.setdefault("summary", "")
    row.setdefault("detail", "")
    row.setdefault("tags", [])
    row.setdefault("ts", _utcnow_iso())
    if "date" not in row or not row["date"]:
        row["date"] = datetime.now(KST).strftime("%Y-%m-%d")
    if "time" not in row or not row["time"]:
        row["time"] = datetime.now(KST).strftime("%H:%M")
    row.setdefault("card_id", None)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_activities(
    date: str | None = None,
    role: str | None = None,
    card_id: str | None = None,
    tag: str | None = None,
) -> list[dict]:
    """Read activities, optionally filtered by date / role / card_id / tag."""
    if not LOG_FILE.exists():
        return []
    out: list[dict] = []
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if date and row.get("date") != date:
            continue
        if role and row.get("role") != role:
            continue
        if card_id and row.get("card_id") != card_id:
            continue
        if tag and tag not in (row.get("tags") or []):
            continue
        out.append(row)
    return out


def latest_date() -> str | None:
    """Most recent activity date (YYYY-MM-DD) in the log, or None."""
    if not LOG_FILE.exists():
        return None
    lines = [l for l in LOG_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        return None
    try:
        row = json.loads(lines[-1])
        return row.get("date")
    except (json.JSONDecodeError, IndexError):
        return None


def count_by_role(date: str | None = None) -> dict[str, int]:
    """Entry count per role for a date (includes roles with zero)."""
    rows = load_activities(date=date)
    counts = {r: 0 for r in ROLES}
    for r in rows:
        counts[r.get("role", "dev")] = counts.get(r.get("role", "dev"), 0) + 1
    return counts
