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
- 플레이어 초기/최대 HP는 3
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
- 플레이어 최대 HP는 `game_settings.player_max_hp`로 관리하며 초기 migration 값은 3이다.
- 신규 일반 회원의 `current_hp`와 `max_hp`는 가입 시점의 `player_max_hp` 값으로
  함께 초기화한다.
- 최고 관리자 bootstrap은 환경변수의 ID/초기 암호로 최고 관리자가 없을 때만 생성하며,
  기존 최고 관리자의 암호나 로그인 ID를 덮어쓰지 않는다.
- 기본 CPU seed는 slug 기준 create-only로 입력한다. 이후 관리자 수정값은 재실행으로
  덮어쓰지 않는다.
- `cpu_result_assets`에는 런타임 저장소 key와 metadata만 기록하고 파일은 만들지 않는다.

## 인증과 회원 프로필

- 비밀번호는 Argon2로 해시한다.
- 인증은 HS256 JWT access token만 사용하며 기본 만료 시간은 60분이다. refresh token과
  token 폐기는 현재 범위에 포함하지 않는다.
- JWT secret은 `JWT_SECRET` 환경변수로만 주입하며 UTF-8 기준 최소 32 bytes를 요구한다.
- 최고 관리자는 최초 비밀번호로 로그인할 수 있지만 응답의 `must_change_password`가
  `true`이다. 현재 비밀번호 검증을 통과한 비밀번호 변경 후에만 이 값을 `false`로
  변경한다. 관리자 기능 접근 제한은 관리자 API 구현 시 적용한다.
- 신규 회원 생성 시 존재하는 모든 CPU에 대해 `defeat_stage = 0` 진행 데이터를 만든다.
- 회원 프로필 API는 현재 이름 조회/수정까지만 제공한다. 프로필 이미지의 형식, 용량,
  저장 key 정책이 확정되지 않았으므로 바이너리 업로드는 구현하지 않고
  `profile_image_key`는 `NULL`로 시작한다.

## 최고 관리자 관리 API 기초

- `/api/admin` API는 활성 최고 관리자만 접근할 수 있다. 최고 관리자는 최초
  비밀번호를 변경해 `must_change_password = false`가 되기 전까지 접근할 수 없다.
- 회원 관리 대상은 `role = member`인 일반 회원으로 한정하며, 현재는 목록 조회와
  `is_active` 변경만 제공한다. 최고 관리자 계정 자체는 이 경로에서 수정하지 않는다.
- CPU 캐릭터는 삭제하지 않고 `active`로 사용 여부를 관리한다. `slug`는 생성 후
  식별자로 유지하며 수정하지 않는다.
- 관리자 API로 CPU를 생성할 때 `age_adult = true`, `profile_image_key = NULL`로
  고정하고, 기존 모든 일반 회원에게 해당 CPU의 `defeat_stage = 0` 진행 데이터를
  함께 생성한다.
- CPU 대사는 CPU별 목록/생성 및 대사 단위 수정/삭제 API로 관리한다. 대사 삭제는
  해당 DB row를 삭제한다.
- CPU/프로필 이미지와 CG 업로드는 미디어 요구사항이 확정된 뒤 별도로 구현한다.

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

## RiichiEnv adapter와 게임 세션 기초

- 애플리케이션 게임 코드는 `RiichiEnvAdapter` 뒤에서 RiichiEnv 0.4.8을 사용한다.
  adapter 생성 시 실제 설치 버전이 0.4.8인지 검사하고, 모드는 `4p-red-east`, 룰은
  `GameRule.default_tenhou()`로 고정한다.
- `MahjongAgent.choose_action(observation) -> Action`을 CPU 제어 공통 경계로 사용한다.
  실제 Tier 0/1/2 정책은 이 경계 뒤에서 후속 구현한다.
- 서버 세션은 사람을 좌석 0, 선택한 CPU 3명을 좌석 1~3에 배치한다. RiichiEnv env,
  전체 좌석 Observation과 Action 객체는 서버 메모리에만 둔다.
- 사람이 행동할 차례에는 좌석 0의 `Observation.to_dict()`와 그 시점의 합법 행동
  목록만 `HumanTurn`으로 제공한다. 다른 좌석의 손패가 빈 목록인 0.4.8 관측 경계를
  그대로 유지한다.
- 실제 0.4.8의 `Observation.to_dict()["melds"]`는 JSON dict가 아니라 pybind `Meld`
  객체를 포함한다. WebSocket 경계에서는 이를 `meld_type`, `tiles`, `called_tile`,
  `from_who`, `opened`만 가진 JSON object로 명시적으로 변환한다.
- 사람 행동은 서버가 제공했던 합법 행동 목록의 index로 내부 선택하고, adapter가
  현재 필요한 모든 좌석의 행동과 각 행동의 합법성을 다시 검사한 뒤 `env.step()`을
  호출한다. 공개 WebSocket도 이 `legal_action_index`만 행동 요청으로 받는다.
- 현재 세션과 registry는 단일 서버 프로세스 메모리 기반이다. 같은 프로세스 내
  소유권 연결과 재접속은 지원하지만 프로세스 간 공유·재시작 영속화는 지원하지 않는다.
