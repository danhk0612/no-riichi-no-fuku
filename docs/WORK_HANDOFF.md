# Work Handoff

## Current status

GitHub bootstrap and the RiichiEnv 0.4.8 spike are complete. Backend settings, initial
database models, Alembic migrations, superadmin bootstrap, CPU seed path, authentication and
member name profile APIs are implemented. Superadmin authorization and member/CPU/dialogue
management foundation APIs are also implemented. The RiichiEnv adapter, MahjongAgent boundary
and process-local authoritative game session foundation are implemented. A minimal React Mahjong
table renders HumanTurn data, legal actions and match results without image assets. The production
Tier 0 CPU uses shanten, approximate ukeire, a weak riichi-genbutsu bias and seeded weighted
selection. **Tier 1 CPU is now implemented** with value awareness (dora, yaku potential), improved
defense (danger levels), basic push/fold decisions, and enhanced riichi/call evaluation. **Tier 2 
CPU is now implemented** with suji/wall defense, placement-aware strategies, expected value 
computation, and endgame ranking conditions. Completed authoritative sessions settle exactly one 
fourth-place outcome: player HP or the mapped user's CPU progress. Authenticated members can list 
active, incomplete CPU choices; validated groups of three create a fresh authoritative session 
through a stage-aware agent factory that maps stage 0 to Tier0Agent, stage 1 to Tier1Agent, and 
stage 2 to Tier2Agent. Authenticated REST creation now persists the session seed, CPU/player 
snapshots and accepted human action log while caching the live RiichiEnv object in an owner-scoped 
registry. The game WebSocket authenticates with its first message, accepts only a legal-action 
index with the current action version, and commits every accepted human action. A cache miss or 
server restart reconstructs an active match by deterministic replay; completed results and 
settlement remain durable and idempotent. Game dialogue events are extracted from authoritative
session observations, matched with active CPU dialogues, and delivered with HumanTurn messages.
The six initial adult CPU characters now have personality-specific Korean seed pools for all
supported in-match events plus game start/rank/result candidates. CPU fourth-place completion sends
the newly reached stage dialogue and its stage 1/2/3 CG metadata when uploaded, while an empty
result slot remains visible without requiring an image file.
The React client now provides minimal member registration/login, selectable CPU cards, REST game
creation, first-message-authenticated WebSocket play, authoritative result settlement display,
speech bubbles during play, and the return-to-selection loop. Access tokens remain in tab memory
only. All three CPU tiers (0/1/2) are now available and functional in the selection UI. After a 
page refresh the member must log in again; the client then discovers the server's active session 
and reconnects to the persisted turn. New members start with current/max HP 3 and stage 0 progress 
for every seeded CPU. Superadmin result CG upload/replace/delete and member-unlocked result display
are implemented against the runtime media volume without Git image assets. Docker/Compose runtime
validation is intentionally deferred to the final integration stage.

Repository:

```text
danhk0612/no-riichi-no-fuku
```

## Verified before handoff

- GitHub root/docs/backend/frontend files are present on `main`.
- Python `backend/app/main.py` syntax check passed.
- `backend/app/seeds/cpu_characters.json` parses correctly.
- Initial CPU seed count: 6.
- All initial CPU seed entries explicitly mark the character as adult.
- A local metadata-only `pip install . --no-deps --no-build-isolation` check for the backend project succeeded.
- RiichiEnv 0.4.8 current PyPI release and Apache-2.0 license were rechecked on 2026-08-29.
- Mortal code license was rechecked as AGPL-3.0-or-later.

## Verified in the first Work

- Backend dependency installation and direct `/api/health` response.
- Frontend production build.
- RiichiEnv 0.4.8 four-seat East-only match completion.
- Actual initialization, observation/action structure, red fives, termination and rank behavior
  are recorded in `docs/DECISIONS.md`.
