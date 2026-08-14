#!/usr/bin/env python3
"""build-soul-data.py — hermes-env 연계 빌드 스크립트

hermes 프로젝트의 ``profiles/{pm,dev,infra,qa,ops}/SOUL.md`` 를 fetch(읽어)
각 봇의 편집자 설정(SOUL)을 파싱해 team-hub 정적 페이지에서 바로 쓸 수 있는
``js/soul-data.js`` 로 변환한다.

정적 사이트 제약: 런타임 network 호출 없음. 빌드 시점에 로컬 파일만 읽어
JSON(== JS 객체 리터럴) 으로 직렬화한다. JSON 은 JS 의 valid literal 이므로
``window.SOUL_DATA = <json>;`` 형태로 안전하게 출력한다.

사용법:
    python scripts/build-soul-data.py              # dry-run (stdout preview)
    python scripts/build-soul-data.py --apply      # js/soul-data.js 로 씀
    HERMES_PROJECT_ROOT=/path python scripts/build-soul-data.py --apply
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# index.html 의 CSS 변수 / 아이콘과 1:1 매핑 (골격 app.js ROLES 와 동일)
ROLE_MAP = {
    "pm":    {"label": "🧄 PM",    "icon": "🧄", "color": "var(--pm)",   "view": "view-pm",   "name": "마늘쫑쿵야"},
    "dev":   {"label": "🧅 Dev",   "icon": "🧅", "color": "var(--dev)",  "view": "view-dev",  "name": "양파쿵야"},
    "infra": {"label": "🧄 Infra","icon": "🧄", "color": "var(--infra)", "view": "view-infra","name": "무시쿵야"},
    "qa":    {"label": "🥗 QA",    "icon": "🥗", "color": "var(--qa)",   "view": "view-qa",   "name": "샐러리쿵야"},
    "ops":   {"label": "🍄 Ops",   "icon": "🍄", "color": "var(--ops)",  "view": "view-ops",  "name": "버섯쿵야"},
}

def editor_block(text: str) -> str:
    """SOUL.md 에서 편집자 설정 블록만 추출.

    구조: [COGNITIVE REFLECTION protocol] ── `---` ── [편집자 설정(== 나머지 전부)]
    즉 **첫 번째 `---` 이후의 텍스트 전체**가 편집자 설정이다.
    (SOUL.md 내부에 추가 `---` 구분선이 섞여 있을 수 있으니 maxsplit=1)
    """
    idx = text.find("\n---")
    if idx == -1:
        idx = text.find("---\n")
        if idx == -1:
            return text.strip()
        # `---` 가 파일 맨 앞에 있는 경우
        if idx == 0:
            rest = text[idx+4:]
        else:
            rest = text[idx+4:]
        return rest.strip()
    return text[idx+4:].strip()


def extract_name(block: str, role: str) -> str:
    """'당신은 'X쿵야' — ' 구문 또는 '# X (Role)...' 헤딩에서 이름 추출.
    없으면 role(대문자) 사용.
    """
    m = re.search(r"당신은\s+'([^']+)'", block)
    if m:
        return m.group(1)
    # 편집자 설정에서 '당신은 'X쿵야'' 를 못 뽑으면 role 기본 이름 사용.
    # (헤딩 기반 추출은 일부 SOUL.md 헤딩이 '# PERSONA — ...' 식으로 name이 아니라
    #  별칭/라벨이라 부정확 → canonical name은 ROLE_MAP 이 우선)
    return ROLE_MAP.get(role, {}).get("name", role.capitalize())


def extract_identity(block: str) -> str:
    """'당신은 ...' 라인(정체성) 1줄 요약."""
    for line in block.splitlines():
        if "당신은" in line and ("쿵야" in line or "입니다" in line or "입니다." in line):
            return line.strip().lstrip("- ").strip()
        if line.startswith("You are Hermes"):
            continue
    return ""


def extract_tone(block: str) -> str:
    """'## 말투' / '# 말투' 섹션의 첫 번째 내용 줄."""
    lines = block.splitlines()
    capture = False
    for i, line in enumerate(lines):
        if re.match(r"^#{1,2}\s*말투", line):
            capture = True
            continue
        if capture:
            ln = line.strip()
            if ln and not ln.startswith("#"):
                return ln
            if ln.startswith("#"):
                # 또 다른 섹션 헤딩이면 멈춤
                return ""
    return ""


def md_to_html(md: str) -> str:
    """SOUL.md 편집자 설정을 최소 마크다운→HTML 로 변환.
    table/bullet/header/quote/code-block 정도만 처리한다.
    """
    out = []
    in_table = False
    in_ul = False
    in_code = False
    skip_table_head = False
    for raw in md.splitlines():
        line = raw.rstrip()

        # 코드 블록
        if re.match(r"^`{3,}", line):
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                out.append('<pre><code>')
                in_code = True
            continue
        if in_code:
            out.append(html_escape(line) + "\n")
            continue

        # 테이블 구분선
        if line.startswith("|") and re.match(r"^\|?\s*-+\s*\|", line):
            skip_table_head = False
            continue
        # 테이블 행
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not in_table:
                in_table = True
                out.append("<table>")
                skip_table_head = True
            if skip_table_head:
                skip_table_head = False
                continue
            out.append("<tr>" + "".join(f"<td>{html_escape(c)}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False

        stripped = line.strip()
        # `---` 구분선(divider) — 출력에서 제거
        if stripped == "---":
            if in_ul:
                out.append("</ul>")
                in_ul = False
            continue
        # 리스트
        m = re.match(r"^[-*]\s+(.+)", stripped)
        if m:
            if not in_ul:
                in_ul = True
                out.append("<ul>")
            out.append(f"<li>{inline_html(m.group(1))}</li>")
            continue
        if stripped == "" or not stripped.startswith("-*"):
            if in_ul and stripped and not m:
                out.append("</ul>")
                in_ul = False

        # 헤더
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            level = len(m.group(1))
            out.append(f"<h{level}>{inline_html(m.group(2))}</h{level}>")
            continue

        if not stripped:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append("")
            continue

        # 블록딧불미 / 일반 문단
        out.append(f"<p>{inline_html(stripped)}</p>")

    if in_ul:
        out.append("</ul>")
    if in_table:
        out.append("</table>")
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def inline_html(text: str) -> str:
    """문장 단위 인라인 마크다운 처리 (굵게/기울임/코드/링크)."""
    text = html_escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(^|\s)[*_]([^*]+)[*_](\s|$)", r"\1<em>\2</em>\3", text)
    return text


def html_escape(s: str) -> str:
    if not s:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace("\"", "&quot;"))


def fetch_role_soul(hermes_root: Path, role: str) -> dict:
    """한 프로필의 SOUL.md 를 읽어 메타데이터 딕셔너리 반환."""
    path = hermes_root / "profiles" / role / "SOUL.md"
    raw = path.read_text(encoding="utf-8")
    block = editor_block(raw)
    meta = ROLE_MAP.get(role, {"label": role, "icon": "🤖", "color": "var(--dev)", "view": f"view-{role}"})
    return {
        "role": role,
        "label": meta["label"],
        "icon": meta["icon"],
        "color": meta["color"],
        "view": meta["view"],
        "name": extract_name(block, role),
        "identity": extract_identity(block),
        "tone": extract_tone(block),
        "html": md_to_html(block),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None,
                    help="team-hub repo root (auto: script dir's parent)")
    ap.add_argument("--hermes-root", default=None,
                    help="override hermes project root")
    ap.add_argument("--apply", action="store_true",
                    help="write js/soul-data.js (default: dry-run preview)")
    args = ap.parse_args()

    # hermes-project root: env var > --hermes-root > default
    hermes_root = Path(args.hermes_root or os.environ.get(
        "HERMES_PROJECT_ROOT", "D:/develop/e2e/hermes")).resolve()
    if not hermes_root.exists():
        print(f"ERROR: HERMES_PROJECT_ROOT not found: {hermes_root}", file=sys.stderr)
        print("  set HERMES_PROJECT_ROOT env var or pass --hermes-root", file=sys.stderr)
        return 1

    # team-hub root
    if args.root:
        hub_root = Path(args.root).resolve()
    else:
        # 이 스크립트는 team-hub/scripts/ 에 있음 → team-hub 루트는 parent
        hub_root = Path(__file__).resolve().parent.parent

    roles = ["pm", "dev", "infra", "qa", "ops"]
    data = {}
    for role in roles:
        soul_path = hermes_root / "profiles" / role / "SOUL.md"
        if soul_path.exists():
            data[role] = fetch_role_soul(hermes_root, role)
            print(f"  fetched: {soul_path}", file=sys.stderr)
        else:
            print(f"  WARN: missing {soul_path}", file=sys.stderr)

    # js/soul-data.js 로 출력 (JSON 은 JS valid literal)
    out = "// soul-data.js — 자동 생성 파일.직접 편집 금지.\n"
    out += "// build: python scripts/build-soul-data.py --apply\n"
    out += "/* global window */\n"
    out += "window.SOUL_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + "\n;\n"

    out_path = hub_root / "js" / "soul-data.js"
    if args.apply:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out, encoding="utf-8")
        print(f"\nWROTE: {out_path} ({len(data)} roles)", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
