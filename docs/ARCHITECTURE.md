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

REST에서 인증된 회원이 CPU 3명을 선택해 process-local 세션을 만든다.

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
  "legal_action_index": 2
}
```

서버 응답 예:

```json
{
  "type": "human_turn",
  "turn": {
    "observation": {},
    "legal_actions": []
  }
}
```

registry는 소유권, authoritative RiichiEnv 세션과 정산 결과를 현재 FastAPI 프로세스
메모리에 유지한다. 같은 프로세스 재접속은 지원하지만 서버 재시작 및 여러 worker 간
공유는 아직 지원하지 않는다. 완료 시 짧은 DB transaction으로 HP 또는 CPU 진행도를
commit한 뒤 서버 산출 점수·순위와 정산 결과를 함께 전송한다.

## 데이터 핵심 관계

```text
users
  1
  |
  +---- N user_cpu_progress N ---- 1 cpu_characters
                                  |
                                  +---- N cpu_dialogues
                                  +---- N cpu_result_assets
```

CG 파일 자체는 DB나 Git에 저장하지 않고 런타임 미디어 볼륨에 둔다.
