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
    /static/<path>     -> css/style.css, js/store.js, js/soul-data.js 등
"""
import json
import os
import re
import subprocess
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


def run_hermes(args):
    try:
        out = subprocess.run(
            ["hermes"] + args, capture_output=True, text=True, timeout=30
        )
        return out.stdout + out.stderr
    except Exception as e:  # pragma: no cover
        return "ERROR: " + str(e)


def api_kanban():
    raw = run_hermes(["kanban", "list"])
    rows = []
    import re
    for line in raw.splitlines():
        m = re.search(r"(t_[0-9a-f]+)", line)
        if not m:
            continue
        tid = m.group(1)
        # assignee + status 추출 (단어 중 t_ 아닌 것)
        words = [w for w in line.replace("✓", "").replace("⊘", "").split() if w != tid]
        status = "done" if "done" in line else ("blocked" if "blocked" in line else "ready")
        assignee = ""
        title = ""
        for i, w in enumerate(words):
            if w in ("done", "blocked", "ready", "running"):
                assignee = words[i + 1] if i + 1 < len(words) else ""
                title = " ".join(words[i + 2:]) if i + 2 < len(words) else ""
                break
        rows.append({"status": status, "id": tid, "assignee": assignee, "title": title})
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


def api_coral():
    # Coral 브리지 seen 파일에서 최근 무전 읽기 (세션 없어도 브리지 로그는 있음)
    seen = os.path.join(
        os.environ.get("TEMP", "C:/Users/KDK/AppData/Local/Temp"),
        "coral-bridge-seen.txt",
    )
    if not os.path.exists(seen):
        return []
    rows = []
    with open(seen, encoding="utf-8") as f:
        for line in f.readlines()[-50:]:
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            rows.append({
                "thread": parts[0] if len(parts) > 0 else "",
                "ts": parts[1] if len(parts) > 1 else "",
                "agent": parts[-1] if len(parts) > 2 else "",
            })
    return rows


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


def api_infra_status():
    """상태 대시보드 (로컬 JSON, cron 연계 예정)."""
    return _load_json("infra_status.json", [
        {"name": "Hermes Gateway", "state": "ok", "note": "정상"},
        {"name": "Coral 서버", "state": "warn", "note": "세션 주기적 만료"},
        {"name": "GitHub Pages", "state": "ok", "note": "배포 완료"},
    ])


def api_infra_resources():
    """리소스 모니터 (로컬 메트릭 샘플)."""
    return _load_json("infra_resources.json", {"cpu": 0, "mem": 0, "note": "샘플 데이터"})


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


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

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
        elif path == "/api/ops-briefing":
            self._send(api_ops_briefing())
        elif path == "/api/ops-commands":
            self._send(api_ops_commands())
        elif path == "/health":
            self._send({"status": "ok", "msg": "hermes-team-hub local backend"})
        else:
            self._send({"error": "unknown path"}, 404)

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
            "/api/infra-status": "infra_status.json",
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