- Initial migration upgrade/downgrade and schema drift check on SQLite.
- Idempotent superadmin/CPU seed bootstrap tests.
- Member registration, login, authenticated profile read/name update and password change tests.
- Superadmin initial-password flag and verified password-change transition tests.
- Initial/max HP 3 migration, including SQLite round-trip and PostgreSQL offline SQL generation.
- Superadmin access denial before the initial password change and member access denial.
- Member listing/activation, CPU create/update and dialogue CRUD API tests.
- New CPU creation adds stage 0 progress for every existing member.
- RiichiEnv adapter rejects missing or illegal seat actions before calling the engine.
- A fixed-seed authoritative session completed in 300 steps with all three injected CPU agents.
- Human turns expose seat 0 observation/legal actions while other seats' hands remain hidden.
- Frontend TypeScript production build with HumanTurn/action types and tile-id conversion.
- Responsive four-seat table, scores, discards, hand actions, dora and result components.
- Tier 0 prioritizes wins/riichi, filters discards by shanten and approximate ukeire, and only
  calls when shanten improves.
- A fixed-seed authoritative match with three production Tier 0 agents completed in 381 steps;
  final scores `(18600, 37000, 26600, 17800)`, ranks `(3, 1, 2, 4)`.
- Completed server sessions decrement only player HP when seat 0 is fourth, or increment only the
  mapped user's CPU defeat stage when a CPU seat is fourth.
- HP 0, completed stage 3 and duplicate process-local settlement boundaries are rejected.
- Member CPU choices exclude inactive and stage 3 characters; selections require three distinct
  available IDs and positive HP.
- Stage-aware session creation maps stage 0 to Tier 0. Stage 1/2 fail explicitly until their agents
  exist instead of silently falling back to Tier 0.
- A settled stage 2 to 3 CPU disappears from the next selection query.
- REST session creation returns a server-generated session ID and four seat descriptors, and rejects
  a second unfinished session for the same member.
- WebSocket first-message JWT authentication rejects unauthenticated and non-owner access without
  putting the token in the URL.
- Invalid action indexes do not advance the authoritative turn; disconnect/reconnect returns the
  same current state.
- RiichiEnv 0.4.8 `Meld` values inside `Observation.to_dict()["melds"]` are converted to explicit
  JSON fields at the transport boundary.
- A fixed-seed Tier 0 match completed through only WebSocket action messages, committed the matching
  HP/CPU settlement, and returned the same completion from a fresh registry on reconnect.
- Active sessions persist their seed, CPU/player snapshots and accepted human action indexes; a
  fresh registry replayed a saved action to exactly the same next `human_turn`.
- A separate RiichiEnv 0.4.8 replay spike reproduced all 99 human turns across 399 engine steps and
  the same final scores/ranks with production Tier 0 agents.
- Stale action versions are rejected and the latest authoritative turn is resent. The active-session
  REST endpoint lets a re-login recover a match without persisting JWT/session IDs in the browser.
- Completed scores, ranks and settlement are stored with `status = completed`, preventing restart
  recovery from applying HP/CPU progress twice.
- The new migration passed SQLite upgrade/schema/downgrade and PostgreSQL offline SQL generation,
  including the one-active-session-per-member partial unique index.
- Backend test suite: 35 tests passed. Frontend TypeScript/Vite production build passed.
- Vite development proxy was verified end to end for registration, login, CPU loading, session
  creation and the game WebSocket. A production-agent match completed after 90 human action-index
  messages and returned the matching CPU stage settlement.
- The frontend disables action controls until the server returns the next turn, and reloads CPU
  choices after a completed match instead of calculating progress locally.
- The nginx `/api/` location is configured to forward WebSocket upgrades, but its actual container
  runtime remains part of the deferred final Docker validation.

## Verified in Tier 2 CPU implementation

