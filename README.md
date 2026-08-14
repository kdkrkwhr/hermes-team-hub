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
├── README.md
└── .gitignore
```

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
