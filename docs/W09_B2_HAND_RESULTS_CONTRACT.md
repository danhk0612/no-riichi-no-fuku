# W09-B2 — 국 결과 사실 저장·복구 계약

기준 main `67c4335`(PR #102 병합), 검토 제품 source `315409c`.
이 문서는 후속 구현 계약이다. 새 collector/DB/queue는 아직 구현하지 않았다.
권장 구현 환경은 저성능 Work이며 W09-B2만 독립 PR로 수행한다.

## 1. 범위와 후속 분리

B1의 검증된 화료 점수와 엔진 원본 국 경계를 누적하여 **국 결과 사실**을 행동 기록과 원자 저장한다.
대국 시작 당시 좌석/캐릭터/이름/stage, 국 시작 정보, 전원 화료/유국·지급·점수 구간을 고정한다.
사람 차례 사이에 종료된 국이 여러 개여도 전부 보존하고 재시작으로 중복 저장하지 않는다.

| 단계 | 이번 처리 |
|---|---|
| B1 | 기존 점수 수집·원본 대조 재사용 |
| B2 | 내부 국 결과 누적, 새 로컬 대국의 사실 영속, replay 대조·복구 |
| 후속 표시 계약 | 사용자 확인 cursor/ack, 결과 전달·화면/다음 행동 gate, 전원 무작위 표시순서 |
| 문구/CG | 캐릭터 고정 문구 관리·이전, content/prompt snapshot, 이미지 선택/생성/연출은 별도 |

B2에는 결과 GET/WS 메시지·확인 버튼·ack endpoint·새 대국 gate·frontend 변경을 추가하지 않는다.
표시 기능이 없는 상태에서 저장된 사실을 미확인 결과로 간주하여 기존 대국을 막지 않는다.
결과 사실은 표시 snapshot이 아니다. 이후 현재 문구/프롬프트로 과거 결과를 보충하거나,
B2 동안 만든 대국을 자동으로 새 표시 정책에 편입하지 않는다. 표시 대상의 도입 경계는 후속 계약에서 확정한다.
기존 공통 선언/화료 음성·최종 결산/엔딩과 pending event ordinal은 유지한다.

## 2. 확인한 제품 경계

- `RiichiEnvAdapter.last_hand_wins`는 가장 최근 step만 보유한다. 다음 step 전에 소비해야 한다.
- `AuthoritativeGameSession._step` 뒤 `_advance_until_human_turn`이 여러 번 호출될 수 있다.
  기존 `pending_events()`는 좌석 observation을 합친 음향/대사 소비 경계로서 국 identity가 아니다.
- 0.4.8의 실제 공개 로그 API는 `env.mjai_log`다. `round_end_scores`는 설치본의 공개 속성이 아니다.
  pyi 선언만 보고 존재하지 않는 API를 사용하거나 엔진 바이너리를 패치하지 않는다.
- `GameRegistry.create`는 game.start 뒤 record를 만든다. 시작 중 수집된 결과도 create transaction이 소유한다.
- `submit_action`은 engine 진행 후 human indices/action_version을 갱신·flush하고 API가 commit한다.
  최종 action과 `settle`의 별도 transaction, completed 복구의 저장 결과 읽기를 유지한다.

## 3. 수집과 identity

새 내부 collector는 adapter의 reset/start부터 누적 MJAI를 읽고 다음을 지킨다.

1. 원본 log offset을 단조 cursor로 읽는다. 이전 prefix가 바뀌거나 log가 짧아지면 검증 실패다.
   같은 내용의 event라도 서로 다른 offset이면 별개다. observation 배열의 index/content dedup은 사용하지 않는다.
2. `start_kyoku` offset을 국 identity로 사용한다. bakaze/kyoku/honba 값은 identity가 아니다.
   start의 필요한 필드를 whitelist로 복사하고 hidden tehais/전체 log는 결과 payload에 넣지 않는다.
3. `hora` 전원의 offset/actor/target/실지급/ura와 같은 step의 B1 HandWin을 정확히 대응한다.
   actor 집합과 개수·원본 offset·event 필드 불일치/점수 누락은 저장 실패이며 일반 band fallback이 없다.
4. `ryukyoku`도 원본 순서대로 보존하고 `end_kyoku`에서 한 국을 닫는다. 화료와 유국 정보가 함께
   있으면 둘 다 보존한다. 트리플론은 기존 규칙의 유국이며 승자 결과를 만들지 않는다.
   엔진이 ryukyoku로 기록하는 `nagashimangan`도 원래 reason/deltas 그대로 보존한다.
5. 같은 suffix의 `end_kyoku`→다음 `start_kyoku`를 처리해도 종료국의 start 정보를 유지한다.
   `end_game`은 직전 종료국의 terminal 표시를 확정한다. 동일 step의 suffix 전체를 처리해 terminal을 반영한 뒤 불변 batch를 확정한다.
   국이 닫히기 전에 결과를 emit하지 않는다.
6. 한 human action 동안 모인 종료국들을 source offset 순서로 별도 누적한다. session의 새
   `pending_hand_results()`는 이 사실 batch만 소비하며 기존 `pending_events()`를 호출/재정의하지 않는다.
   수집/serialize는 CPU agent를 다시 호출하거나 RNG를 소비하지 않는다.

adapter가 직접 DB를 쓰지 않는다. session은 엔진 사실만 수집하고 registry가 저장된 참가자 snapshot을 붙인다.
로그 API가 전체 목록을 반환하므로, 새 suffix 처리와 prefix 확인의 비용을 고정 seed701 Tier0/2에서
수집 전후 각1회(총4대국) 비교·기록한다. steps/actions/scores/ranks/log는 같아야 한다.
추가 seed 탐색·난이도 튜닝·새 엔진 API/패치는 이번 범위가 아니다.
합성 collector 입력은 유효한 start_game/start_kyoku 경계부터 만든다. B1 fixture의 reset 로그에
별도 start_kyoku를 붙인 설정을 그대로 전체 대국 로그로 취급하지 않는다.

## 4. additive schema와 payload v1

migration은 구현 시작 시 최신 head를 확인해 다음 revision을 사용한다. 현재 head0011 기준 제안은
`20261019_0012_hand_results`다. 기존 저장을 backfill하거나 rules_snapshot/CPU policy version을 바꾸지 않는다.

| 모델 | 필드/제약 |
|---|---|
| GameSessionRecord | `hand_results_version: nullable Integer`, NULL 또는1. server default 없음 |
| GameHandResult | `session_id:String(36)`와 `hand_start_log_offset:Integer` 복합 PK |
| 소유 | session_id FK→game_sessions.id, ondelete CASCADE로 기존 parent 삭제 계약 준수 |
| 순서 | `sequence:Integer >=1`, UNIQUE(session_id,sequence) |
| 경계 | `hand_end_log_offset > hand_start_log_offset >=0` |
| 행동 | `source_action_version:Integer >=0` |
| 내용 | `payload:JSON NOT NULL`, `created_at` 기존 UTC timestamp 관례 |

reset은 parent를 삭제하지 않고 cancel/generation 갱신하므로 사실 row도 보존한다.
사용자 자료의 DELETE/청소/파일 이동을 추가하지 않는다. downgrade 검사는 소유 임시 DB에서만 한다.

payload는 다음 whitelist를 사용한다. 신규 scalar/리스트는 JSON 값으로 복사하며 공유 mutable 참조를 두지 않는다.

```text
{
  version: 1,
  generation: string,
  start: {bakaze, kyoku, honba, oya, kyotaku, scores:[int,int,int,int]},
  participants: [{seat, is_human, name, cpu_id:null|int, stage_at_hand:null|0..3}, ...4명],
  outcome: "win"|"draw"|"mixed",
  winners: [{hora_log_offset, actor, target, win_kind:"ron"|"tsumo",
             deltas:[int,int,int,int], ura_markers:[string],
             score:{han,fu,yakuman,yaku:[int],ron_agari,tsumo_agari_oya,tsumo_agari_ko,
                    pao_payer:null|int,band:1|2|3}}],
  draws: [{log_offset, reason, deltas:[int,int,int,int]}],
  engine_scores_after_step: [int,int,int,int],
  terminal: bool
}
```

- identity는 (generation,session_id,start offset), 승자 identity는 추가 hora offset이다.
  컬럼의 sequence/end/source_action_version도 결과 metadata이며 payload와 함께 불변이다.
- 참가자 이름은 record.players, CPU/stage는 record.cpu_choices의 기존 seat 순서1/2/3에서 얻는다.
  human seat0의 cpu_id/stage는 null이다. 현재 CpuCharacter/UserCpuProgress/설정/후속 stage_after를 읽지 않는다.
- score는 B1의 실제 확정값만 복사한다. source는 payload version1의 pinned 0.4.8/B1 경로다.
- engine_scores_after_step은 원본 step 반환 뒤 scores()의 관측값이다. 이 값으로 순수 화료 본체 점수를
  새로 계산하지 않는다. band는 B1만 담당한다.
- draws는 최소 reason/deltas 원본만 복사한다. 없는 값을 추정하지 않으며 허용 reason을 새 규칙으로 재해석하지 않는다.
- content revision·문구·prompt/media 참조·표시 RNG/순서·ack 상태는 v1 사실 payload에 만들지 않는다.
  이 값들의 소유/고정 시점은 후속 표시 계약의 책임이다.

## 5. 새 대국/저장 원자성

새 Windows 로컬 대국만 hand_results_version=1로 생성한다. 기존 local/웹 record는 NULL을 유지한다.
웹 신규 생성·테스트의 기존 factory는 기본 수집 off다. `create_game_session_from_choices`와
session에 내부 keyword를 전달하되, 해당 값은 규칙/난이도/agent 선택에 영향을 주지 않는다.

- create: choices/players를 확정하고 수집 on으로 start한다. parent record를 먼저 flush하여 기존
  active unique 오류를 처리한 뒤 시작 batch row를 같은 transaction에 저장한다. source_action_version은0.
  새 결과 insert 실패를 ActiveGameExistsError로 잘못 바꾸지 않는다. commit 전 사실 payload를 외부 응답에 공개하지 않는다.
- action: 기존 writer intent/record lock/version 검사→engine 진행→새 batch 구성→human indices와
  결과 rows를 같은 transaction에 flush→API commit 순서다. source_action_version은 갱신 후 action_version이다.
  engine 내부 step 수를 human action_version으로 대체하지 않으며 sequence는 원본 종료국 순서다.
- 기존 identity가 있으면 sequence/end/action_version/payload가 전부 같은지 확인한다.
  같으면 중복 emit 없이 유지하며, 다르면 실패한다. merge/upsert로 과거 payload를 덮지 않는다.
- 수집 검증 실패는 B1의 controlled failure 경로에 연결한다. 필요 최소
  HandResultCaptureError(HandScoreCaptureError 하위)로 기존 hand_score_failed 응답을 재사용한다.
  DB flush/commit 실패는 기존 persistence_failed/rollback 경계를 유지한다.
  registry의 B1 catch 범위에 새 batch 구성/검증도 포함한다. 현재 API의 score 실패 handler는
  registry에서 game/cache를 폐기한 것으로 전제하므로 새 helper를 catch 밖에서 호출한 채 두지 않는다.
- 원본이 진행한 뒤 검증/serialize/flush/commit이 실패하면 game/cache를 폐기한다. create 예외도
  record/row/cache가 남지 않아야 한다. caller transaction 안에서 임의 commit/별도 DB 연결로 결과를 저장하지 않는다.
- GET/WS 전송/음악/이미지 load가 사실 row를 새로 쓰거나 소비하지 않는다.

## 6. 복구/legacy/정산

| 저장 형태 | 복구 |
|---|---|
| marker NULL | 기존 경로 유지. 과거 사실/문구/표시 queue를 생성하지 않음 |
| v1 active | 같은 seed/actions를 수집 on으로 replay, DB rows와 전체 순서/경계/점수/참가자 사실 대조 |
| v1 completed | 기존 완료 결과와 DB rows 읽기. 엔진 replay·재정산 없음 |
| cancelled/옛 generation | 기존 거절 경계 유지. 보존 사실을 새 대국에 섞지 않음 |
| 알 수 없는 marker/payload version | controlled failure. legacy fallback/추정 복구 없음 |

active replay의 이미 commit된 batch는 대조 후 비운다. 복구 pending 음향도 기존처럼 비운다.
대조 시 source_action_version은 replay의 human action index를 사용한다. factory의 start 직후 batch를0으로
대조·drain하고, 각 human index 제출 뒤 생긴 batch를1,2,...로 각각 대조·drain한다. 전체 replay가
끝난 뒤 모든 batch에 마지막 action_version을 붙이지 않는다. 복구 GET에서 새 row를 생성하거나
누락 row를 backfill하지 않는다. 불일치는 cache 등록 전에 실패한다.
completed v1은 row sequence가1부터 연속이고 마지막이 terminal인지 검사하며 재대국하지 않는다.
completed 전 마지막 action에 terminal row가 이미 commit되어야 한다. 정산 transaction은 row를 다시 쓰지 않는다.
정산 실패·crash 후 기존 action을 복구해 한 번만 정산하며 row 수/payload가 변하지 않아야 한다.
표시 완료 상태/ack/ending 진행은 B2에서 바꾸지 않는다. 후속 표시는 모든 미확인 국→마지막 국→
최종 결산의 stage_after CG/패배 문구→기존 ending→자유 대국 순서를 별도 계약으로 구현한다.

## 7. 파일 범위·수용 검사

변경 허용: mahjong adapter/session/새 최소 collector, game_setup keyword, game_registry와 새 저장 service,
GameSessionRecord/새 model·exports, 다음 additive migration, 기존 game API의 필요한 실패 경계 및 관련 tests.
정확한 package DB 검증을 위해 `.github/workflows/w05-windows-shell.yml`과 소유 test helper만 최소 보강 가능하다.
frontend·게임 규칙/CPU·오디오·공유 prompt/캐릭터 관리·생성/파일 청소는 제외한다.

필수 검사:

1. 원본 start→전원hora/ryukyoku→end_kyoku, 같은 step의 다음 국, 본장 반복, offset identity,
   멀티 step/복수 pending, start 자동 진행, 승자 없는 유국·트리플론·nagashimangan 원본 reason 보존.
2. B1 점수대응/친자/론쯔모/본장·공탁·구간·특수 화료 회귀, source trace/RNG·policy1/2/3 보존.
3. 새 v1 create/action 원자 저장, row 중복·변조/누락, 결과 flush/commit 실패 후 같은 턴 복구,
   source_action_version0/증분, 원본 진행 뒤 serialize 오류·cache 폐기.
4. 파일 SQLite 종료/재시작 replay대조·동일 batch·새 suffix1회 저장, 완료 복구에 엔진 미호출,
   마지막 action 후 정산 전 crash/정산 commit 실패·재접속에도 row/단계 증가1회.
5. marker NULL active/completed/web, progress/완료 보충/omake, reset 전후 보존/세대 격리,
   캐릭터 이름/stage 설정 변경이 저장 사실을 덮지 않음. 전체 raw log/hidden 손패 미저장.
6. 전체 backend/대사 회귀·기존 build/browser, 최종 source SHA Windows W04/W05·artifact source/hash.
   packaged renderer 종료 뒤 소유 explicit-test-data/game.db를 read-only로 검사해 새 migration/marker/
   실제 완료 대국의 사실 rows·연속 sequence·terminal/참가자 stage를 확인하고 JSON 근거를 artifact에 둔다.
   새 production 진단 endpoint를 만들지 않는다. 기존 package 재시작/종료 검사는 유지한다.

실제 수집/DB/UI가 구현됐다는 결과를 이 문서만으로 보고하지 않는다. 제품 구현 후
CURRENT_STATE/TASKS/ARCHITECTURE·PR에 구현/미검증·정확한 source/Windows 근거를 구분한다.
