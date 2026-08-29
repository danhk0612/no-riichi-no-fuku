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

클라이언트 전송 예:

```json
{
  "type": "discard",
  "tile": "5p"
}
```

서버 응답/이벤트 예:

```json
{
  "type": "game_event",
  "event": "dahai",
  "actor": 0,
  "tile": "5p"
}
```

클라이언트는 서버가 제공한 합법 행동만 UI에서 선택 가능하게 한다.

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
