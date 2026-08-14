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
# env-overridable — 하드코딩된 경로는 폴백 (HARNESS-5: .env.example 의존성 추적)
_HERMES_HOME_RAW = os.environ.get("HERMES_HOME", "D:/develop/e2e/hermes")
HERMES_LOGS = os.environ.get("HERMES_LOGS", os.path.join(_HERMES_HOME_RAW, "logs"))
HERMES_HOME = _HERMES_HOME_RAW
ROLES = ["pm", "dev", "infra", "qa", "ops"]
ROLE_NAMES = {"pm": "마늘쿵야", "dev": "양파쿵야", "infra": "무시쿵야", "qa": "샐러리쿵야", "ops": "버섯쿵야"}


def run_hermes(args):
    import subprocess
    try:
        out = subprocess.run(["hermes"] + args, capture_output=True, text=True, timeout=30)
        return out.stdout + out.stderr
    except Exception:
        return ""


def collect_kanban():
    """hermes kanban list --json 파싱 → role별 {done, blocked, reject}.

    --json으로 파싱하면 assignee/status가 구조화되어 정확히 매핑된다
    (기존 텍스트 파싱은 'claude', 'default' 같은 가짜 assignee를 잡아먹� 수 있음).
    """
    txt = run_hermes(["kanban", "list", "--json"])
    stats = {r: {"done": 0, "blocked": 0, "reject": 0} for r in ROLES}
    data = []
    try:
        data = json.loads(txt)
    except Exception:
        # fallback: 텍스트 파싱 (기존 방식)
        data = []
        for m in re.finditer(r"(done|blocked|running|ready)\s+(\w+)", txt):
            s, who = m.group(1), m.group(2)
            if who in stats:
                if s == "done":
                    stats[who]["done"] += 1
                elif s == "blocked":
                    stats[who]["blocked"] += 1
    for r in data:
        who = r.get("assignee") or ""
        status = r.get("status") or ""
        title = (r.get("title") or "").lower()
        if who in stats:
            if status == "done":
                stats[who]["done"] += 1
            elif status == "blocked":
                stats[who]["blocked"] += 1
            if "reject" in title:
                stats[who]["reject"] += 1
    return stats


def collect_errors():
    """errors.log에서 role별 에러 **점수** (정규화, 비율 기반).

    기존: err = total // 5, pen_err = err * 5 → 9270점 (평가 100점 만점)
    문제: 9000건 에러면 항상 0점/C등급, 의미 없는 결과.
    개선: 에러 100건당 1점 (최대 30점 포화)으로 **정규화**.
    role별 정확 매핑은 불가하므로 전체 에러율을 공통점수로 사용.
    """
    path = os.path.join(HERMES_LOGS, "errors.log")
    if not os.path.isfile(path):
        return {r: 0.0 for r in ROLES}
    try:
        lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    except Exception:
        return {r: 0.0 for r in ROLES}
    total = sum(1 for l in lines if "WARNING" in l or "ERROR" in l)
    # 10000건당 1점, 최대 15점
    score = min(total / 10000.0, 15.0)
    return {r: round(score, 1) for r in ROLES}


def collect_coral():
    """Coral 통신 기록 수 (coral-bridge-seen.txt + coral_read.txt).

    기존: coral_read.txt만 확인 → 최근 스레드 1개만 보임.
    개선: Temp 디렉토리의 coral-bridge-seen.txt도 함께 스캔 (role별 발언 수).
    """
    counts = {r: 0 for r in ROLES}
    temp = os.environ.get("TEMP", "/c/Users/KDK/AppData/Local/Temp")
    candidates = [
        os.path.join(temp, "coral-bridge-seen.txt"),
        os.path.join(temp, "coral_read.txt"),
        os.path.join(HERMES_LOGS, "coral_read.txt"),
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            try:
                txt = open(cand, encoding="utf-8", errors="ignore").read()
                for r in ROLES:
                    counts[r] += len(re.findall(r"\b" + r + r"\b", txt))
            except Exception:
                pass
    return counts


def score_agent(stat, err, coral):
    done = stat["done"]
    blocked = stat["blocked"]
    base = 70
    add_done = done * 2      # 3 → 2 (done 49개만 해도 98점, 100점 포화 방지)
    add_coral = min(coral, 15)
    pen_block = blocked * 5   # 10 → 5 (블락도 지나치게 감점)
    pen_err = round(err, 1)   # err: 100건당 0.5점, max 15
    s = base + add_done - pen_block + add_coral - pen_err
    s = max(0, min(100, s))
    grade = "A" if s >= 85 else "B" if s >= 70 else "C"
    breakdown = {
        "base": base,
        "done": add_done,
        "coral": add_coral,
        "block": -pen_block,
        "error": -pen_err,
    }
    return s, grade, breakdown


def build_note(r, stat, err, coral, bd, s):
    """감점 사유 명시형 코멘트 (학습용). 기본/가산 - 감점 = 점수 + 보완제안.

    에러는 정규화된 점수(float)이므로 '에러N(-N점)' 형식으로 표기.
    """
    parts = ["기본%d" % bd["base"]]
    if bd["done"]:
        parts.append("+완료%d" % bd["done"])
    if bd["coral"]:
        parts.append("+무전%d" % bd["coral"])
    pen = []
    if stat["blocked"]:
        pen.append("블락%d(-%d)" % (stat["blocked"], -bd["block"]))
    if err:
        pen.append("에러%.1f(-%.1f)" % (err, -bd["error"]))
    note = " ".join(parts)
    if pen:
        note += " -" + " ".join(pen)
    note += " = %.0f" % s
    fix = []
    if stat["blocked"]:
        fix.append("장기카드 분할")
    if err:
        fix.append("예외 핸들링 강화")
    if fix:
        note += ". 보완: " + "·".join(fix)
    return note

def main():
    today = datetime.date.today().isoformat()
    kanban = collect_kanban()
    errors = collect_errors()
    coral = collect_coral()
    evaluations = []
    for r in ROLES:
        s, grade, bd = score_agent(kanban[r], errors[r], coral[r])
        note = build_note(r, kanban[r], errors[r], coral[r], bd, s)
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