- Tier2Agent class implements suji and wall defense calculations.
- Suji safety: tiles 3 apart from opponent discards are considered safer.
- Wall safety: tile kinds with 3+ visible copies are considered safer.
- Game state analysis computes current scores, ranks, remaining tiles, and final round status.
- Placement-aware strategy: 4th place prioritizes offense, 1st place in final round prioritizes defense.
- Expected value computation weighs efficiency, value, danger, and placement conditions.
- Factory maps defeat_stage 2 to Tier2Agent; all three tiers (0/1/2) are now implemented.
- Fixed-seed match with four Tier2Agent instances completes in under 2000 steps.
- Backend test suite: 42 core tests passed (9 Tier2Agent tests, all Tier0/Tier1/session/result tests).
- Frontend TypeScript production build passed.

## Deferred to final integration

- `docker compose config/build/up`
- Web root and nginx-proxied `/api/health`
- PostgreSQL container health
- `postgres_data` and `media_data` persistence

These remain unverified until the final Docker integration task succeeds.

## Dialogue system integration (2026-09-12)

Game dialogue event contract and speech-bubble integration is complete. The server detects RiichiEnv
events (riichi, chi, pon, kan, ron, tsumo) from `Observation.to_dict()["events"]`, selects matching
active CPU dialogues from the database, and sends `dialogue_event` WebSocket messages to the client.
The React frontend displays speech bubbles above each CPU seat with the most recent dialogue for that
seat. Speech bubbles have CSS fade-in animation and seat-specific tail positioning.

`AuthoritativeGameSession` accumulates events from each step and exposes them via `pending_events()`.
The WebSocket sends dialogue events before the turn state. The client maintains up to 10 recent
dialogues and maps the latest per seat to the active table display. Dialogue selection uses a seeded
`DialogueSelector` that randomly chooses from active `cpu_dialogues` rows matching the CPU character
and event key.

Event mapping covers riichi, chi, pon, kan (all types), ron, and tsumo. Events like game_start,
final_east, match_first/last, large_win, and defeat_stage_N are not yet implemented and remain as
future candidates. The server now applies a session-scoped policy before selecting from the
admin-managed dialogue pool: ron/tsumo 100%, riichi 90%, kan 75%, pon 45%, and chi 35%.
Call events use per-CPU and per-event action-version cooldowns. Each state delivery emits at most
one line, prioritized as win, riichi, kan, pon, then chi. Recovery replay discards historical
events so reconnecting does not burst old dialogue.

Backend tests cover dialogue selection, active/inactive filtering, event extraction, and multi-event
handling. Frontend types include `DialogueEvent` and `dialogue_event` in `GameServerMessage`. The
implementation added:
- `backend/app/services/dialogue_service.py`
- `backend/tests/test_dialogue_service.py`
- `PendingGameEvents` dataclass and `pending_events()` method in `AuthoritativeGameSession`
- `dialogue_event` WebSocket message handling in `game.py`
- `DialogueEvent` type, `recentDialogues` state, and speech-bubble UI in the frontend

After the server-side policy change, the complete backend suite passes with 74 tests and the
frontend TypeScript/Vite production build passes. Docker/Compose remains explicitly unverified
until the deferred final integration task.

## Tier 1 CPU implementation (2026-09-12)

Tier 1 CPU agent is now implemented in `backend/app/mahjong/tier1.py`. The `create_production_cpu_agent`
factory in `game_setup.py` maps `defeat_stage == 1` to `Tier1Agent` and `defeat_stage == 2` continues
to raise `CpuTierUnavailableError`.

### Tier 1 features beyond Tier 0

- **Hand value evaluation**: Counts dora, estimates yaku potential (tanyao, pinfu, chinitsu, etc.)
- **Improved defense**: Danger level estimation based on tile types and opponent riichi; prioritizes
  safe tiles when folding
- **Push/fold decisions**: Considers shanten, score, opponent riichi count, and dora holdings to
  decide when to fold
