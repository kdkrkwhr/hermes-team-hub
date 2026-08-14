# 🍄 hermes-team-hub

쿵야 크루(🧄PM · 🧅Dev · 🧄Infra · 🥗QA · 🍄Ops)를 위한 **팀 허브** 사이트.

- **🌐 공개 데모 (GitHub Pages)**: https://kdkrkwhr.github.io/hermes-team-hub/
  - 정적 Pages 버전은 **데모용**이며, 실제 하드코딩된 URL/데이터가 아닙니다.
  - **⚠️ 고정 URL 경고**: 이 데모 URL은 정적 호스팅 URL이며, 서비스 엔드포인트가
    아닙니다. 실제 서비스 호출을 위해서는 `local/` 실행형(`python local/app.py`)을
    사용하거나, [HARNESS-5] `.env.example`에 의존성 자동 추적 규칙에 따라
    환경 변수로 관리해야 합니다.
- **💻 로컬 실행형 (실시간 agent 연동)**: `local/` 폴더 → `python local/app.py` → http://localhost:5000

> 정적 Pages 버전은 데모/공개용입니다 (역할별 탭 + 팀 로그 대시보드, localStorage 기반).
> 실시간 칸반/봇/무전 연동은 로컬 실행형을 사용하세요.

## 특징

- **역할별 메뉴**(PM / Dev / Infra / QA / Ops 탭) — 각자 최적화된 입력 화면
- **팀 로그 대시보드**(Ops 뷰) — 5명 기록이 역할 배지로 구분돼 날짜별 타임라인 표시
- **실시간 연동 (local 실행형)**: `local/app.py`가 Hermes 칸반·봇 프로필·Coral 무전을
  실시간으로 읽어 `/api/*`로 제공 (in-memory 캐시 + SSE 스트림)
- **백엔드 없음 (정적 버전)** — 모든 데이터는 브라우저 `localStorage`에만 저장
- **정적 호스팅** — GitHub Pages 그대로 배포 가능

## 구조

```
hermes-team-hub/
├── index.html        # 골격 + 탭 네비게이션 (정적 Pages 버전)
├── css/style.css     # 테마(다크) + 역할별 배지 색상
├── js/store.js       # 공유 데이터 레이어 (localStorage)
├── js/app.js         # 골격 index.html 전용 (역할별 뷰 렌더링 + 탭 전환)
├── js/soul-data.js   # build-soul-data.py 자동 생성 (SOUL.md → JS 객체)
├── scripts/
│   └── build-soul-data.py   # SOUL.md → js/soul-data.js (봇 소개 카드 자동생성)
├── local/            # 팀 로컬 실행형 도구 (실시간 agent 연동, 비공개 데이터 포함)
│   ├── app.py        # stdlib http.server 백엔드 API
│   │                 #   /, /static/, /health
│   │                 #   /api/kanban, /api/agents, /api/coral, /api/state
│   │                 #   /api/feed (SSE)
│   │                 #   /api/logs, /api/logs-list
│   │                 #   /api/pm-tasks, /api/pm-roadmap, /api/dev-snippets
│   │                 #   /api/dev-bugs, /api/infra-status, /api/infra-resources
│   │                 #   /api/qa-checklist, /api/qa-coverage
│   │                 #   /api/ops-briefing, /api/ops-commands
│   ├── index.html    # 로컬 전용 대시보드 (실시간 패널 + 게임 탭)
│   ├── game.js       # Canvas 무한 점프 러너 (Infra 안, localStorage 최고점)
│   ├── README.md     # local 전용 가이드
│   ├── team_hub.py   # 팀 작업일지 CLI (work-log hub)
│   └── team_hub/     # team_hub 패키지 (model.py + data/)
│       ├── __init__.py
│       ├── model.py  # JSONL 데이터 모델
│       └── data/     # activities.jsonl (런타임 생성, .gitignore)
├── .env.example        # 빌드 시크릿 / 설정 (HERMES_PROJECT_ROOT 등)
├── .gitignore
└── README.md
```

## `local/` — 로컬 실행형 백엔드 (stdlib `http.server`)

`local/` 폴더는 팀 멤버가 로컬에서 실행하는 실시간 허브입니다.
**Flask가 아니라 Python 표준 라이브러리 `http.server`만 사용**합니다
(의존성 0, 별도 설치 불필요 — Python 3.11+ 권장).

