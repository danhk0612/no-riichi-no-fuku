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
- 서버 세션은 사람을 좌석 0, 선택한 CPU 3명을 좌석 1~3에 배치한다. 실행 중인
  RiichiEnv env와 전체 좌석 Observation/Action 객체는 서버 메모리 cache에 두되,
  복구에 필요한 seed·CPU 선택 snapshot·사람 행동 log는 DB에 저장한다.
- 사람이 행동할 차례에는 좌석 0의 `Observation.to_dict()`와 그 시점의 합법 행동
  목록만 `HumanTurn`으로 제공한다. 다른 좌석의 손패가 빈 목록인 0.4.8 관측 경계를
  그대로 유지한다.
- 실제 0.4.8의 `Observation.to_dict()["melds"]`는 JSON dict가 아니라 pybind `Meld`
  객체를 포함한다. WebSocket 경계에서는 이를 `meld_type`, `tiles`, `called_tile`,
  `from_who`, `opened`만 가진 JSON object로 명시적으로 변환한다.
- 사람 행동은 서버가 제공했던 합법 행동 목록의 index로 내부 선택하고, adapter가
  현재 필요한 모든 좌석의 행동과 각 행동의 합법성을 다시 검사한 뒤 `env.step()`을
  호출한다. 공개 WebSocket도 이 `legal_action_index`만 행동 요청으로 받는다.
- registry cache가 없는 경우 DB의 seed·CPU 선택 snapshot·사람 행동 log로
  authoritative session을 결정론적으로 다시 만든다. 영속화와 동시 입력 경계는 아래
  `게임 상태 실시간 영속화` 결정을 따른다.
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
- `AuthoritativeGameSession.result_settled`는 현재 실행 객체의 중복 적용을 막고,
  `game_sessions`의 완료 상태와 저장된 정산 결과는 프로세스 재시작 뒤 중복 정산을
  막는다.

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
- registry는 실행 중 RiichiEnv 세션을 서버 프로세스 메모리에 cache하고, 소유 회원,
  좌석 표시 정보, 복구 log와 완료 정산은 DB에 보관한다. DB partial unique index로 한
  회원당 active 세션을 하나만 허용한다. 정산 commit 뒤에는 새 세션을 만들 수 있고
  이전 완료 세션은 프로세스 재시작 뒤에도 조회할 수 있다.
- WebSocket 경로는 `/api/game/sessions/{session_id}/ws`이다. 브라우저 WebSocket에서
  임의 Authorization header를 전제로 하지 않고 JWT가 URL/query log에 남지 않도록,
  첫 JSON 메시지 `{ "type": "authenticate", "access_token": "..." }`로 인증한다.
  활성 일반 회원이 아니면 4401, 소유하지 않은 세션은 존재 여부를 숨긴 채 4404로
  종료한다.
- 인증 직후와 합법 행동 처리 후 서버는 `action_version`을 포함한 `human_turn`을
  전송한다. 클라이언트 행동은 직전 version과 합법 행동 index를 함께 보내야 한다.
  범위를 벗어난 index나 오래된 version은 게임을 진행하지 않고 `error`와 최신 turn을
  반환한다.
- 대국 완료 시 서버는 `AuthoritativeGameSession.result()`로 `scores`/`ranks`를 만들고
  짧은 별도 DB session에서 즉시 정산·commit한 뒤 `match_complete`에 authoritative
  result와 settlement를 함께 보낸다. 클라이언트가 점수·순위·정산 값을 제출하는
  경로는 없다.
- WebSocket 연결 종료는 대국을 삭제하지 않는다. cache hit이면 현재 객체를 사용하고,
  cache miss나 서버 재시작이면 DB에서 active 대국을 재생하거나 완료 결과를 읽는다.

## 게임 상태 실시간 영속화

