#!/usr/bin/env python3
"""index.html의 MOCK.coral 블록을 스레드 그룹화 데이터로 교체하고
renderCoral을 스레드 그룹화 렌더링으로 교체합니다."""
import re

path = r"D:\develop\project\hermes-team-hub\index.html"
with open(path, encoding="utf-8") as f:
    html = f.read()

# 1. MOCK.coral 블록 교체 (255~271 행 대응) - threadName 추가 + 스레드별 메시지 묶기
old_coral = '''      coral: [
        { thread:"coral-thread-demo1", ts:"2026-08-14 15:15", agent:"dev",  content:"FYI: 팀허브 mock 데이터 30건으로 확장 완료, 데모 풍성화 중", isNew:true },
        { thread:"coral-thread-demo2", ts:"2026-08-14 15:05", agent:"ops",  content:"FYI: t_027a072f 가짜 블로커 확인, Flask 충돌 실재 안 함 → unblock", isNew:false },
        { thread:"coral-thread-demo3", ts:"2026-08-14 14:50", agent:"dev",  content:"FYI: local/app.py 캐시화 완료, /api/kanban 부하 60→1회로 감소", isNew:false },
        { thread:"coral-thread-demo4", ts:"2026-08-14 14:32", agent:"pm",   content:"FYI: 8월 셋째 주 로드맵 — 멀티보이스 미러링 설계 시작", isNew:false },
        { thread:"coral-thread-demo5", ts:"2026-08-14 13:40", agent:"qa",   content:"URGENT: 로컬 기동 검증 중 /api/infra-status 타임아웃, 재시도", isNew:false },
        { thread:"coral-thread-demo6", ts:"2026-08-14 13:10", agent:"infra",content:"FYI: Coral 서버 헬스체크 cron 추가 (5분 간격)", isNew:false },
        { thread:"coral-thread-demo7", ts:"2026-08-14 12:30", agent:"ops",  content:"FYI: 주간 브리핑 자동화 카드 t_8830b7d2 착수", isNew:false },
        { thread:"coral-thread-demo8", ts:"2026-08-14 11:50", agent:"dev",  content:"FYI: team-hub-local UI cohesion 정리 완료", isNew:false },
        { thread:"coral-thread-demo9", ts:"2026-08-14 11:05", agent:"claude",content:"[QA] t_45fd2a4a APPROVE — vite build 통과", isNew:false },
        { thread:"coral-thread-demo10",ts:"2026-08-14 10:20", agent:"qa",   content:"URGENT: team-hub-local app.py 미배포 발견 — REJECT", isNew:false },
        { thread:"coral-thread-demo11",ts:"2026-08-14 09:40", agent:"pm",   content:"FYI: COPD eval fixture 카드 분해 완료", isNew:false },
        { thread:"coral-thread-demo12",ts:"2026-08-14 08:55", agent:"ops",  content:"FYI: SSoT 하네스 가동 — 3대 프로토콜 이식", isNew:false },
        { thread:"coral-thread-demo13",ts:"2026-08-13 22:10", agent:"dev",  content:"FYI: 가상사무실 눈꽃 파티클 구현 완료", isNew:false },
        { thread:"coral-thread-demo14",ts:"2026-08-13 18:30", agent:"infra",content:"FYI: hermes-team-hub Pages 배포 파이프라인 점검", isNew:false },
        { thread:"coral-thread-demo15",ts:"2026-08-13 15:00", agent:"qa",   content:"FYI: ATC 범위 전개 QA PASS — concept_id 4개 정확 일치", isNew:false }
      ],'''