- **Riichi decisions**: Evaluates tenpai state, opponent riichi count, dora, and score to decide
  whether to declare riichi
- **Enhanced call evaluation**: Prefers chi/pon with dora; pon is considered even when shanten does
  not improve

### Verification

- Fixed-seed match (seed 7, CPU seeds 601/602/603) completes with Tier 1 agents
- Fixed-seed comparison (seed 15) shows Tier 1 produces different final scores from Tier 0
- Stage 1 selection successfully creates `Tier1Agent` and completes matches
- Stage 2 continues to explicitly fail with `CpuTierUnavailableError`

Backend test suite: 49 tests passed. Frontend TypeScript/Vite production build passed.

## Result CG asset integration (2026-09-12)

- 결과 CG는 JPEG/PNG/WebP만 허용하고 signature로 판별하며, 파일당 최대 크기는 5 MiB이다.
- storage key는 서버가
  `/cpu/{cpu_id}/result/stage-{1|2|3}/{uuid}.{jpg|png|webp}`로 생성한다.
- 최초 비밀번호를 변경한 활성 superadmin만 CPU/단계별 asset 목록 조회 및
  multipart 업로드·교체·삭제를 할 수 있다.
- 파일은 `MEDIA_ROOT` 아래에 저장하고 기존 `cpu_result_assets` row에는 storage key,
  MIME type, CPU와 단계 연결 metadata만 저장한다. 교체 시 새 key를 사용하고 이전
  파일을 삭제하며, 삭제 시 런타임 파일을 제거하고 DB row는 빈 슬롯으로 유지한다.
- 회원 metadata/file API는 해당 회원의 `defeat_stage`가 asset 단계 이상인지 서버에서
  확인한다. 잠긴 단계와 존재하지 않는 asset은 같은 404 경계로 응답한다.
- CPU가 4위인 대국 종료 payload는 방금 해금된 단계의 활성 `result_asset` metadata를
  포함한다. 플레이어가 4위이거나 등록 asset이 없으면 `null`이다.
- React 종료 화면은 JWT를 포함한 별도 fetch로 바이너리를 받은 뒤 object URL로
  표시하고 다음 대국/로그아웃/unmount 시 URL을 해제한다.
- 테스트에는 실제 CG가 아닌 synthetic signature 및 metadata fixture만 사용했다.
- 백엔드 전체 suite 76개 통과, 프런트엔드 production build 통과.
- Docker/Compose, PostgreSQL 컨테이너, 실제 persistent volume 재시작 보존은 이
  작업 범위에서 검증하지 않았다.

## Stage dialogue and empty CG slot integration (2026-09-12)

- 사용자 표시용 패배 단계는 `0 정상·일상복`, `1 자켓/겉옷 벗음`,
  `2 속옷만 착용`, `3 알몸·최종 완료`로 확정했다. 모든 캐릭터는 기존 규칙대로
  명시적인 성인이다.
- `backend/app/seeds/cpu_dialogues.json`에 6개 seed CPU별로 12개 event key,
  event당 2문장씩 총 144개 한국어 대사를 추가했다. 포함 key는 `game_start`,
  `riichi`, `chi`, `pon`, `kan`, `ron`, `tsumo`, `match_first`, `match_last`,
  `defeat_stage_1`, `defeat_stage_2`, `defeat_stage_3`이다.
- bootstrap은 CPU/event별 기존 관리자 대사를 덮어쓰지 않는 create-only 방식으로
  기본 대사를 넣는다. 기존의 in-match 확률/cooldown 값은 변경하지 않았다.
- CPU가 4위가 되어 stage가 증가하면 WebSocket `match_complete`가
  `result_dialogue`와 `result_asset`을 함께 반환한다. 완료 세션 재접속에서도 같은
  stage 문장이 선택되도록 session ID와 event key를 기반으로 선택한다.
