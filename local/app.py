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
        elif path == "/api/coral":
            self._send(api_coral())
        elif path == "/health":
            self._send({"status": "ok", "msg": "hermes-team-hub local backend"})
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
