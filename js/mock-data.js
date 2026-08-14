// mock-data.js — 하드코딩된 mock JSON (정적 Pages용)
// real 서버가 없어도 모든 패널이 채워짐. 빌드 시점에 로컬 index.html의 API 응답 shape과 동일 구조.
// local/app.py 의 api_agents()/api_kanban()/api_coral() 출력과 시간적으로 유사하도록 채움.
/* global window */
window.MOCK = {
  // 5명 봇 프로필 (name/identity/tone + provider/model/fallback)
  agents: [
    { role: "pm", exists: true, name: "마늘쫑쿵야", identity: "당신은 '마늘쫑쿵야' — 프로젝트 방향을 잡고 업무를 분배하는 '프로젝트 매니저(PM)'입니다.", tone: "따뜻하고 솔직하게. '내 생각엔', '근데', '솔직히' 자연스럽게. 상대 말에 짧은 공감 한 줄 넣고 본론", provider: "nous", model: "upstage/solar-pro4:free", fallback: "nous/tencent/hy3:free" },
    { role: "dev", exists: true, name: "양파쿵야", identity: "당신은 '양파쿵야' — 전반적인 개발을 책임지는 크루입니다.", tone: "10년 넘게 친한 친구처럼 말해. 반말, 편한 톤.", provider: "nous", model: "poolside/laguna-s-2.1:free", fallback: "openrouter/cohere/north-mini-code:free" },
    { role: "infra", exists: true, name: "무시쿵야", identity: "당신은 '무시쿵야' — 양파쿵야(dev)의 개발을 보조하되 인프라적인 부분을 담당하는 크루입니다.", tone: "", provider: "openrouter", model: "nvidia/nemotron-3-super-120b-a12b:free", fallback: "nous/tencent/hy3:free" },
    { role: "qa", exists: true, name: "샐러리쿵야", identity: "당신은 '샐러리쿵야' — 양파쿵야(dev)와 무시쿵야(infra)가 작업한 결과물을 체크리스트 기준으로 채점·테스트하는 크루입니다.", tone: "10년 넘게 친한 친구처럼 말해. 반말, 편한 톤.", provider: "openrouter", model: "nvidia/nemotron-3-ultra-550b-a55b:free", fallback: "openrouter/google/gemma-4-26b-a4b-it:free" },
    { role: "ops", exists: true, name: "버섯쿵야", identity: "당신은 이 프로젝트의 '운영 및 비서(Operations)' 에이전트입니다.", tone: "", provider: "nous", model: "tencent/hy3:free", fallback: "" }
  ],

  // 진행 중 칸반 (pm/dev/infra/qa/ops 별 샘플 몇 개씩)
  kanban: [
    { id: "t_fd0cb6ce", title: "[hermes-team-hub] 데모(index.html)를 local과 동일 UI로 교체 + mock 데이터 인라인 주입", assignee: "dev", status: "running", created: "2026-08-14 14:54" },
    { id: "t_55602266", title: "[team-hub-local] UI/데이터 cohesion 정리 (래스터 통일·에러 상태·메타노트 제거)", assignee: "dev", status: "blocked", created: "2026-08-14 14:15" },
    { id: "t_53282abb", title: "[team-hub-local] team-hub-local UI/데이터 표시 전체 다듬기 + 브리핑 생성기 + 대장님 명령 보관함", assignee: "dev", status: "done", created: "2026-08-14 09:41" },
    { id: "t_01fa78c4", title: "[hermes-team-hub] 오류 수정: /api/kanban 캐시화 + 미커밋 4파일 커밋 + README 최신화 + 하위 blocked 정리", assignee: "dev", status: "done", created: "2026-08-14 14:07" },
    { id: "t_aee7497a", title: "[team-hub-local] Kanban 카드 우선순위/최신순 정렬 + done 페이징 + 부모/자식 계층 표시", assignee: "dev", status: "done", created: "2026-08-14 11:20" },
    { id: "t_6010084a", title: "[메뉴확장-Ops] 브리핑 생성기 + 대장님 명령 정리 보관함", assignee: "dev", status: "done", created: "2026-08-14 11:03" },
    { id: "t_20899d43", title: "[메뉴확장-QA] 테스트 체크리스트 + 커버리지 뷰", assignee: "dev", status: "done", created: "2026-08-14 11:03" },
    { id: "t_1ab20489", title: "[메뉴확장-Infra] 상태 대시보드 + 리소스 모니터", assignee: "dev", status: "done", created: "2026-08-14 11:03" },
    { id: "t_9b41932e", title: "[메뉴확장-Dev] 코드 스니펫 뷰어 + 버그 추적(QA 반려 카드 필터)", assignee: "dev", status: "done", created: "2026-08-14 11:03" },
    { id: "t_06902850", title: "[메뉴확장-PM] 태스크 분해기 + 로드맵 타임라인", assignee: "dev", status: "done", created: "2026-08-14 11:03" },
    { id: "t_1919f338", title: "[team-hub-local] UI/데이터 cohesion 정리 (래스터 통일·에러 상태·메타노트 제거)", assignee: "dev", status: "done", created: "2026-08-14 13:43" },
    { id: "t_4b981e22", title: "[team-hub-local] static index.html 토론/배지 재활용 + SOUL_DATA 봇 소개 카드 + 실시간 패널 fetch", assignee: "dev", status: "done", created: "2026-08-14 06:46" }
  ],

  // Coral 무전 (최근 몇 줄)
  coral: [
    { thread: "t_fd0cb6ce", threadName: "t_fd0cb6ce", ts: "2026-08-14T14:54:00Z", agent: "dev", content: "FYI: t_fd0cb6ce 착수 — root index.html과 local/index.html 통합 + MOCK 데이터 인라인 주입", mentions: [] },
    { thread: "t_fd0cb6ce", threadName: "t_fd0cb6ce", ts: "2026-08-14T14:50:00Z", agent: "dev", content: "FYI: t_1919f338 완료 — static/index.html 내부 메타노트 정리 (em-dash/§2.2 제거, 빈 값 '없음' 처리)", mentions: [] },
    { thread: "t_aee7497a", threadName: "t_aee7497a", ts: "2026-08-14T11:22:00Z", agent: "dev", content: "FYI: t_aee7497a 완료 — app.py _get_tasks_grouped 신규 구현 + /api/state 응답 구조 개선", mentions: [] }
  ],

  // PM 전용
  "pm-tasks": [
    "대장님 메뉴 확장: 브리핑 생성기 + 명령 보관함",
    "데모 페이지 UI/데이터 통합 (root ↔ local)",
    "Hermes-Agent skill 작성 가이드라인 정리"
  ],
  "pm-roadmap": [
    { month: "2026-08", goal: "team-hub UI 통합 + mock 데이터 인라인 주입" },
    { month: "2026-09", goal: "봇 메뉴 2개씩 추가 (PM/Dev/Infra/QA/Ops)" },
    { month: "2026-09", goal: "hermes-env 연동 (SOUL.md 자동 fetch)" }
  ],

  // Dev 전용
  "dev-snippets": [
    { ts: "2026-08-14", code: "const MOCK = window.MOCK; // 정적 Pages에서 fetch 대신 mock JSON 사용" },
    { ts: "2026-08-14", code: "function getJSON(u){ return window.MOCK[u] || []; }" }
  ],
  "dev-bugs": [
    { id: "t_55602266", title: "[team-hub-local] UI/데이터 cohesion 정리", assignee: "dev", status: "blocked", created: "2026-08-14 14:15" }
  ],

  // Infra 전용
  "infra-status": [
    { name: "Hermes Gateway", state: "ok", note: "정상" },
    { name: "Coral 서버 (:5555)", state: "warn", note: "세션 만료/미기동" },
    { name: "GitHub Pages", state: "ok", note: "200 OK" },
    { name: "Team Hub (localhost:5000)", state: "bad", note: "서버 다운" }
  ],
  "infra-resources": { cpu: 23, mem: 58, note: "샘플 데이터 — local/app.py 실시간 메트릭 아님" },

  // QA 전용
  "qa-checklist": [
    "데모 페이지가 local/index.html과 동일 UI를 사용하는가",
    "모든 fetch 호출이 MOCK 데이터로 대체되었는가",
    "POST 요청이 no-op (localStorage/saveAll) 처리되는가",
    "브라우저 에러 없이 모든 패널이 렌더링되는가"
  ],
  "qa-coverage": { total: 4, passed: 4, failed: 0 },

  // Ops 전용
  "ops-briefing": { yesterday: "team-hub-local UI/데이터 cohesion 정리 완료 (t_1919f338)", today: "root index.html과 local/index.html 동일 UI로 교체 + MOCK 데이터 인라인 주입", blocker: "없음" },
  "ops-commands": [
    { ts: "2026-08-14T10:53:00", text: "Coral 무전 규칙(착수=FYI, 완료=FYI) 확인" },
    { ts: "2026-08-14T09:41:00", text: "team_hub CLI (log/view/timeline/report/reset) 구현" }
  ]
};
