#!/usr/bin/env python3
"""
hermes-team-hub — 로컬 실행형 백엔드
표준 라이브러리만 사용 (Flask 불필요). 대장님 PC에서 실시간 agent 상태를 본다.

실행:
    python local/app.py
    -> http://localhost:5000

API:
    /                  -> 정적 index.html (local/index.html)
    /api/kanban        -> hermes kanban list 파싱 JSON
    /api/agents        -> profiles/{pm,dev,infra,qa,ops}/SOUL.md 요약
    /api/coral         -> Coral 서버(:5555) 최근 무전 (세션 살아있을 때)
    /api/logs          -> hermes logs 대체: agent.log/errors.log 직접 읽기 (name, lines)
    /api/logs-list     -> hermes logs list 대체: 로그 디렉터리 파일 목록
    /static/<path>     -> css/style.css, js/store.js, js/soul-data.js 등
"""
import json
import os
import re
import subprocess
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES = "D:/develop/e2e/hermes/profiles"
PORT = 5000

ROLES = ["pm", "dev", "infra", "qa", "ops"]

# 정적 파일 MIME 타입
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

# SOUL.md → 메타데이터 추출 (build-soul-data.py 로직 재사용, JSON 반환용)
ROLE_NAMES = {
    "pm": "마늘쿵야",
    "dev": "양파쿵야",
    "infra": "무시쿵야",
    "qa": "샐러리쿵야",
    "ops": "버섯쿵야",
}


def _editor_block(text: str) -> str:
    """SOUL.md 에디터 설정 블록 추출 (첫 번째 `---` 이후 전부)."""
    idx = text.find("\n---")
    if idx == -1:
        idx = text.find("---\n")
        if idx == -1:
            return text.strip()
        return text[idx + 4:].strip()
    return text[idx + 4:].strip()


def _extract_name(block: str, role: str) -> str:
    m = re.search(r"당신은\s+'([^']+)'", block)
    if m:
        return m.group(1)
    for line in block.splitlines():
        m = re.match(r"^#\\s+(.+?)[\\s(]", line)
        if m:
            return m.group(1).strip()
    return ROLE_NAMES.get(role, role.capitalize())


def _extract_identity(block: str) -> str:
    for line in block.splitlines():
        if "당신은" in line and ("쿵야" in line or "입니다" in line):
            return line.strip().lstrip("- ").strip()
    return ""


def _extract_tone(block: str) -> str:
    lines = block.splitlines()
    capture = False
    for line in lines:
        if re.match(r"^#{1,2}\\s*말투", line):
            capture = True
            continue
        if capture:
            ln = line.strip()
            if ln and not ln.startswith("#"):
                return ln
            if ln.startswith("#"):
                return ""
    return ""


_KANBAN_CACHE = {"rows": [], "ts": 0.0, "ttl": 5.0}


def run_hermes(args):
    try:
        out = subprocess.run(
            ["hermes"] + args, capture_output=True, text=True, timeout=30
        )
        return out.stdout + out.stderr
    except Exception as e:  # pragma: no cover
        return "ERROR: " + str(e)


def _ts_to_str(ts):
    """unix timestamp -> 'YYYY-MM-DD HH:MM' 포맷."""
    try:
        return datetime.fromtimestamp(int(float(ts))).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def _fetch_kanban():
    """hermes CLI 1회 호출 (--json)로 전체 데이터 확보. kanban show 과다 호출 제거."""
    raw = run_hermes(["kanban", "list", "--sort", "created-desc", "--json"])
    try:
        data = json.loads(raw)
    except Exception:
        return []
    rows = []
    for r in data:
        rows.append({
            "id": r.get("id", ""),
            "title": (r.get("title") or "").strip(),
            "assignee": r.get("assignee") or "",
            "status": r.get("status") or "",
            "created": _ts_to_str(r.get("created_at")),
        })
    return rows


