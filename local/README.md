# 🍄 hermes-team-hub (local)

`hermes-team-hub`의 **로컬 실행형** 버전. 백엔드가 대장님 PC에서 직접
Hermes 칸반 / 봇 프로필 / Coral 무전을 읽어 실시간으로 보여줍니다.

정적 Pages 버전(`/`, 데모/공개용)과 달리, 이 폴더는 **agent 정보를 실시간으로
가져올 수 있습니다** (서버가 로컬에서 직접 파일/CLI를 읽음).

## 실행

```bash
cd hermes-team-hub/local
python app.py
# 브라우저에서 http://localhost:5000 접속
```

표준 라이브러리만 사용 (Flask 불필요). Python 3.8+ 권장.

## API

| 엔드포인트 | 설명 |
|---|---|
| `/api/kanban` | `hermes kanban list` 파싱 → 칸반 카드 JSON |
| `/api/agents` | `D:/develop/e2e/hermes/profiles/{pm,dev,infra,qa,ops}/SOUL.md` 로드 |
| `/api/coral` | Coral 브리지 seen 로그에서 최근 무전 |

## 구조

```
local/
├── app.py        # 표준 라이브러리 http.server 백엔드 (localhost:5000)
└── index.html    # 대시보드/칸반/봇/무전 패널 (30초 자동 갱신)
```

## 참고

- 프론트는 루트 `css/style.css`(역할별 배지 테마)를 재활용합니다.
- 데이터는 대장님 PC 한정 (외부 공유하려면 정적 Pages 버전 사용).
- Coral 무전은 세션이 살아있을 때만 채워집니다 (세션 만료 시 브리지 로그만 표시).
