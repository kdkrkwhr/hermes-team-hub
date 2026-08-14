# 팀 작업일지 (Team Work Log Hub)

5-profile fleet(pn/dev/infra/qa/ops)의 일일 작업 기록을 중앙에서 기록·조회·리포트하는 CLI 허브입니다.

## 빠른 시작

```bash
cd D:/develop/e2e/hermes/profiles/dev/cron

# 오늘 활동 기록 (role: pm|dev|infra|qa|ops)
python team_hub.py log dev "team_hub CLI 구현 완료" --card t_53282abb --tag cli

# 오늘 전체 보기
python team_hub.py view
python team_hub.py timeline      # role별 그룹
python team_hub.py report        # EOD 마크다운 요약

# 필터링
python team_hub.py view --role qa --ts
python team_hub.py view --card t_53282abb

# 개발용: 오늘 기록 전체 삭제
python team_hub.py reset
```

## 서브커드

| 명령 | 설명 | 옵션 |
|------|------|------|
| `log` | 활동 1건 기록 | `--date`, `--card`, `--action`, `--detail`, `--tag` |
| `view` | 날짜별 목록 | `--role`, `--card`, `--ts` |
| `timeline` | role별 타임라인 | (날짜) |
| `report` | EOD 마크다운 요약 | (날짜) |
| `reset` | (dev) 날짜 기록 삭제 | (날짜) |

## 데이터 모델

JSONL(`team_hub/data/activities.jsonl`) — � 외부 의존성 없음.

```json
{"role":"dev","summary":"...","action":"log","detail":"","tags":["cli"],
 "card_id":"t_53282abb","date":"2026-08-14","time":"09:36",
 "ts":"2026-08-14T00:36:54+00:00"}
```

- `role`: pm|dev|infra|qa|ops (fleet.json + discord mention-map.json과 정렬)
- `action`: log|heartbeat|block|comment|complete|claim|review
- `card_id`: kanban 카드 ID (t_xxx) — 빈 문자열 허용
- `tags`: 콤마 구분 필터링용
- `date/time`: KST 기준 (ts는 UTC ISO)

## cron 연동 (선택)

크론 잡에서 `team_hub.py log <role> <summary>`를 호출해 자동 기록을 누적할 수 있습니다.
EOD 리포트는 `team_hub.py report` 출력을 Discord에 전달하도록 jobs.json에 `no_agent` 스크립트로 등록 가능.

## 역할 배지

- pm [기획] / dev [개발] / infra [인프라] / qa [검수] / ops [운영]