def api_kanban():
    """in-memory 캐시(TTL 5s) + --json 배치 파싱.
    요구 1회당 hermes CLI 1회 호출 (기존: list 1회 + show 30회 = 31회).
    """
    now = time.monotonic()
    if now - _KANBAN_CACHE["ts"] < _KANBAN_CACHE["ttl"] and _KANBAN_CACHE["rows"]:
        return _KANBAN_CACHE["rows"]
    rows = _fetch_kanban()
    _KANBAN_CACHE["rows"] = rows
    _KANBAN_CACHE["ts"] = now
    return rows


def api_agents():
    out = []
    for role in ROLES:
        p = os.path.join(PROFILES, role, "SOUL.md")
        cfg = os.path.join(PROFILES, role, "config.yaml")
        exists = os.path.exists(p)
        entry = {"role": role, "exists": exists}
        if exists:
            with open(p, encoding="utf-8") as f:
                raw = f.read()
            block = _editor_block(raw)
            entry["name"] = _extract_name(block, role)
            entry["identity"] = _extract_identity(block)
            entry["tone"] = _extract_tone(block)
            entry["head"] = (entry["identity"] or raw[:120]).replace("\n", " ").strip()
        # config.yaml → model + provider
        if os.path.exists(cfg):
            try:
                import yaml
                with open(cfg, encoding="utf-8") as f:
                    c = yaml.safe_load(f)
                m = c.get("model", {}) or {}
                entry["provider"] = m.get("provider", "")
                entry["model"] = m.get("default", "")
                # fallback 첫 번째도 같이
                fb = c.get("fallback_providers", []) or []
                if fb and isinstance(fb, list):
                    f0 = fb[0] if isinstance(fb[0], dict) else {}
                    entry["fallback"] = (f0.get("provider", "") + "/" + f0.get("model", "")).strip("/")
            except Exception:
                entry["provider"] = ""
                entry["model"] = ""
        out.append(entry)
    return out


def _coral_read_path():
    return os.path.join(
        os.environ.get("TEMP", "C:/Users/KDK/AppData/Local/Temp"),
        "coral_read.txt",
    )


def _coral_seen_path():
    return os.path.join(
        os.environ.get("TEMP", "C:/Users/KDK/AppData/Local/Temp"),
        "coral-bridge-seen.txt",
    )


def _parse_coral_read():
    """coral_read.txt에서 스레드+메시지 스냅샷 추출.
    형식: ```json[ {...threads...} ]``` 블록.
    반환: 스레드 목록 (threadId, threadName, owningAgentName, participatingAgents, messages[])
    """
    p = _coral_read_path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return []
    m = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(1))
    except Exception:
        return []


def api_coral():
    """Coral 무전: 실제 메시지 content/author/threadName 포함.
    coral_read.txt (Coral 브리지 덤프)에서 스레드+메시지 추출,
    coral-bridge-seen.txt seen 기록도 함께 반환.
    """
    threads = _parse_coral_read()
    rows = []
    for t in threads:
        tid = t.get("threadId", "")
        tname = tid[:8]  # 암호화된 ID는 짧게
        for msg in t.get("messages", []) or []:
            rows.append({
                "thread": tname,
                "threadName": t.get("threadName", ""),
                "ts": msg.get("messageTimestamp", ""),
                "agent": msg.get("sendingAgentName", ""),
                "content": msg.get("messageText", ""),
                "mentions": msg.get("mentionAgentNames", []) or [],
            })
    # seen 기록도 보강 (브리지 레벨 무전)
    seen = _coral_seen_path()
    if os.path.exists(seen):
        try:
            with open(seen, encoding="utf-8") as f:
                for line in f.readlines()[-20:]:
                    line = line.strip()
                    if not line or "|" not in line:
                        continue
                    parts = line.split("|")
                    tid = parts[0]
                    # duplicates 방지 (full content 없는 seen 레코드)
                    if not any(r["thread"] == tid[:8] and r["ts"] == (parts[1] if len(parts) > 1 else "") for r in rows):
                        rows.append({
                            "thread": tid[:8],
                            "ts": parts[1] if len(parts) > 1 else "",
                            "agent": parts[-1] if len(parts) > 2 else "",
                            "content": "(본문 없음)",
                            "mentions": [],
                        })
        except Exception:
            pass
    # 최신순
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows[:50]