- RiichiEnv 0.4.8에는 애플리케이션이 채택할 안정적인 snapshot/restore API가 확인되지
  않아 엔진 객체를 직렬화하지 않는다. `game_sessions`에 match seed, 좌석/CPU 선택
  snapshot, 승인된 사람 행동 index 배열, 상태와 완료 결과/정산을 저장한다.
- 서버가 사람 행동 하나를 정상 처리할 때마다 해당 index를 짧은 DB transaction으로
  즉시 commit한다. crash가 엔진 step 뒤 DB commit 전에 발생하면 그 미커밋 행동만
  사라지고, 재접속한 클라이언트는 저장된 최신 turn에서 다시 선택한다.
- cache miss 시 동일 seed와 CPU별 파생 seed로 session을 다시 만들고 저장된 사람 행동을
  순서대로 재생한다. 2026-08-31 실제 production Tier 0 검증에서 seed 5와 CPU seed
  51/52/53으로 99개 사람 행동(전체 399 step)을 두 session에 재생했으며 매 HumanTurn과
  최종 점수 `(20700, 16900, 35100, 27300)`, 순위 `(3, 4, 1, 2)`가 동일했다.
- 완료 시 점수·순위·정산과 `status = completed`를 HP/CPU 진행 변경과 같은 transaction에
  commit한다. 따라서 완료 결과 재조회나 프로세스 재시작이 정산을 반복하지 않는다.
- `GET /api/game/sessions/active`는 로그인한 회원의 active session ID와 좌석 정보를
  반환한다. access token 자체는 계속 브라우저 메모리에만 두지만, 새로고침 후 다시
  로그인하면 active 대국을 발견해 WebSocket으로 복구한다.
- 이 방식은 Redis나 별도 인프라를 추가하지 않는다. row lock과 `action_version`으로
  중복/오래된 입력을 거부하지만, 여러 worker가 같은 active 세션 객체를 공동 소유하는
  구조는 아니며 각 worker가 필요할 때 DB log를 재생한다. 엔진/agent 정책 변경을 섞은
  active 대국 배포 호환성은 후속 배포 정책에서 관리해야 한다.

## 프론트엔드 게임 흐름 연결

- 최소 회원 화면은 가입 후 즉시 로그인하거나 기존 회원으로 로그인한다. JWT access
  token은 React 메모리에만 두며 local/session storage나 URL에 저장하지 않는다.
  새로고침 후 로그인 유지와 refresh token은 현재 범위가 아니다. 다시 로그인하면
  서버의 active session을 조회해 진행 중 대국에 재접속한다.
- 로그인 후 `GET /api/game/cpus` 결과에서 정확히 3명을 선택하고 요청 순서대로 좌석
  1/2/3에 배치한다. stage 1/2 CPU는 서버 목록에는 남지만 해당 agent가 아직 없으므로
  UI에서도 `Tier N 미구현`으로 표시하고 선택을 막는다. Tier 0으로 대체하지 않는다.
- `POST /api/game/sessions` 응답의 session ID와 좌석 표시 정보를 그대로 사용하며,
  같은 origin의 `/api/game/sessions/{session_id}/ws`에 연결한 뒤 첫 메시지로 JWT를
  보낸다. Vite 개발 proxy와 nginx 모두 `/api`의 WebSocket upgrade를 전달한다.
- `human_turn`을 기존 마작 테이블 상태로 반영하고, 사용자가 선택한 합법 행동 index만
  보낸다. 다음 `human_turn` 또는 `error`가 올 때까지 행동 UI를 잠가 같은 turn의
  연속 클릭이 다음 turn 행동으로 잘못 처리되지 않게 한다.
- `match_complete`의 점수·순위·정산만 결과 화면에 사용한다. 다음 대국 버튼은 CPU
  목록을 다시 조회해 stage 3 제외 및 갱신된 stage를 반영한다. 클라이언트는 HP나
  CPU 진행도를 직접 계산하거나 제출하지 않는다.
