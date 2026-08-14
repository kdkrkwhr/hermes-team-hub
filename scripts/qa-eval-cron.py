#!/usr/bin/env python3
"""
qa-eval-cron.py — Hermes 팀허브 QA 일일 평가 집계 스크립트

매일 자정(cron)에 실행되어:
  1. kanban 티켓 (완료/보류/REJECT) 집계
  2. errors.log 에러 건수 집계 (HTTP 429 등 rate-limit / 예외)
  3. Coral 통신 기록 수집 (coral_read.txt 또는 coral 디렉터리)
각 에이전트(pm/dev/infra/qa/ops)별 점수화 → data/qa_eval.json 저장

저장 위치: local/data/qa_eval.json (대시보드가 /api/qa-eval 로 읽음)
실행: python scripts/qa-eval-cron.py
"""
import json
import os
import re
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "local", "data")
HERMES_LOGS = "D:/develop/e2e/hermes/logs"
HERMES_HOME = "D:/develop/e2e/hermes"
ROLES = ["pm", "dev", "infra", "qa", "ops"]
ROLE_NAMES = {"pm": "마늘쿵야", "dev": "양파쿵야", "infra": "무시쿵야", "qa": "샐러리쿵야", "ops": "버섯쿵야"}


def run_hermes(args):
    import subprocess
    try:
        out = subprocess.run(["hermes"] + args, capture_output=True, text=True, timeout=30)
        return out.stdout + out.stderr
    except Exception as e:
        return ""


def collect_kanban():
    """hermes kanban list 파싱 → role별 {done, blocked, reject}."""
    txt = run_hermes(["kanban", "list"])
    stats = {r: {"done": 0, "blocked": 0, "reject": 0} for r in ROLES}
    # 라인 예: "t_xxx  done    dev   title"
    for m in re.finditer(r"(done|blocked|running|ready)\s+(\w+)", txt):
        status, who = m.group(1), m.group(2)
        # assignee가 role명과 일치할 때만
        if who in stats:
            if status == "done":
                stats[who]["done"] += 1
            elif status == "blocked":
                stats[who]["blocked"] += 1
        # reject는 보통 title에 REJECT 표시
    for m in re.finditer(r"REJECT", txt):
        # REJECT 카드는 assignee 파악 어려움 → 일단 전체 reject+1은 안 함
        pass
    return stats


def collect_errors():
    """errors.log에서 role별 에러 건수 (대략적: 세션ID 기반 불가하므로 전체 건수만)."""
    path = os.path.join(HERMES_LOGS, "errors.log")
    if not os.path.isfile(path):
        return {r: 0 for r in ROLES}
    try:
        lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    except Exception:
        return {r: 0 for r in ROLES}
    total = sum(1 for l in lines if "WARNING" in l or "ERROR" in l)
    # 균등 배분 (정확한 role 매핑 불가)
    per = total // len(ROLES)
    return {r: per for r in ROLES}


def collect_coral():
    """Coral 통신 기록 수 (coral_read.txt 또는 coral 디렉터리)."""
    counts = {r: 0 for r in ROLES}
    cand = os.path.join(HERMES_LOGS, "coral_read.txt")
    if os.path.isfile(cand):
        try:
            txt = open(cand, encoding="utf-8", errors="ignore").read()
            for r in ROLES:
                counts[r] = len(re.findall(r"\b" + r + r"\b", txt))
        except Exception:
            pass
    return counts


def score_agent(stat, err, coral):
    done = stat["done"]
    blocked = stat["blocked"]
    # 점수: 완료 5점, block -10, 에러 -5, coral +1 (상한/하한 0~100)
    s = 70 + done * 3 - blocked * 10 - err * 5 + min(coral, 15)
    s = max(0, min(100, s))
    grade = "A" if s >= 85 else "B" if s >= 70 else "C"
    return s, grade


def main():
    today = datetime.date.today().isoformat()
    kanban = collect_kanban()
    errors = collect_errors()
    coral = collect_coral()
    evaluations = []
    for r in ROLES:
        s, grade = score_agent(kanban[r], errors[r], coral[r])
        note = "완료 %d·보류 %d·에러 %d·무전 %d" % (kanban[r]["done"], kanban[r]["blocked"], errors[r], coral[r])
        evaluations.append({
            "evaluator": "qa",
            "evaluatee": r,
            "date": today,
            "score": s,
            "grade": grade,
            "lights": {"ok": s // 25, "warn": 0, "bad": max(0, 4 - s // 25)},
            "comment": note,
            "done": kanban[r]["done"],
            "blocked": kanban[r]["blocked"],
            "reject": kanban[r]["reject"],
            "errors": errors[r],
            "coral": coral[r],
        })
    os.makedirs(DATA_DIR, exist_ok=True)
    out = {
        "date": today,
        "evaluations": evaluations,
        "scoring": {"weights": {"kanban": 0.4, "errors": 0.3, "coral": 0.3}, "light_thresholds": {"ok": 85, "warn": 70}},
        "updated": datetime.datetime.now().isoformat(timespec="seconds"),
        "generated_by": "qa-eval-cron",
    }
    path = os.path.join(DATA_DIR, "qa_eval.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("QA eval saved:", path)
    for e in evaluations:
        print("  %s %s: %d점 %s" % (e["evaluatee"], ROLE_NAMES[e["evaluatee"]], e["score"], e["grade"]))


if __name__ == "__main__":
    main()