- `cpu_result_assets.storage_key`를 nullable로 바꾸는 Alembic revision 0004를 추가했다.
  bootstrap과 관리자 CPU 생성은 각 CPU에 stage 1/2/3 빈 metadata 슬롯을 만든다.
  업로드는 해당 슬롯을 채우고 삭제는 슬롯을 `NULL`/inactive 상태로 되돌린다.
- CPU 선택 카드는 Stage 1/2를 더 이상 미구현으로 막지 않는다. 카드와 결과 화면에
  네 단계의 복장 문구를 표시하고, 프로필 key가 없을 때 문자 avatar를 표시한다.
  결과 CG가 등록되지 않은 경우에도 해당 단계의 빈 CG 슬롯과 안내 문구를 표시한다.
- Git에는 CG, 더미 CG, 프로필 이미지 바이너리를 추가하지 않았다.
- 실제 운영 CG 업로드와 프로필 이미지 업로드 정책은 여전히 별도 운영/후속 작업이다.
- 이 변경 후 `python3 -m unittest discover -s tests -v` 전체 66개 테스트가 통과했다.
- `npm run build`로 TypeScript/Vite production build가 통과했다.
- 새 Alembic revision을 포함한 SQLite `upgrade head`와 `downgrade base` 왕복이
  통과했다. Docker/Compose와 PostgreSQL runtime 검증은 수행하지 않았다.

## Next entry point

Docker/Compose full runtime validation is the next entry point. Verify `docker compose
config/build/up`, nginx-proxied web/API/WebSocket behavior, PostgreSQL health, and
`postgres_data`/`media_data` persistence across service recreation. Include an actual runtime
result CG upload/serve/persistence check, but do not commit that file.

Deferred dialogue keys such as game_start/final_east and profile image upload remain separate
follow-up work and must not be folded into Docker validation.

For guidance, read:

1. `AGENTS.md`
2. `docs/WORK_INSTRUCTIONS.md`
3. `docs/WORK_START.md`
4. Tournament simulation results in `docs/DECISIONS.md`

Profile/CPU image upload and CG management remain undecided. Do not implement media upload paths
or add CG binary files to the repository.

## Automated Difficulty Tuning Simulation (2026-09-12)

A fixed-seed tournament simulation harness was implemented to measure relative performance among
Tier 0/1/2 agents.

### Implementation

- `backend/app/simulation/tournament.py`: Tournament execution and metric collection
- `backend/scripts/run_simulation.py`: Standalone simulation script with JSON/markdown output
- `backend/tests/test_tournament_simulation.py`: 7 simulation tests covering single matches,
  homogeneous/heterogeneous combinations, statistics computation, and small integration

### Methodology

- 16 fixed seeds: 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61
- 9 seat combinations per seed (homogeneous + balanced mixed tiers)
- 144 total matches (16 seeds × 9 combinations)
- Each tier played 192 matches

### Results

| Tier | Matches | Avg Rank | Avg Score | 1st Rate | 4th Rate | Rank Distribution |
|------|---------|----------|-----------|----------|----------|-------------------|
| Tier0 | 192 | 2.510 | 25162.5 | 27.1% | 26.6% | 1위:52, 2위:41, 3위:48, 4위:51 |
| Tier1 | 192 | 2.531 | 24988.0 | 23.4% | 24.5% | 1위:45, 2위:47, 3위:53, 4위:47 |
| Tier2 | 192 | 2.458 | 24844.3 | 24.5% | 24.0% | 1위:47, 2위:56, 3위:43, 4위:46 |

### Analysis

All three tiers are well-balanced with average ranks within 0.073 of each other (near-perfect
balance at 2.5). Tier2 shows slight superiority (2.458) but not dominating performance. First-place
rates range from 23.4% to 27.1%, and fourth-place rates from 24.0% to 26.6%. The "no intentional
worst-move easy mode" principle is preserved. No tuning adjustments were needed.

Backend test suite: 65 tests passed. Frontend TypeScript/Vite production build passed.

