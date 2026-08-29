# Initial Decisions

## 확정

- 게임명: No Riichi No Fuku
- 웹 기반
- 간단 회원가입/로그인
- 회원 프로필 이름/이미지는 계정 데이터로 유지
- 1인 플레이
- 플레이어 1 + CPU 3
- 4인 일본 리치마작
- 동풍전
- 매 대국 시작 전 CPU 3명 재선택
- 좌석별 프로필/이름/점수 등 표시
- CPU 프로필 클릭 시 상세 정보
- 주요 상황 말풍선/대사
- CPU 4위 시 해당 CPU `defeat_stage + 1`
- `defeat_stage` 증가에 따라 CPU 난이도 증가
- 3회 패배 CPU는 최종 완료 후 선택 불가
- 플레이어 4위 시 HP -1
- HP 0이면 게임 오버
- CPU 4위 종료 시 단계별 CG + 결과 대사
- 최고 관리자 1종
- 최고 관리자 최초 비밀번호 변경 강제
- 최고 관리자에서 회원/CPU/대사/CG/기본 설정 관리
- Docker 기반
- CG 파일은 Git 저장소에 만들거나 커밋하지 않음
- 기본 CPU seed 몇 명 포함
- 초기 CPU 판단에 외부 LLM/API 사용 안 함

## 초기 기술 결정

- React + TypeScript + Vite
- FastAPI + Python
- PostgreSQL
- WebSocket
- RiichiEnv 0.4.8 1차 엔진 후보
- 초기 프로젝트 라이선스 MIT
- GPL/AGPL 핵심 소스가 필요해지면 프로젝트 라이선스도 호환 계열로 전환

## Docker 검증 시점

- 개발 중에는 현재 Docker/Compose 골격을 유지하되 기능 구현과 로컬 테스트를 우선한다.
- 실제 `docker compose config/build/up`, nginx 경유 API, PostgreSQL health와 persistent
  volume 검증은 기능 구현이 완료된 최종 통합 단계에서 수행한다.
- 최종 Docker 검증 전에는 Docker 배포 완료로 간주하지 않는다.

## 백엔드 기반

- SQLAlchemy 2.x 동기 session과 `psycopg` 드라이버를 사용한다.
- Alembic migration을 DB schema의 기준으로 사용한다.
- 최고 관리자와 일반 회원은 `users`를 공유한다. 최고 관리자는 플레이어 전용 필드
  (`player_name`, 프로필 이미지, 현재/최대 HP)를 `NULL`로 둘 수 있다.
- 일반 회원 생성 단계에서는 플레이어 전용 필드를 서비스 계층에서 필수 검증한다.
- 최대 HP 값은 아직 확정하지 않았으며 migration이나 seed에 임의 기본값을 넣지 않는다.
- 최고 관리자 bootstrap은 환경변수의 ID/초기 암호로 최고 관리자가 없을 때만 생성하며,
  기존 최고 관리자의 암호나 로그인 ID를 덮어쓰지 않는다.
- 기본 CPU seed는 slug 기준 create-only로 입력한다. 이후 관리자 수정값은 재실행으로
  덮어쓰지 않는다.
- `cpu_result_assets`에는 런타임 저장소 key와 metadata만 기록하고 파일은 만들지 않는다.

## RiichiEnv 0.4.8 스파이크 확정 사항

2026-08-29에 PyPI의 `riichienv==0.4.8`을 Python 3.12 환경에 실제 설치하고
`backend/app/spikes/riichienv_0_4_8.py`로 4좌석 자동 제어 동풍전 완주를 확인했다.

### 초기화와 제어 API

```python
from riichienv import GameRule, RiichiEnv

env = RiichiEnv(
    game_mode="4p-red-east",
    rule=GameRule.default_tenhou(),
    seed=5,
)
observations = env.reset()

while not env.done():
    actions = {
        seat: controllers[seat].choose_action(observation)
        for seat, observation in observations.items()
    }
    observations = env.step(actions)

scores = env.scores()
ranks = env.ranks()
```