- test-only 결정적 agent와 고정 seed 5로 완주한 결과는 300 step, 사람 행동 요청
  66회, 최종 점수 `(16700, 25000, 33300, 25000)`, 순위 `(4, 2, 1, 3)`이다.
  세 CPU 좌석 모두 실제 행동 요청을 받았다.

## 최소 마작 UI 기초

- 프론트엔드는 서버 `HumanTurn`의 seat 0 관측과 합법 행동 목록을 TypeScript 타입으로
  그대로 받는다. 다른 좌석의 숨겨진 손패를 추정하거나 별도 상태로 만들지 않는다.
- RiichiEnv 0.4.8의 tile id는 0~135 물리 패 ID로 표시한다. 4개 단위로 같은 패를
  구분하며 16/52/88은 각각 적5만/적5통/적5삭으로 표시한다. 별도 패 이미지나 더미
  이미지는 사용하지 않고 텍스트 기반 패 컴포넌트로 시작한다.
- 사람의 discard는 손패의 물리 tile id와 일치하는 합법 행동 index를 전송하고,
  치/퐁/깡/론/리치/쯔모/패스 등은 별도 행동 버튼으로 같은 index를 전송한다.
- 최소 UI는 좌석별 이름/장풍/점수/리치/버림패, 사람 손패, 도라 표시, 본장/리치봉과
  종료 점수·순위를 표현한다. 데스크톱에서는 4방향 테이블, 좁은 화면에서는 세로
  레이아웃을 사용한다.
- 현재 기본 화면은 가짜 대국 fixture 없이 연결 대기 상태를 표시한다. WebSocket route,
  인증, 세션 registry와 실제 메시지 연결은 후속 통합한다.

## Tier 0 CPU 정책

- production `Tier0Agent`는 기존 `MahjongAgent` 경계 뒤에서 RiichiEnv 0.4.8의
  `Observation`과 `Action`을 직접 사용한다. 외부 API나 새 의존성은 사용하지 않는다.
- 쯔모/론을 가장 먼저 선택하고 리치가 합법이면 리치를 선택한다. 버리기 후보는
  `calculate_shanten(hand_after_discard)` 결과가 가장 낮은 후보로 한정한 뒤, 현재
  보이는 패로 계산한 기본 유효패 수가 최상위에서 4장 이내인 후보만 남긴다.
- 유효패 근사는 자기 손패, 전체 버림패, 도라 표시패와 공개 몸통의 물리 패 ID를
  사용한다. 0.4.8의 `Observation.to_dict()["melds"]` 내부 값은 dict가 아니라
  `Meld` 객체이므로 실제 공개 패는 `Meld.tiles`에서 읽는다.
- 상대가 리치한 경우 그 상대의 버림패와 같은 종류인 현물에 작은 가중치를 준다.
  이 수비 보정은 최저 샹텐과 상위 유효패 후보 안에서만 작동하므로 Tier 0의 약한
  수비로 한정한다.
- 치/퐁/대명깡 응답은 소비 패를 제거한 뒤 샹텐이 감소하는 후보만 선택하고, 개선이
  없으면 패스한다. 암깡/가깡의 가치 판단은 Tier 0 범위에 추가하지 않는다.
- 같은 상위 후보 사이에서는 유효패 수와 리치 현물 보정을 weight로 사용하며,
  agent별 seed를 주입하면 선택 순서를 재현할 수 있다.
- RiichiEnv seed 5, CPU seed 501/502/503과 결정적 사람 행동 정책으로 production
  Tier 0 세 좌석을 주입한 동풍전은 381 step, 사람 행동 요청 92회에 종료됐다.
  최종 점수는 `(18600, 37000, 26600, 17800)`, 순위는 `(3, 1, 2, 4)`였다.

## 동풍전 결과 정산

- 결과 정산은 클라이언트가 보낸 점수나 순위를 받지 않고 완료된
  `AuthoritativeGameSession.result()`의 `MatchResult`만 사용한다. RiichiEnv가 확정한
  순위에서 정확히 rank 4인 좌석 하나를 찾는다.
- 좌석 0이 4위이면 회원 `current_hp`만 1 줄이고 CPU 진행도는 바꾸지 않는다.
  감소 결과가 0이면 정산 응답의 `game_over`를 `true`로 둔다. HP가 이미 0인 회원의
  대국 결과는 유효한 시작 상태가 아니므로 정산을 거부한다.
- 좌석 1~3이 4위이면 게임 세션의 `cpu_character_by_seat` 매핑으로 해당 CPU를 찾고,
  그 회원의 `UserCpuProgress.defeat_stage`만 1 올린다. 2에서 3이 되면
  `cpu_completed`를 `true`로 둔다. 이미 stage 3인 CPU 결과는 선택 불변식 위반으로
  정산을 거부한다.
- 회원과 CPU 진행 row는 정산 중 `SELECT ... FOR UPDATE`로 조회하고 한 DB transaction
  안에서 flush한다. HP와 CPU 진행도는 같은 결과에서 동시에 변경하지 않는다.