## CPU Personality Parameter Integration (2026-09-12)

CPU 캐릭터별 성향 파라미터(aggression, defense, call_preference, riichi_preference,
hand_value_preference, speed_preference)가 Tier 0/1/2 Agent 의사결정에 연결되었다.

### Implementation

- `app/services/game_setup.py`: `CpuChoice` dataclass에 6개 personality 파라미터 추가
- `list_selectable_cpus()`가 DB의 personality 필드를 포함하도록 수정
- `create_production_cpu_agent()`가 선택된 CPU의 성향값을 각 Tier agent 생성자에 전달
- `app/mahjong/tier0.py`: riichi 선언 판단, call 수용 threshold, defense/speed 가중치
- `app/mahjong/tier1.py`: push/fold 판단 threshold, value/speed 밸런스, call 확률 조정
- `app/mahjong/tier2.py`: EV 계산 가중치, placement 판단 urgency, defense threshold
- `tests/test_personality_integration.py`: 파라미터 저장 및 영향 검증 7개 테스트

### Integration Points

**Tier0Agent:**
- `_should_declare_riichi()`: riichi_preference/defense 비율로 선언 확률 조정
- `_choose_discard()`: defense로 안전패 가중치, speed_preference로 유효패 가중치
- `_improving_calls()`: call_preference < 0.8이면 거부, < 1.0이면 확률적 거부

**Tier1Agent:**
- `_should_riichi()`: riichi_preference/defense 비율, aggression 반영한 점수 threshold
- `_choose_discard()`: speed/value/defense 가중치 분리
- `_should_fold()`: aggression/defense 비율로 fold threshold 조정
- `_improving_calls()`: call_preference/hand_value_preference로 call 확률 조정

**Tier2Agent:**
- `_should_riichi()`: riichi_preference/defense/aggression으로 종반 리치 판단
- `_compute_expected_value()`: 6개 파라미터로 EV 가중치 분리
- `_should_fold()`: aggression/defense/hand_value_preference로 fold 판단
- `_improving_calls()`: call_preference/hand_value_preference/aggression으로 call 판단

### Personality Separation

Stage/Tier 매핑은 불변(stage 0→Tier0, 1→Tier1, 2→Tier2)이며, 동일 Tier 내에서도
캐릭터별 성향 차이가 의사결정에 반영된다. seed data의 6개 CPU:
- tachibana-rin: balanced (모든 파라미터 1.0)
- kurokawa-mio: defensive (defense 1.25, aggression 0.8)
- amamiya-yuna: aggressive (aggression 1.25, defense 0.8, riichi 1.1)
- shirogane-rei: menzen-riichi (call 0.7, riichi 1.3, value 1.1)
- kanzaki-aya: fast-call (call 1.3, speed 1.3, riichi 0.8)
- saionji-kaede: high-value (value 1.35, call 0.75, speed 0.8)

Backend test suite: 64 tests passed. Frontend TypeScript/Vite production build passed.

## Next entry points

1. **Docker/Compose full runtime validation**: Verify `docker compose config/build/up`,
   nginx-proxied web/API/WebSocket behavior, PostgreSQL health, and `postgres_data`/`media_data`
   persistence. Include a runtime-only result CG upload/serve/recreation check.
2. **Deferred dialogue event wiring**: Seed pools for `game_start` and `match_first/match_last`
   exist, but only the defeat-stage result event is wired outside the six RiichiEnv action events.
   Wire the remaining candidates only when their exact display timing is decided; do not rewrite
   the completed cooldown/probability policy.
3. **Profile images**: Decide member/CPU profile image format, size, and storage rules before
   implementing uploads.
4. **Real media content**: Upload final CGs through the admin API at runtime. Do not add them to Git.

Read:

1. `AGENTS.md`
2. `docs/WORK_INSTRUCTIONS.md`
3. `docs/WORK_START.md`