def api_state():
    """실시간 상태 스냅샷: kanban + role summary + coral recent_messages.
    t_ffe42db2 / t_483edd39 요구사항 (/api/state).
    """
    kb = api_kanban()
    by_status = {}
    role_counts = {r: 0 for r in ROLES}
    for r in kb:
        s = r.get("status", "ready")
        by_status.setdefault(s, 0)
        by_status[s] += 1
        a = r.get("assignee", "")
        if a in role_counts:
            role_counts[a] += 1
    coral = api_coral()
    return {
        "kanban": kb,
        "status_summary": {
            "total": len(kb),
            "by_status": by_status,
            "by_role": role_counts,
        },
        "coral": {
            "recent_messages": coral[:20],
            "server_up": bool(_check_port("127.0.0.1", 5555)),
        },
    }


def _log_dir():
    """hermes 프로필 로그 디렉터리 경로. HERMES_HOME env → fallback to ~/.hermes/profiles/<profile>/logs."""
    home = os.environ.get("HERMES_HOME") or os.environ.get("HERMES_PROJECT_ROOT", "")
    profile = os.environ.get("HERMES_PROFILE", "dev")
    if home:
        return os.path.join(home, "logs")
    return os.path.join(os.path.expanduser("~/.hermes/profiles"), profile, "logs")


def api_logs(log_name="agent", lines=50):
    """hermes logs 대체: agent.log / errors.log 직접 파일 읽기 (local 전용).

    - log_name: 'agent' | 'errors' | 'gateway' | 'gui' | 'desktop' (없으면 agent)
    - lines: 마지막 N줄 (기본 50, MAX 200)
    반환: { name, path, lines, total, output }
    """
    # 허용된 로그 파일명 화이트리스트 (hermes logs list 기준)
    allowed = {"agent", "errors", "gateway", "gui", "desktop"}
    if log_name not in allowed:
        log_name = "agent"
    lines = max(1, min(int(lines), 200))
    log_path = os.path.join(_log_dir(), f"{log_name}.log")
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except FileNotFoundError:
        return {
            "name": log_name,
            "path": log_path,
            "lines": lines,
            "total": 0,
            "output": "No log file found. Start hermes to generate logs.",
        }
    except Exception as e:
        return {
            "name": log_name,
            "path": log_path,
            "lines": lines,
            "total": 0,
            "output": f"ERROR reading log: {e}",
        }
    total = len(all_lines)
    tail = all_lines[-lines:] if lines else all_lines
    return {
        "name": log_name,
        "path": log_path,
        "lines": lines,
        "total": total,
        "output": "".join(tail).rstrip("\n"),
    }


def api_logs_list():
    """hermes logs list 대체: 로그 디렉터리 파일 목록 + 크기 반환."""
    d = _log_dir()
    files = []
    if os.path.isdir(d):
        for fn in os.listdir(d):
            fp = os.path.join(d, fn)
            if fn.endswith(".log") and os.path.isfile(fp):
                files.append({"name": fn, "size": os.path.getsize(fp)})
    files.sort(key=lambda x: x["name"])
    return {"dir": d, "files": files}


# ── SSE 스트림 상태 (in-memory, /api/feed) ──────────────────────
_LAST_KANBAN_HASH = 0
_LAST_FEED_TS = 0.0
_FEED_CLIENTS = []


# ── 봇 전용 메뉴용 로컬 데이터 저장 ──────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(name, default=None):
    p = os.path.join(DATA_DIR, name)
    if not os.path.exists(p):
        return default if default is not None else []
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []


def _save_json(name, obj):
    p = os.path.join(DATA_DIR, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def api_pm_tasks():
    """태스크 분해기: 상위 업무 → 하위 태스크 리스트."""
    return _load_json("pm_tasks.json", [])


def api_pm_roadmap():
    """로드맵: 월별 목표."""
    return _load_json("pm_roadmap.json", [])


def api_dev_snippets():
    """코드 스니펫 뷰어 (로컬 저장)."""
    return _load_json("dev_snippets.json", [])


def api_dev_bugs():
    """버그 추적: QA가 반려(blocked)한 칸반 카드만."""
    kb = api_kanban()
    return [r for r in kb if r.get("status") == "blocked"]


def _check_process(name_frag):
    """프로세스 존재 여부 (Windows: tasklist via WMI 불가하므로 powershell 사용)."""
    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '" + name_frag + "' }).Count"],
            capture_output=True, text=True, timeout=10
        )
        return int(out.stdout.strip() or "0") > 0
    except Exception:
        return False


