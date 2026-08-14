# 🍄 hermes-team-hub (local)

`hermes-team-hub`의 **로컬 실행형** 버전. 백엔드가 대장님 PC에서 직접
Hermes 칸반 / 봇 프로필 / Coral 무전을 읽어 **실시간**으로 보여줍니다.

정적 Pages 버전(`/`, 데모/공개용)과 달리, 이 폴더는 **agent 정보를 실시간으로
가져올 수 있습니다** (서버가 로컬에서 직접 파일/CLI를 읽음).

## 실행

```bash
cd hermes-team-hub/local
python app.py
# 브라우저에서 http://localhost:5000 접속
```

표준 라이브러리만 사용 (Flask 불필요). Python 3.8+ 권장.

## 기능

| 영역 | 설명 |
|---|---|
| **토론/배지** (role 탭) | PM / Dev / Infra / QA / Ops 5개 탭. 각 탭은 **localStorage**에 저장된 개인 토론 기록을 `js/store.js`로 CRUD. **골격 index.html의 토론/배지 UI를 재활용**. |
| **봇 소개 카드** | 각 role 탭에 `scripts/build-soul-data.py`가 빌드한 `js/soul-data.js`에서 추출한 봇 이름/정체성/톤을 **배지 재활용** 형태로 표시. |
| **실시간 패널** (rt 탭) | 📊 대시보드 / 📋 칸반 / 🤖 봇 / 📡 무전 4개 탭. `local/app.py`의 `/api/*` fetch로 **30초 주기 자동 갱신**. |

## API (`/api/*`)

| 엔드포인트 | 설명 |
|---|---|
| `/` | `local/index.html` 정적 서빅 |
| `/api/kanban` | `hermes kanban list` 파싱 → 칸반 카드 JSON (`status`, `id`, `assignee`, `title`) |
| `/api/agents` | `profiles/{pm,dev,infra,qa,ops}/SOUL.md` → 풍성 메타데이터 (`name`, `identity`, `tone`, `head`) |
| `/api/coral` | Coral 브리지 seen 로그에서 최근 무전 (`thread`, `ts`, `agent`) |
| `/health` | 헬스 체크 |

## 정적 파일

`/static/<path>` 로 css/style.css, js/store.js, js/soul-data.js 등을 서빼합니다.
(local/index.html에서 `/static/` 기반 참조)

## 구조

```
hermes-team-hub/
├── index.html           # 골격 페이지 (데모용, Pages 호스팅용)
├── css/style.css        # 공유 다크 테마 + 역할별 배지 색상
├── js/store.js          # 공유 localStorage 데이터 레이어
├── js/soul-data.js      # build-soul-data.py 자동 생성 (SOUL.md → JS 객체)
├── js/app.js            # 골격 app.js (골격 index.html 전용)
├── scripts/
│   └── build-soul-data.py  # SOUL.md → js/soul-data.js 빌드 스크립트
├── local/
│   ├── app.py           # 로컬 백엔드 (http.server, localhost:5000)
│   ├── index.html       # local 전용 페이지 (토론/배지 + 실시간 패널 통합)
│   └── README.md        # 이 파일
├── .env.example         # HERMES_PROJECT_ROOT 설정
├── .gitignore
└── README.md
```

## 빌드: soul-data.js

```bash
cd hermes-team-hub
python scripts/build-soul-data.py              # dry-run (stdout)
python scripts/build-soul-data.py --apply      # js/soul-data.js 쓰기
```

## 참고

- **토론/배지 재활용**: `local/index.html`은 골격 `index.html`의 탭 네비·역할·배지 CSS를 재사용하고, 인라인 스크립트로 `localStorage` CRUD + `SOUL_DATA` 봇 소개 카드를 통합 렌더링.
- **실시간 fetch**: `local/app.py`가 `hermes kanban list`, `profiles/*/SOUL.md`, Coral 브리지 로그를 직접 읽어 `/api/*`로 제공.
- **데이터 분리**: 토론/배지는 브라우저 `localStorage` (기기별), 실시간 패널은 대장님 PC의 실제 Hermes 상태.
- Coral 무전은 세션이 살아있을 때만 채워집니다 (세션 만료 시 브리지 로그만 표시).

---
Built by 쿵야 크루 · powered by Hermes Agent