- `reset()`과 `step()`은 현재 선택이 필요한 좌석 번호를 key로 하고 해당 좌석의
  `Observation`을 value로 하는 `dict[int, Observation]`을 반환한다.
- 같은 단계에서 여러 좌석의 응답이 필요할 수 있으므로 반환된 모든 좌석의 행동을
  `dict[int, Action]`으로 `step()`에 전달한다.
- 따라서 좌석 0을 사람 입력 adapter, 좌석 1~3을 CPU agent로 분리해 같은 API로
  제어할 수 있다. 스파이크에서는 네 좌석 모두 자동 선택해 완주하되 이 좌석별
  controller 경계를 확인했다.
- `Observation.to_dict()`의 확인된 최상위 필드는 `player_id`, `hands`, `melds`,
  `discards`, `dora_indicators`, `scores`, `riichi_declared`, `legal_actions`, `events`,
  `honba`, `riichi_sticks`, `round_wind`, `oya`이다.
- `observation.legal_actions()`는 `Action` 목록을 반환하며, `Action.to_dict()`의
  확인된 필드는 `type`, `tile`, `consume_tiles`, `actor`이다. `ActionType`에는
  discard/chi/pon/kan/ron/riichi/tsumo/pass 등이 포함된다.
- `observation.hand`에는 자기 손패만 노출되고 `to_dict()["hands"]`의 다른 좌석
  손패는 빈 목록이다. 전체 이벤트 로그인 `env.mjai_log`는 서버 내부 검증/기록용이며
  클라이언트 관측으로 직접 노출하지 않는다.

### 확정 룰과 종료 동작

- 모드: 4인 `4p-red-east` (`env.game_mode == 1`)
- 룰 preset: `GameRule.default_tenhou()`
- 시작 점수: 각 25,000점, 반환점/서든데스 기준 30,000점
- 적도라: 5만/5통/5삭 각 1장씩 포함
- 토비: 국 종료 후 한 명이라도 0점 미만이면 대국 종료(0점은 종료 조건 아님)
- 예정 마지막 국은 동4국이다. 동4국에서 비연장이며 최고점이 30,000점 이상이면
  종료하고, 전원이 30,000점 미만이면 남입한다.
- 동4국 또는 연장 국의 친이 연장 조건을 충족한 경우, 친이 1위이면서 30,000점
  이상이면 종료한다. 도중유국은 이 친 종료 조건을 적용하지 않는다.
- 남입 후 비연장이며 최고점이 30,000점 이상이면 그 국에서 종료한다.
- 30,000점 도달자가 없어도 남4국의 비연장 결과에서 종료한다. 남4국 친이
  연장하고 종료 조건을 충족하지 못하면 남4국을 반복한다.
- 동일 점수 순위는 좌석 번호가 작은 쪽이 우선한다. 25,000점 동점 초기 상태에서
  `ranks()`는 좌석 0부터 `[1, 2, 3, 4]`를 반환했다.

고정 seed 5 스파이크 결과는 남입 및 남4국 연장을 포함한 11국/788 step으로
종료됐고 최종 점수는 `[33200, 26100, 24300, 16400]`, 순위는
`[1, 2, 3, 4]`였다. 화료 6회, 유국 5회를 포함했으며 네 좌석 모두 실제 행동
요청을 받아 제어되었다.

## 스파이크 전 초기 가정(확정 완료)

첫 통합 전에 다음을 후보로 두었으며, 위 0.4.8 스파이크에서 실제 동작을 확정했다.

```text
RiichiEnv game_mode = 4p-red-east
Tenhou 계열 기본 규칙
```

문서 예시보다 설치된 라이브러리의 실제 API를 계속 우선한다.

## 아직 결정하지 않음

- 최대 HP 실제 값
- 게임 오버 후 진행 초기화/재시작 정책
- 최종 전체 완료 후 엔딩 처리
- CG 실제 이미지/연출
- 캐릭터 최종 이름/설정/프로필 이미지
- Mortal 사용 여부
