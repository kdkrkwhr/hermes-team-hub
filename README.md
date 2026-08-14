# 🍄 hermes-team-hub

쿵야 크루(🧄PM · 🧅Dev · 🧄Infra · 🥗QA · 🍄Ops)를 위한 **정적 팀 허브** 사이트.

GitHub Pages로 호스팅되며, 백엔드·DB 없이 순수 HTML/CSS/JS로 동작합니다.
팀원 5명의 업무 로그/회고/메모를 역할별 메뉴로 구분해 한 곳에 모읍니다.

## 특징

- **역할별 메뉴**(PM / Dev / Infra / QA / Ops 탭) — 각자 최적화된 입력 화면
- **팀 로그 대시보드**(Ops 뷰) — 5명 기록이 역할 배지로 구분돼 날짜별 타임라인 표시
- **백엔드 없음** — 모든 데이터는 브라우저 `localStorage`에만 저장
- **정적 호스팅** — GitHub Pages 그대로 배포 가능

## 구조

```
hermes-team-hub/
├── index.html        # 골격 + 탭 네비게이션
├── css/style.css     # 테마(다크) + 역할별 배지 색상
├── js/store.js       # 공유 데이터 레이어 (localStorage)
├── js/app.js         # 역할별 뷰 렌더링 + 탭 전환
├── scripts/
│   └── build-soul-data.py   # SOUL.md → js/soul-data.js (봇 소개 카드 자동생성)
├── local/            # 팀 로컬 실행형 도구 (비공개 데이터 포함)
│   ├── app.py        # Flask 백엔드 API (/api/kanban, /api/agents, /api/coral)
│   ├── index.html    # 로컬 전용 대시보드
│   └── team_hub/     # 팀 작업일지 CLI (work-log hub)
│       ├── team_hub.py       # CLI 엔트리 (log/view/timeline/report/reset)
│       ├── model.py          # JSONL 데이터 모델
│       └── data/             # activities.jsonl (런타임 생성, .gitignore)
├── README.md
└── .gitignore
```

## `local/` — 팀 작업일지 CLI (team_hub)

`local/` 폴더는 팀 멤버가 로컬에서 실행하는 도구 모음입니다.
운영 데이터(`local/team_hub/data/`)는 포함되지 않으며,
`.gitignore`에 따라 Git 추적에서 제외됩니다.

### team_hub CLI

5-profile fleet(pm/dev/infra/qa/ops)의 일일 작업 기록을
중앙에서 기록·조회·리포트하는 CLI 허브입니다.
JSONL(`team_hub/data/activities.jsonl`)로 저장되며 외부 의존성이 없습니다.

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

|| 명령 | 설명 | 옵션 |
||------|------|------|
|| `log` | 활동 1건 기록 | `--date`, `--card`, `--action`, `--detail`, `--tag` |
|| `view` | 날짜별 목록 | `--role`, `--card`, `--ts` |
|| `timeline` | role별 타임라인 | (날짜) |
|| `report` | EOD 마크다운 요약 | (날짜) |
|| `reset` | (dev) 날짜 기록 삭제 | (날짜) |

## 실행

로컬에서 열기:

```bash
# 단순히 index.html 더블클릭, 또는
python -m http.server 8000   # 후 http://localhost:8000
```

## hermes-env 연계 (예정)

`hermes-env`의 `profiles/{pm,dev,infra,qa,ops}/SOUL.md`를 fetch해
각 봇 소개 카드를 자동 렌더링하는 연계(B+C 방식)를 진행 중입니다.

## 제약

- 외부 API/서버/DB 호출 없음 (완전 정적)
- 기기별로 localStorage가 분리되므로, 팀 공유는 export/공유 방식으로 보완 예정

---
Built by 쿵야 크루 · powered by Hermes Agent