```bash
cd local
python app.py
# -> http://localhost:5000
```

### API 엔드포인트 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET  | `/` | `local/index.html` (대시보드) |
| GET  | `/static/<path>` | `css/style.css`, `js/*`, `local/game.js` 등 정적 파일 |
| GET  | `/health` | 서버 상태 확인 |
| GET  | `/api/kanban` | `hermes kanban list --json` 실시간 snapshot (in-memory 캐시 TTL 5s) |
| GET  | `/api/agents` | 5 profile SOUL.md 요약 (name/identity/tone + config model/provider) |
| GET  | `/api/coral` | Coral 브리지 seen 로그 + coral_read.txt 최근 무전 (thread/agent/content) |
| GET  | `/api/state` | 실시간 상태 스냅샷: kanban + role summary + coral recent_messages + server_up |
| GET  | `/api/feed` | SSE 스트림 (state 이벤트, 4초 폴링, kanban/coral 변화 감지) |
| GET  | `/api/logs?name=agent&lines=50` | hermes logs 대체: agent.log / errors.log 직접 읽기 (local 전용) |
| GET  | `/api/logs-list` | hermes logs list 대체: 로그 디렉터리 파일 목록 |
| GET  | `/api/infra-status` | 게이트웨이/Coral/Pages/Hub 실시간 상태 (cron 불필요, 매 refresh 신선) |
| GET  | `/api/dev-bugs` | QA 반려(blocked) 카드 필터 |
| GET  | `/api/{pm-tasks,pm-roadmap,dev-snippets,qa-checklist,qa-coverage,ops-briefing,ops-commands,infra-resources}` | 로컬 저장 JSON (게이트웨이·Infra·QA·Ops 전용 메뉴 데이터) |
| POST | `/api/{pm-tasks,...}` | 로컬 저장 JSON 쓰기 |

### team_hub CLI

5-profile fleet(pm/dev/infra/qa/ops)의 일일 작업 기록을
중앙에서 기록·조회·리포트하는 CLI 허브입니다.
JSONL(`local/team_hub/data/activities.jsonl`)로 저장되며 외부 의존성이 없습니다.

```bash
cd local

# 오늘 활동 기록 (role: pm|dev|infra|qa|ops)
python team_hub.py log dev "team_hub CLI 구현 완료" --card t_53282abb --tag cli

# 오늘 전체 보기
python team_hub.py view
python team_hub.py timeline      # role별 그룹
python team_hub.py report        # EOD 마크다운 요약

# 필터링
python team_hub.py view --role qa --ts
python team_hub.py view --card t_53282abb

# (dev) 오늘 기록 전체 삭제
python team_hub.py reset
```

#### 서브커드

| 명령 | 설명 | 옵션 |
|------|------|------|
| `log` | 활동 1건 기록 | `--date`, `--card`, `--action`, `--detail`, `--tag` |
| `view` | 날짜별 목록 | `--role`, `--card`, `--ts` |
| `timeline` | role별 타임라인 | (날짜) |
| `report` | EOD 마크다운 요약 | (날짜) |
| `reset` | (dev) 날짜 기록 삭제 | (날짜) |

## 실행

로컬에서 열기:

```bash
# 정적 Pages 버전 (데모용)
python -m http.server 8000   # 후 http://localhost:8000

# 실시간 agent 연동 (추천)
cd local
python app.py                # -> http://localhost:5000
```

## hermes-env 연계 (예정)

`hermes-env`의 `profiles/{pm,dev,infra,qa,ops}/SOUL.md`를 fetch해
각 봇 소개 카드를 자동 렌더링하는 연계(B+C 방식)를 진행 중입니다.
`HERMES_PROJECT_ROOT` env 로 루트 지정 (기본값: `D:/develop/e2e/hermes`).

```bash
python scripts/build-soul-data.py --apply
```

## 제약

- 외부 API/서버/DB 호출 없음 (완전 정적, Pages 버전)
- 기기별로 localStorage가 분리되므로, 팀 공유는 export/공유 방식으로 보완 예정

---
Built by 쿵야 크루 · powered by Hermes Agent