- `AuthoritativeGameSession.result_settled`는 현재 process-local 세션 객체에서 같은
  결과를 두 번 적용하지 못하게 한다. 대국 이력 테이블과 프로세스 재시작 이후의
  idempotency는 아직 세션 registry가 없으므로 이번 범위에 추가하지 않는다.

## CPU 선택과 재대국 기초

- 인증된 일반 회원은 `GET /api/game/cpus`에서 `active = true`이고 그 회원의
  `defeat_stage < 3`인 CPU만 조회한다. 응답은 캐릭터 표시 정보와 회원별
  `defeat_stage`를 포함하며 관리자용 AI 성향 수치는 노출하지 않는다.
- 새 대국은 서로 다른 CPU ID 정확히 3개를 요청 순서대로 좌석 1/2/3에 배치한다.
  비활성 CPU, stage 3 CPU, 해당 회원의 진행 row가 없는 CPU가 하나라도 포함되면
  전체 선택을 거부한다. HP가 0이거나 회원 게임 프로필이 아니어도 생성하지 않는다.
- 선택 검증이 끝나면 stage와 캐릭터 정보를 받는 `CpuAgentFactory`로 좌석별 agent를
  만들고 새 `AuthoritativeGameSession`을 즉시 시작한다. 고정 match seed가 있으면
  좌석별 agent seed는 `match_seed * 10 + seat`로 파생한다.
- 현재 production factory는 stage 0에만 `Tier0Agent`를 연결한다. stage 1/2 CPU는
  규칙상 선택 가능 목록에 남지만 실제 Tier 1/2 구현 전에는 세션 생성을 명시적으로
  거부한다. 구현되지 않은 난이도를 Tier 0으로 임시 대체하지 않는다.
- 결과 정산으로 stage 3이 된 CPU는 다음 선택 목록에서 즉시 제외된다. 다음 대국은
  같은 세션을 재사용하지 않고 검증된 새 선택으로 별도 authoritative session을 만든다.
- 세션 생성 서비스는 아래 process-local registry와 transport가 소유한다.

## 인증 게임 registry와 WebSocket transport

- 인증된 일반 회원은 `POST /api/game/sessions`에 서로 다른 CPU ID 3개를 보내 새
  authoritative 세션을 만든다. match seed와 session ID는 서버가 생성하고 응답은
  session ID 및 좌석 0~3의 이름/사람 여부를 반환한다.
- registry는 서버 프로세스 메모리에 게임, 소유 회원, 좌석 표시 정보와 완료 정산을
  보관한다. 한 회원은 정산되지 않은 미완료/완료 세션을 동시에 하나만 가질 수 있다.
  완료 정산까지 끝난 뒤에는 새 세션을 만들 수 있으며 이전 완료 세션도 같은 프로세스
  안에서 다시 조회할 수 있다.
- WebSocket 경로는 `/api/game/sessions/{session_id}/ws`이다. 브라우저 WebSocket에서
  임의 Authorization header를 전제로 하지 않고 JWT가 URL/query log에 남지 않도록,
  첫 JSON 메시지 `{ "type": "authenticate", "access_token": "..." }`로 인증한다.
  활성 일반 회원이 아니면 4401, 소유하지 않은 세션은 존재 여부를 숨긴 채 4404로
  종료한다.
- 인증 직후와 합법 행동 처리 후 서버는 `human_turn`을 전송한다. 클라이언트 행동은
  `{ "type": "action", "legal_action_index": N }`만 허용한다. 범위를 벗어난 index나
  잘못된 메시지는 게임을 진행하지 않고 `error`를 반환한다.
- 대국 완료 시 서버는 `AuthoritativeGameSession.result()`로 `scores`/`ranks`를 만들고
  짧은 별도 DB session에서 즉시 정산·commit한 뒤 `match_complete`에 authoritative
  result와 settlement를 함께 보낸다. 클라이언트가 점수·순위·정산 값을 제출하는
  경로는 없다.
- WebSocket 연결 종료는 registry의 게임을 삭제하지 않는다. 같은 서버 프로세스에서
  재접속하면 현재 human turn 또는 캐시된 완료 결과를 다시 받는다. 서버 재시작,
  worker 간 공유, 메모리 회수, 영속적인 대국 이력과 재시작 이후 정산 idempotency는
  후속 설계 범위다.

## 스파이크 전 초기 가정(확정 완료)

첫 통합 전에 다음을 후보로 두었으며, 위 0.4.8 스파이크에서 실제 동작을 확정했다.

```text
RiichiEnv game_mode = 4p-red-east
Tenhou 계열 기본 규칙
```

문서 예시보다 설치된 라이브러리의 실제 API를 계속 우선한다.

## 아직 결정하지 않음

- 게임 오버 후 진행 초기화/재시작 정책
- 최종 전체 완료 후 엔딩 처리
- CG 실제 이미지/연출
- 캐릭터 최종 이름/설정/프로필 이미지
- 프로필/CPU 이미지의 허용 형식, 용량 제한과 저장 key 정책
- Mortal 사용 여부
