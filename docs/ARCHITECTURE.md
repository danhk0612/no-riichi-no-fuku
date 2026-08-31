# Architecture

## 전체 구조

```text
Browser
  |
  | HTTPS / WebSocket
  v
Web (React + nginx)
  |
  +---- REST --------------------+
  |                              |
  +---- WebSocket ----------+    |
                           v    v
                         FastAPI API
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
     Account/Admin     Game Service      Media Service
                           |
                           v
                     RiichiEnv Adapter
                           |
                    +------+------+
                    |             |
                    v             v
                Human Seat     CPU Agents x3
                                  |
                          Character AI Profile
                                  |
                           Difficulty Tier

FastAPI API ---- PostgreSQL
FastAPI API ---- media_data volume
```

## 백엔드 목표 구조

```text
backend/app/
  api/
    auth/
    admin/
    game/
  core/
    config.py
    security.py
  db/
    models/
    migrations/
  domain/
    users/
    characters/
    dialogue/
    progression/
  mahjong/
    engine.py
    riichienv_adapter.py
    state.py
    agents/
      base.py
      heuristic.py
      mortal.py        # 후속 선택 기능, 초기 생성하지 않음
    evaluation/
      efficiency.py
      defense.py
      placement.py
  media/
```

`mortal.py`는 향후 필요할 때의 위치 예시이며 초기 구현 파일로 만들 필요가 없다.

## 프론트엔드 목표 구조

```text
frontend/src/
  pages/
    Login
    Register
    Home
    CpuSelect
    Game
    Result
    GameOver
    Admin
  components/
    PlayerSeat
    CpuCard
    CpuDetail
    SpeechBubble
    MahjongTable
  features/
    auth
    profile
    characters
    game
    admin
```

## 게임 상태

서버가 authoritative state를 유지한다.

REST에서 인증된 회원이 CPU 3명을 선택해 서버 권한형 세션을 만든다. 실행 객체는
process-local cache에 두고 복구 데이터는 PostgreSQL에 저장한다.

```json
{
  "cpu_character_ids": [1, 2, 3]
}
```

WebSocket 연결 후 첫 클라이언트 메시지는 인증이다.

```json
{
  "type": "authenticate",
  "access_token": "..."
}
```

이후 클라이언트 행동 요청은 서버가 직전에 제공한 합법 행동 index만 사용한다.

```json
{
  "type": "action",
  "legal_action_index": 2,
  "action_version": 7
}
```

서버 응답 예:

```json
{
  "type": "human_turn",
  "action_version": 7,
  "turn": {
    "observation": {},
    "legal_actions": []
  }
}
```

registry는 authoritative RiichiEnv 실행 객체만 FastAPI 프로세스 메모리에 cache한다.
`game_sessions`에는 소유권, match seed, CPU/좌석 snapshot, 승인된 사람 행동 log와 완료
결과를 저장한다. 사람 행동마다 log를 commit하고 cache miss나 재시작 시 결정론적으로
재생한다. 완료 시 같은 DB transaction으로 HP 또는 CPU 진행도와 점수·순위·정산을
commit한 뒤 결과를 전송한다. 각 turn의 `action_version`과 DB row lock으로 오래된
중복 입력을 거부한다.

React 클라이언트는 access token을 현재 탭 메모리에만 유지한다. 재로그인 시 active
session을 REST로 조회해 진행 중 대국에 재접속한다. CPU 선택과 세션 생성은
상대 `/api` REST 경로를 사용하고, WebSocket도 현재 page의 `ws`/`wss` origin 아래 같은
`/api` 경로를 사용한다. 개발 시 Vite proxy가, 배포 시 nginx가 REST와 WebSocket을
FastAPI로 전달한다. 클라이언트는 서버 응답을 화면 상태로 옮길 뿐 결과와 진행도를
별도로 판정하지 않는다.

## 데이터 핵심 관계

```text
users
  1
  |
  +---- N game_sessions
  |
  +---- N user_cpu_progress N ---- 1 cpu_characters
                                  |
                                  +---- N cpu_dialogues
                                  +---- N cpu_result_assets
```

CG 파일 자체는 DB나 Git에 저장하지 않고 런타임 미디어 볼륨에 둔다.