- 개발 환경에서 Vite `/api` proxy를 경유해 가입, 로그인, CPU 조회, 세션 생성,
  WebSocket 인증과 90회의 사람 행동 요청으로 실제 동풍전 완주 및 CPU stage 정산을
  확인했다. nginx/Docker 경유 검증은 최종 Docker 통합 단계에 남긴다.

## 스파이크 전 초기 가정(확정 완료)

첫 통합 전에 다음을 후보로 두었으며, 위 0.4.8 스파이크에서 실제 동작을 확정했다.

```text
RiichiEnv game_mode = 4p-red-east
Tenhou 계열 기본 규칙
```

문서 예시보다 설치된 라이브러리의 실제 API를 계속 우선한다.

## 대사 시스템 구현 (2026-09-12)

- 게임 중 발생하는 이벤트(riichi, chi, pon, kan, ron, tsumo 등)를 감지하여 CPU 말풍선으로 표시한다.
- RiichiEnv 0.4.8의 `Observation.to_dict()["events"]` 필드에서 이벤트를 추출한다.
- **검증 완료 (2026-09-12)**: RiichiEnv 0.4.8 이벤트는 **JSON 문자열 리스트**로 반환되며, `json.loads()`로 파싱해야 한다.
- 검증된 이벤트 타입:
  - `reach`: 리치 선언 → `riichi` 대사 키
  - `reach_accepted`: 리치 수리 (대사 키 없음)
  - `chi`: 치 → `chi`
  - `pon`: 퐁 → `pon`
  - `ankan`, `kakan`, `daiminkan`: 깡 (통합) → `kan`
  - `hora`: 화료, `target` 필드로 구분
    - `target`이 있고 `actor`와 다름 → `ron`
    - 그 외 → `tsumo`
- `AuthoritativeGameSession`은 각 step에서 발생한 이벤트를 누적하고, `pending_events()` 메서드로 소비한다.
- `DialogueSelector`는 DB의 `cpu_dialogues` 테이블에서 해당 CPU와 이벤트 키에 맞는 활성 대사 중 하나를 랜덤으로 선택한다.
- WebSocket은 게임 상태 전송 전에 대사 이벤트를 `dialogue_event` 메시지로 먼저 전송한다.
- 프론트엔드는 `recentDialogues` 상태로 최근 10개 대사를 관리하고, 각 좌석별 최신 대사를 말풍선으로 표시한다.
- 말풍선은 CSS 애니메이션과 좌석별 꼬리 위치를 가진다.
- 대사 노출 여부는 서버의 게임 세션별 `DialogueEventPolicy`가 결정하며 클라이언트는
  정책을 계산하지 않는다.
- cooldown은 wall-clock 시간이 아니라 authoritative `action_version` 단위로 계산한다.
  따라서 테스트와 고정 seed replay에서 동일한 turn 경계를 사용한다.
- 기본 이벤트 확률은 `ron`/`tsumo` 100%, `riichi` 90%, `kan` 75%, `pon` 45%,
  `chi` 35%이다. 활성 `cpu_dialogues` 후보가 없으면 노출 기록을 남기지 않는다.
- 일반 호출 대사는 CPU별 2 action-version cooldown을 적용한다. 이벤트별 cooldown은
  `kan` 2, `pon`/`chi` 3 action-version이며, 화료와 리치는 희소한 중요 이벤트이므로
  CPU/event cooldown을 적용하지 않는다.
- 같은 상태 전송에 여러 이벤트가 몰리면 `ron`/`tsumo`, `riichi`, `kan`, `pon`,
  `chi` 순으로 우선하며 대사는 최대 1개만 전송한다. 이 rapid-event 제한 뒤에도
  기존 `dialogue_event` WebSocket 필드와 관리자 관리 `cpu_dialogues` pool을 그대로 쓴다.
- 프로세스 재시작 복구 시 DB action log replay에서 생긴 과거 이벤트는 폐기한다.
  이미 지나간 대사를 재접속 시 한꺼번에 보내지 않으며 정책 상태 자체는 DB에 저장하지 않는다.