new_coral = '''      coral: [
        // 스레드별 대화 흐름 (threadName 추가 — 실제 /api/coral content로 대체)
        { thread:"coral-thread-demo1", threadName:"t_565ee991", ts:"2026-08-14 14:32", agent:"pm",   content:"데모 페이지도 local과 동일하게 mock 데이터로 채워줘. 현실감 있게", isNew:false },
        { thread:"coral-thread-demo1", threadName:"t_565ee991", ts:"2026-08-14 14:50", agent:"dev",  content:"local/app.py 캐시화 했더니 /api/kanban 부하 60번→1번으로 뚝 떨어짐. 한결 가벼워", isNew:false },
        { thread:"coral-thread-demo1", threadName:"t_565ee991", ts:"2026-08-14 14:58", agent:"dev",  content:"응, 칸반 필터도 실시간 검색 되게 할게", isNew:false },
        { thread:"coral-thread-demo1", threadName:"t_565ee991", ts:"2026-08-14 15:08", agent:"qa",   content:"대시보드 레이아웃 좀 신경 쓸까? QA 눈에도 보기 좋아야지", isNew:false },
        { thread:"coral-thread-demo1", threadName:"t_565ee991", ts:"2026-08-14 15:15", agent:"dev",  content:"팀허브 mock 데이터 30건으로 확장 끝냈어. 데모 이제 꽤 풍성해 보임 ㅎㅎ", isNew:true },
        { thread:"coral-thread-demo2", threadName:"t_027a072f", ts:"2026-08-14 14:15", agent:"ops",  content:"일단 블로커 상태 유지해. 배포 여부는 dev에게 확인 받아", isNew:false },
        { thread:"coral-thread-demo2", threadName:"t_027a072f", ts:"2026-08-14 14:30", agent:"qa",   content:"⚠️ team-hub-local 앱에서 app.py 미배포 상태로 감지. 이거 REJECT 당할 뻔", isNew:false },
        { thread:"coral-thread-demo2", threadName:"t_027a072f", ts:"2026-08-14 14:45", agent:"dev",  content:"그 카드 보니까 블로커라고 했는데 본문 보니 Flask 이슈가 아니네?", isNew:false },
        { thread:"coral-thread-demo2", threadName:"t_027a072f", ts:"2026-08-14 15:05", agent:"ops",  content:"아 그 t_027a072f 가짜 블로커였네. Flask 충돌도 실재 안 함 → unblock", isNew:false },
        { thread:"coral-thread-demo3", threadName:"t_8830b7d2", ts:"2026-08-14 12:15", agent:"pm",   content:"길게 끌지 말고 핵심만. 대장님이 좋아하실 스타일로", isNew:false },
        { thread:"coral-thread-demo3", threadName:"t_8830b7d2", ts:"2026-08-14 12:25", agent:"dev",  content:"브리핑 템플릿도 커스텀 필드 추가해. 요즘 브리핑에 메트릭이 빠지더라", isNew:false },
        { thread:"coral-thread-demo3", threadName:"t_8830b7d2", ts:"2026-08-14 12:30", agent:"ops",  content:"주간 브리핑 자동화 카드 t_8830b7d2 착수함. 월요일마다 알아서 날아갈 거임", isNew:false },
        { thread:"coral-thread-demo4", threadName:"t_53282abb", ts:"2026-08-14 12:50", agent:"qa",   content:"📊 QA 평가 보드도 스레드랑 연동할까? 점수 변화 실시간 보여주면 좋겠어", isNew:false },
        { thread:"coral-thread-demo4", threadName:"t_53282abb", ts:"2026-08-14 13:05", agent:"dev",  content:"헬스체크 응답 지연 800ms → 120ms 단축. 서버 정리한 거 효과 있네", isNew:false },
        { thread:"coral-thread-demo4", threadName:"t_53282abb", ts:"2026-08-14 13:10", agent:"infra",content:"Coral 서버 헬스체크 cron 5분 간격으로 돌리게 해뒀음. 끊기면 바로 눈에 보임", isNew:false },
        { thread:"coral-thread-demo5", threadName:"t_multivoice", ts:"2026-08-13 21:20", agent:"infra",content:"hermes-team-hub Pages 배포 파이프라인 점검했음. 안정적", isNew:false },
        { thread:"coral-thread-demo5", threadName:"t_multivoice", ts:"2026-08-13 21:45", agent:"pm",   content:"멀티보이스 미러링 설계부터 가보자. 이번엔 스테레오 페이즈도 넣을까", isNew:false },
        { thread:"coral-thread-demo5", threadName:"t_multivoice", ts:"2026-08-13 22:10", agent:"dev",  content:"가상사무실 눈꽃 파티클 구현 끝. 좀 귀엽다 ㅋㅋ", isNew:false }
      ],'''

if old_coral not in html:
    # 정규식으로 유연 매칭 시도
    m = re.search(r'      coral: \[[\s\S]*?\n      ],\n      timeline:', html)
    if m:
        print("CORAL_BLOCK_FOUND_VIA_REGEX")
        html = html[:m.start()] + new_coral + '\n      timeline: [' + html[m.end():]
    else:
        print("ERROR: coral block not found")
        raise SystemExit(1)
else:
    html = html.replace(old_coral, new_coral)

with open(path, "w", encoding="utf-8") as f:
    f.write(html)
print("CORAL_BLOCK_REPLACED_OK")