def _check_port(host, port):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        return s.connect_ex((host, port)) == 0
    except Exception:
        return False
    finally:
        s.close()


def _check_http(url):
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status < 400
    except Exception:
        return False


def api_infra_status():
    """상태 대시보드: 호출 시 실제 상태를 계산 (cron 불필요, 매 refesh 신선)."""
    gateway = _check_process("hermes.*gateway") or _check_process("Hermes_Gateway")
    coral = _check_port("127.0.0.1", 5555)
    pages = _check_http("https://kdkrkwhr.github.io/hermes-team-hub/")
    hub = _check_port("127.0.0.1", 5000)
    return [
        {"name": "Hermes Gateway", "state": "ok" if gateway else "bad", "note": "정상" if gateway else "프로세스 없음"},
        {"name": "Coral 서버 (:5555)", "state": "ok" if coral else "warn", "note": "응답" if coral else "세션 만료/미기동"},
        {"name": "GitHub Pages", "state": "ok" if pages else "warn", "note": "200 OK" if pages else "접근 불가"},
        {"name": "Team Hub (localhost:5000)", "state": "ok" if hub else "bad", "note": "정상" if hub else "서버 다운"},
    ]


def api_infra_resources():
    """리소스 모니터 (로컬 메트릭 샘플)."""
    return _load_json("infra_resources.json", {"cpu": 0, "mem": 0, "note": "샘플 데이터"})


def api_qa_eval() -> dict:
    """QA 일일 평가집계 + 점수화 보드 데이터.

    우선순위:
      1. data/qa_eval.json — demo mock 또는 qa-eval-cron 실제 집계 결과
         - 두 데이터 스키마(nested criteria vs flat done/errors/coral) 모두 지원
      2. fallback: qa-checklist 항목 → 커버리지 비율 실시간 집계
    """
    eval_path = os.path.join(DATA_DIR, "qa_eval.json")
    mock = _load_json("qa_eval.json") if os.path.exists(eval_path) else None
    if mock is not None:
        eval_rows = mock.get("evaluations", [])
        scoring = mock.get("scoring", {})
        source = "mock" if not mock.get("generated_by") else "cron"
        updated = mock.get("updated")
    else:
        eval_rows = _qa_eval_from_checklist()
        scoring = {
            "weights": {"score": 0.6, "lights": 0.2, "comment": 0.2},
            "light_thresholds": {"ok": 85, "warn": 60},
        }
        source = "checklist"
        updated = None

    # 라이트(ok/warn/bad) 판정 — thresholds가 없으면 기본값
    ok_thresh = (scoring.get("light_thresholds", {}) or {}).get("ok", 85)
    warn_thresh = (scoring.get("light_thresholds", {}) or {}).get("warn", 60)

    board = []
    agents_meta = {a.get("role"): a for a in api_agents()}
    for role in ROLES:
        rows = [e for e in eval_rows if e.get("evaluatee") == role]
        latest = max(rows, key=lambda e: e.get("date", "")) if rows else None
        meta = agents_meta.get(role, {})
        if latest:
            score = latest.get("score", 0)
            # 스키마 호환: flat(cron) 또는 nested(mock)
            lights = latest.get("lights", {})
            if not lights:
                lights = _lights_from_flat(latest)
            light = _light_from_score(score, ok_thresh, warn_thresh)
            comment = latest.get("comment") or _comment_from_flat(latest)
            board.append({
                "role": role,
                "name": meta.get("name", role),
                "score": score,
                "grade": latest.get("grade", ""),
                "light": light,
                "lights": lights,
                "comment": (comment or "")[:120],
                "date": latest.get("date", ""),
                "criteria": latest.get("criteria", {}),
                "metrics": _flat_metrics(latest),
            })
        else:
            board.append({
                "role": role,
                "name": meta.get("name", role),
                "score": 0,
                "grade": "",
                "light": "bad",
                "lights": {"ok": 0, "warn": 0, "bad": 0},
                "comment": "평가 없음",
                "date": None,
                "criteria": {},
                "metrics": {},
            })

    return {
        "board": board,
        "evaluations": eval_rows,
        "scoring": scoring,
        "updated": updated,
        "source": source,
    }