- 게임 시작, 최종 순위, 만관 이상 화료, defeat_stage 결과 등은 별도 이벤트로 처리 가능하지만 초기 구현에서는 게임 중 행동 이벤트만 처리한다.

## Tier 2 CPU 정책

- production `Tier2Agent`는 Tier 1 기반 위에 고급 공수 판단과 상황 인식을 추가한다.
- 스지(suji) 방어: 상대가 버린 패와 3간 차이 나는 패가 대기패일 가능성이 낮다고 판단한다.
  예를 들어 1만이 버려진 경우 4만은 상대적으로 안전하다고 평가한다.
- 벽(wall) 방어: 보이는 패가 3장 이상이면 나머지 1장은 매우 안전하다고 평가한다.
- 게임 상황 인식: 현재 점수, 순위, 남은 패 수, 동4국 여부를 분석한다.
- 순위별 전략 조정: 4위일 때는 공격 우선, 1위이고 동4국이며 30,000점 이상이면 수비 우선,
  동4국 4위인 경우 3위와의 점수 차이에 따른 긴급도 반영.
- 기대값 종합 평가: 패효율, 타점, 도라, 위험도, 안전도를 모두 고려한 종합 점수로 행동 선택.
- 치/퐁 판단: 샹텐 개선이 있고, 4위이거나 상대 리치가 없을 때만 선택.
- RiichiEnv seed 11, CPU seed 201/202/203/204으로 production Tier 2 네 좌석 동풍전은
  330 step에 정상 종료했고, 최종 점수는 `[11600, 32500, 38500, 17400]`, 순위는 `[4, 2, 1, 3]`이다.
- factory는 `defeat_stage == 2`를 `Tier2Agent`로 매핑하며, stage 0/1/2 모두 구현되어
  선택 가능하다. stage 3은 여전히 최종 완료로 선택 불가이다.

## CPU Personality Parameter Integration

CPU 캐릭터 성향 파라미터(aggression, defense, call_preference, riichi_preference, 
hand_value_preference, speed_preference)를 Tier 0/1/2 Agent의 의사결정에 연결했다.

### 통합 범위

- `CpuChoice` dataclass에 6개 personality 파라미터 추가
- `Tier0Agent`, `Tier1Agent`, `Tier2Agent` 생성자에 파라미터 전달
- 각 Tier의 핵심 의사결정 지점에 파라미터 가중치 적용:
  - Tier0: riichi 선언, call 수용, defense 가중치
  - Tier1: push/fold 판단, value/speed 밸런스, call 평가
  - Tier2: EV 계산, placement 판단, defense 임계값

### 파라미터 영향

각 파라미터는 0.5~1.5 범위를 권장하며 1.0이 기본값이다. 예:
- `riichi_preference=1.3`: 리치 선언을 더 적극적으로 선택
- `defense=1.2`: 수비 가중치 증가, fold 판단 빠름
- `call_preference=0.7`: 울기를 덜 선호, 멘젠 성향
- `aggression=1.3`, `defense=0.8`: 공격적 push 성향

동일 Tier라도 캐릭터별 파라미터 차이로 플레이 느낌이 달라진다. Stage/Tier 매핑은 
기존과 동일하게 유지(stage 0→Tier0, 1→Tier1, 2→Tier2)한다.

### 검증

- `test_personality_integration.py`로 파라미터 저장 및 의사결정 영향 검증
- 기존 64개 backend test 전체 통과
- Frontend production build 정상

## 아직 결정하지 않음

- 게임 오버 후 진행 초기화/재시작 정책
- 최종 전체 완료 후 엔딩 처리
- CG 실제 이미지/연출
- 캐릭터 최종 이름/설정/프로필 이미지
- 프로필/CPU 이미지의 허용 형식, 용량 제한과 저장 key 정책
- Mortal 사용 여부

## 자동화된 난이도 튜닝 시뮬레이션

2026-09-12에 고정 시드 토너먼트 시뮬레이션 하네스를 구현하고 Tier 0/1/2 에이전트 간 상대 성능을 측정했다.

