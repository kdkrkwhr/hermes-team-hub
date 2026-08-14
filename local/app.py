#!/usr/bin/env python3
"""
hermes-team-hub — 로컬 실행형 백엔드
표준 라이브러리만 사용 (Flask 불필요). 대장님 PC에서 실시간 agent 상태를 본다.

실행:
    python local/app.py
    -> http://localhost:5000

API:
    /api/kanban  -> hermes kanban list 파싱 JSON
    /api/agents  -> profiles/{pm,dev,infra,qa,ops}/SOUL.md 요약
    /api/coral   -> Coral 서버(:5555) 최근 무전 (세션 살아있을 때)
"""
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES = "D:/develop/e2e/hermes/profiles"
PORT = 5000

ROLES = ["pm", "dev", "infra", "qa", "ops"]


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
        if not os.path.exists(p):
            out.append({"role": role, "exists": False, "head": ""})
            continue
        with open(p, encoding="utf-8") as f:
            head = f.read(600).replace("\n", " ").strip()
        out.append({"role": role, "exists": True, "head": head})
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

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/kanban":
            self._send(api_kanban())
        elif parsed.path == "/api/agents":
            self._send(api_agents())
        elif parsed.path == "/api/coral":
            self._send(api_coral())
        elif parsed.path == "/":
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