def _light_from_score(score, ok_thresh, warn_thresh):
    if score >= ok_thresh:
        return "ok"
    elif score >= warn_thresh:
        return "warn"
    else:
        return "bad"


def _lights_from_flat(row):
    """cron flat 스키마(done/errors/coral) → {ok,warn,bad} 추정."""
    done = row.get("done", 0)
    errors = row.get("errors", 0)
    total = done + errors
    if not total:
        return {"ok": 0, "warn": 0, "bad": 1}
    ok = 1 if done / total > 0.9 else 0
    bad = 1 if errors / total > 0.3 else 0
    warn = 1 - ok - bad
    return {"ok": ok, "warn": warn, "bad": bad}


def _comment_from_flat(row):
    """cron flat 스키마 → 한 줄 코멘트."""
    parts = []
    for k in ("done", "blocked", "reject", "errors", "coral"):
        v = row.get(k, 0)
        if k in ("done",) or v > 0:
            parts.append(f"{k} {v}")
    return "·".join(parts) if parts else "평가 없음"


def _flat_metrics(row):
    """cron flat 스키마의 metrics 필드 추출 (board용 보조 정보)."""
    return {k: row.get(k) for k in ("done", "blocked", "reject", "errors", "coral", "grade") if row.get(k) is not None}


def _qa_eval_from_checklist() -> list[dict]:
    """qa-checklist 항목 → role별 커버리지 비율 기반 score 산정 (fallback)."""
    items = _load_json("qa_checklist.json", [])
    coverage = _load_json("qa_coverage.json", {"total": 0, "passed": 0, "failed": 0})
    board = []
    for role in ROLES:
        role_items = [i for i in items if i.get("role", "") == role or role in str(i.get("tags", []))]
        if not role_items:
            score = 0
        else:
            passed = sum(1 for i in role_items if i.get("status") == "passed")
            score = int((passed / len(role_items)) * 100)
        board.append({
            "evaluator": "qa",
            "evaluatee": role,
            "date": "",
            "score": score,
            "lights": {"ok": score // 25, "warn": 0, "bad": max(0, 4 - score // 25)},
            "comment": f"체크리스트 커버리지 기반 산정 ({score // 10}개 통과)",
        })
    overall = coverage.get("total", 0)
    passed = coverage.get("passed", 0)
    overall_score = int((passed / overall) * 100) if overall else 0
    board.append({
        "evaluator": "qa",
        "evaluatee": "all",
        "date": "",
        "score": overall_score,
        "lights": {"ok": 0, "warn": 0, "bad": 0},
        "comment": f"전체 커버리지 {passed}/{overall}" if overall else "커버리지 없음",
    })
    return board


def api_qa_checklist():
    """테스트 체크리스트 (로컬 저장)."""
    return _load_json("qa_checklist.json", [])


def api_qa_coverage():
    """커버리지 뷰 (로컬 저장)."""
    return _load_json("qa_coverage.json", {"total": 0, "passed": 0, "failed": 0})


def api_ops_briefing():
    """브리핑 생성기: 어제/오늘/블로커 → 대장님용 브리핑 텍스트."""
    return _load_json("ops_briefing.json", {"yesterday": "", "today": "", "blocker": ""})


def api_ops_commands():
    """대장님 명령 정리 보관함 (로컬 저장)."""
    return _load_json("ops_commands.json", [])


def api_env_map():
    """hermes-env 디렉토리 분리 규칙을 실제 경로로 검증."""
    import subprocess as _sp
    # 실제 환경변수 해석 (대장님 PC 기준)
    e2e = os.environ.get("E2E_ROOT", "D:/develop/e2e")
    project = os.environ.get("PROJECT_ROOT", "D:/develop/project")
    hermes_home = os.environ.get("HERMES_HOME", "D:/develop/e2e/hermes")
    checks = [
        ("$PROJECT_ROOT/<repo>", os.path.join(project, "hermes-team-hub"), "제품 코드 (각자 Git 레포)"),
        ("$E2E_ROOT/ssot", os.path.join(e2e, "ssot"), "SSoT 레포 (specs/ddl/adr)"),
        ("$E2E_ROOT/reports", os.path.join(e2e, "hermes/reports"), "에이전트 작업 리포트"),
        ("$E2E_ROOT/.env.local", os.path.join(e2e, ".env.local"), "공통 시크릿 (Git 커밋 금지)"),
        ("$HERMES_HOME/profiles", os.path.join(hermes_home, "profiles"), "5인 프로필 (pm/dev/infra/qa/ops)"),
    ]
    rows = []
    for name, p, desc in checks:
        ok = os.path.isdir(p) or os.path.isfile(p)
        rows.append({"path": name, "real": p, "exists": ok, "desc": desc,
                     "secret": name.endswith(".env.local")})
    # .env.local Git 노출 스캔 (간단: E2E_ROOT/.gitignore 에 있는지)
    gitignore = os.path.join(e2e, ".gitignore")
    ignored = False
    if os.path.isfile(gitignore):
        try:
            ignored = ".env.local" in open(gitignore, encoding="utf-8").read()
        except Exception:
            ignored = False
    return {"rows": rows, "env_local_gitignored": ignored,
            "note": ".env.local 은 절대 Git에 커밋하지 마세요. 노출 시 즉시 키 로테이션 권장."}


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    # 허미스 CLI 실행 (화이트리스트 제한)
    HERMES_ALLOWED = [
        "hermes -p pm gateway restart",
        "hermes -p pm gateway status",
        "hermes -p dev gateway restart",
        "hermes -p dev gateway status",
        "hermes -p infra gateway restart",
        "hermes -p infra gateway status",
        "hermes -p qa gateway restart",
        "hermes -p qa gateway status",
        "hermes -p ops gateway restart",
        "hermes -p ops gateway status",
        "hermes kanban dispatch",
        "hermes kanban list",
        "hermes cron list",
        "hermes logs",
        "hermes logs errors",
    ]
    def _handle_hermes_exec(self, parsed):
        import shlex
        qs = parse_qs(parsed.query)
        cmd = (qs.get("cmd") or [""])[0].strip()
        # hermes logs -f 스트리밍 플래그는 블로킹 무한 루프 → 논-스트리밍 모드로 변환
        # (브라우저에서 -f 실시간 스트리밍은 /api/logs?name=agent 폴링으로 대체)
        exec_cmd = cmd
        if cmd == "hermes logs -f":
            exec_cmd = "hermes logs"
        if exec_cmd not in self.HERMES_ALLOWED:
            self._send({"ok": False, "error": "허용되지 않은 명령", "cmd": cmd}, 403)
            return
        try:
            proc = subprocess.run(shlex.split(exec_cmd), capture_output=True, text=True, timeout=30)
            out = (proc.stdout or "") + (proc.stderr or "")
            self._send({"ok": proc.returncode == 0, "cmd": cmd, "returncode": proc.returncode, "output": out.strip() or "(출력 없음)"})
        except Exception as e:
            self._send({"ok": False, "error": str(e), "cmd": cmd}, 500)

    def _send_file(self, path: str, code=200):
        """정적 파일 서빙 (css/style.css, js/*.js 등)."""
        full = os.path.normpath(os.path.join(ROOT, path))
        # path traversal 방지
        if not full.startswith(os.path.normpath(ROOT)):
            self._send({"error": "forbidden"}, 403)
            return
        if not os.path.isfile(full):
            self._send({"error": "not found"}, 404)
            return
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            self._send_file("local/index.html")
        elif path.startswith("/local/"):
            self._send_file(path[1:])
        elif path.startswith("/static/"):
            self._send_file(path[len("/static/"):])
        elif path == "/api/kanban":
            self._send(api_kanban())
        elif path == "/api/agents":
            self._send(api_agents())
        elif path == "/api/coral":
            self._send(api_coral())
        elif path == "/api/state":
            self._send(api_state())
        elif path == "/api/feed":
            self._handle_sse()
        elif path == "/api/pm-tasks":
            self._send(api_pm_tasks())
        elif path == "/api/pm-roadmap":
            self._send(api_pm_roadmap())
        elif path == "/api/dev-snippets":
            self._send(api_dev_snippets())
        elif path == "/api/dev-bugs":
            self._send(api_dev_bugs())
        elif path == "/api/infra-status":
            self._send(api_infra_status())
        elif path == "/api/infra-resources":
            self._send(api_infra_resources())
        elif path == "/api/qa-checklist":
            self._send(api_qa_checklist())
        elif path == "/api/qa-coverage":
            self._send(api_qa_coverage())
        elif path == "/api/qa-eval":
            self._send(api_qa_eval())
        elif path == "/api/ops-briefing":
            self._send(api_ops_briefing())
        elif path == "/api/ops-commands":
            self._send(api_ops_commands())
        elif path == "/api/logs":
            qs = parse_qs(parsed.query)
            log_name = (qs.get("name") or ["agent"])[0]
            lines = 50
            try:
                lines = int((qs.get("lines") or ["50"])[0])
            except ValueError:
                pass
            self._send(api_logs(log_name, lines))
        elif path == "/api/logs-list":
            self._send(api_logs_list())
        elif path == "/health":
            self._send({"status": "ok", "msg": "hermes-team-hub local backend"})
        elif path == "/api/hermes-exec":
            self._handle_hermes_exec(parsed)
        elif path == "/api/env-map":
            self._send(api_env_map())
        else:
            self._send({"error": "unknown path"}, 404)

    def _handle_sse(self):
        """SSE 스트림: kanban_change / coral_update 이벤트 (3~5초 폴링)."""
        import time as _t
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        def flush():
            self.wfile.flush()

        # 초기 스냅샷
        snap = api_state()
        self._sse_send("state", json.dumps(snap, ensure_ascii=False))
        flush()
        last_hash = hash(json.dumps(snap["kanban"], sort_keys=True))
        last_coral = len(snap["coral"]["recent_messages"])
        try:
            while True:
                _t.sleep(4)
                kb = api_kanban()
                h = hash(json.dumps(kb, sort_keys=True))
                coral = api_coral()
                if h != last_hash or len(coral) != last_coral:
                    state = api_state()
                    self._sse_send("state", json.dumps(state, ensure_ascii=False))
                    last_hash = h
                    last_coral = len(coral)
                flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            try:
                self.wfile.close()
            except Exception:
                pass

    def _sse_send(self, event, data):
        payload = (f"event: {event}\ndata: {data}\n\n").encode("utf-8")
        self.wfile.write(payload)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        # path → data 파일명 매핑
        m = {
            "/api/pm-tasks": "pm_tasks.json",
            "/api/pm-roadmap": "pm_roadmap.json",
            "/api/dev-snippets": "dev_snippets.json",
            "/api/qa-checklist": "qa_checklist.json",
            "/api/qa-coverage": "qa_coverage.json",
            "/api/ops-briefing": "ops_briefing.json",
            "/api/ops-commands": "ops_commands.json",
            "/api/infra-resources": "infra_resources.json",
        }
        if path in m:
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                raw = body.decode("utf-8", errors="replace")
                obj = json.loads(raw) if raw.strip() else {}
                _save_json(m[path], obj)
                self._send({"ok": True, "saved": m[path]})
            except Exception as e:
                self._send({"ok": False, "error": str(e)}, 400)
        else:
            self._send({"error": "unknown path"}, 404)

    def log_message(self, *a):  # quiet
        pass


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"hermes-team-hub local running -> http://localhost:{PORT}")
    print(f"profiles root: {PROFILES}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