### 시뮬레이션 방법론

- 16개 고정 시드: 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61
- 9개 좌석 조합 (동종 4명 + 혼합 조합)
- 총 144 매치 (16 시드 × 9 조합)
- 각 Tier는 192회 출전

### 측정 결과

| Tier | 평균 순위 | 평균 점수 | 1위 비율 | 4위 비율 | 순위 분포 |
|------|----------|-----------|---------|---------|-----------|
| Tier0 | 2.510 | 25162.5 | 27.1% | 26.6% | 1위:52, 2위:41, 3위:48, 4위:51 |
| Tier1 | 2.531 | 24988.0 | 23.4% | 24.5% | 1위:45, 2위:47, 3위:53, 4위:47 |
| Tier2 | 2.458 | 24844.3 | 24.5% | 24.0% | 1위:47, 2위:56, 3위:43, 4위:46 |

### 분석 및 결론

1. **균형 잡힌 난이도**: 세 Tier의 평균 순위 차이가 0.073 이내로 매우 작다. 완벽한 균형(2.5)에 가깝다.

2. **Tier2 우위 존재하지만 미미함**: Tier2가 평균 순위 2.458로 가장 우수하지만, Tier0/1과의 차이가 작아 압도적이지 않다.

3. **1위/4위 비율 균형**: 모든 Tier가 23~27% 범위의 1위 비율과 24~27% 범위의 4위 비율을 보인다. 어느 Tier도 일방적으로 강하거나 약하지 않다.

4. **튜닝 조정 불필요**: 현재 가중치와 평가 함수가 "no intentional worst-move easy mode" 원칙을 유지하면서도 단계별 성능 차이를 적절히 표현하고 있다. 추가 튜닝 없이 현재 구현을 유지한다.

5. **재현 가능성**: 시뮬레이션은 고정 시드와 에이전트별 시드 파생(match_seed * 10 + seat)으로 완전히 재현 가능하다.

### 시뮬레이션 도구

- `backend/app/simulation/tournament.py`: 토너먼트 실행 및 메트릭 수집
- `backend/scripts/run_simulation.py`: 독립 실행 스크립트
- `backend/tests/test_tournament_simulation.py`: 시뮬레이션 기능 테스트

후속 난이도 조정이 필요하면 동일한 하네스와 시드로 재측정할 수 있다.

## Tier 1 CPU (2026-09-12)

`Tier1Agent`를 `backend/app/mahjong/tier1.py`에 production 구현으로 추가했다.
`create_production_cpu_agent` 팩토리는 `defeat_stage == 1`일 때 `Tier1Agent`를 생성한다.

### Tier 1 기능

Tier 0 대비 다음 기능이 추가되었다:

- **타점 평가**: 도라 개수, 역 가능성 추정(탄요/일기통관/멘젠/호니소 등)
- **향상된 수비**: 위험도 평가(상대 리치 시 종류별 위험 점수), 현물 우선
- **Push/fold 판단**: 샹텐, 자기 점수, 상대 리치 수, 도라 보유에 따라 안전패 우선 여부 결정
- **리치 판단**: 텐파이 상태, 상대 리치 수, 도라, 점수 상황을 종합해 리치 여부 결정
- **향상된 울기 평가**: 샹텐 개선 외에 도라가 포함된 치/퐁 우선, 퐁은 샹텐이 같아도 고려

### 검증 결과

- 고정 seed 7, CPU seed 601/602/603으로 동풍전 완주 확인
- 고정 seed 15에서 Tier0 3명과 Tier1 3명이 다른 최종 점수를 기록
- stage 1 선택이 정상적으로 `Tier1Agent`를 생성하고 게임을 진행함
- stage 2는 여전히 `CpuTierUnavailableError`를 발생시킴

백엔드 테스트 49개, 프론트엔드 빌드 모두 통과.
- 대사 이벤트의 확률 제한 또는 cooldown 정책
