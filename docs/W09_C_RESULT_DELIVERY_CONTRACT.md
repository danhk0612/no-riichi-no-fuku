# 국 결과 표시·확인 계약 — W09-C1/C2 인계

기준 main `c197029`(PR #106 병합), B2 수용 main `3341d4e`/검토 source `3bb3307`.
이 문서는 **설계**다. 아래 테이블·DTO·endpoint·gate·UI는 아직 제품에 없다.
B2 사실 계약과 최신 REQUIREMENTS를 유지하며 과거의 통합 W09-B 지시문보다 본 분해를 우선한다.
긴 transaction/복구·구현 지시문을 한 곳에서 참조하기 위해 독립 계약으로 둔다.

## 1. 소스 대조와 설계 범위

| 실제 코드 | 현재 사실 / 후속 접점 |
|---|---|
| `backend/app/db/models/game_session_record.py`, `game_hand_result.py` | hand_results_version=1 및 불변 사실 rows. 표시 버전/확인 상태 없음 |
| `backend/app/services/hand_results.py`, `game_registry.py` create/submit_action/_restore | 시작 batch=action0, action과 facts 원자 저장. replay 전체 대조, completed는 엔진 미호출 |
| `game_registry.py` settle/_settle_local/publish_completed | 마지막 action과 별도 정산 transaction. 정산에서 stage 및 기존 presentation v2/ending 고정, commit 뒤 공개 |
| `backend/app/api/game.py` send_registered_game_state | pending_events를 소비하고 human_turn 또는 match_complete 전송. 완료 시 별도 정산/commit. 표시 수신은 저장되지 않음 |
| `backend/app/api/local_play.py` _state_payload | active 또는 최근 completed를 반환. 미확인 completed 전용 탐색 없음 |
| `backend/app/services/local_play.py` | ending ack는 phase/event/generation 검사, reset은 active 취소·새 generation·자료 보존 |
| `frontend/src/main.tsx` restoreLocalPlay/connectGame/nextGame | active 다음 ending_pending 우선, omake는 선택 화면. match_complete에서 socket 종료; 다음 대국 선택은 서버 확인 cursor 없음 |
| `frontend/src/api.ts`, `game/types.ts` | 기존 play/ending DTO와 action version. 새 표시 상태와 구별 필요 |

따라서 UI에 결과 배열만 붙이면 completed/ending 복구 때 누락되고 다른 socket이 행동을 보낼 수 있다.
표시의 소유는 **서버 DB**이며 socket/React state/localStorage는 표시 사본일 뿐이다.
B2 facts·CPU·엔진·정산·음향 source ordinal은 수정하지 않는다. 한 action 내부 자동 CPU 진행을
국마다 중단하지 않는다. 이미 확정된 사람 차례 사이 종료국을 모두 쌓고 다음 사람 행동을 gate한다.

## 2. 의존성 분해와 도입 경계

| 단계 | 독립 구현 / 선행 / 제외 |
|---|---|
| W09-C1 전달·확인 | B2 수용 + 본 계약 검토/병합 후 별도 승인. 사실 기반 결과 카드·고정 무작위 순서·cursor/ack·gate·복구. 새 고정 문구/P/N/CG는 미연결임을 명시 |
| W09-M 고정 문구 관리 | 캐릭터별 win/defeat_stage_1..3 및 기존 match_first 보존. 공유 문장풀 없음. Q-LEGACY 이전 정책 결정 전 자동 이전 금지; 기존 여러 행 중 임의 한 행 선택 금지 |
| W09-S 공유 상황 연결 | D05-c 편집 방향 확정 후 event/band/Level과 명시 후보·기본값 연결. W08-D 복장/포즈 관리 재사용. 상황 미지정을 모든 event 허용으로 해석하지 않음 |
| W09-C2 콘텐츠 snapshot | M/S·변수 검증·content revision과 아래 이미지 정책 확정 후 별도 계약/승인. 당시에 선택한 문자열/후보/P/N/미디어 불변화. C1 기존 대국에 보충 금지 |
| W10/W11 생성 | Q-IMAGE/Q-FRAME/D07~09 응답 및 실제 ComfyUI 기술 확인 후 별도. C1 전달/확인은 이 선행을 기다리지 않음 |
| W11-U CG 연출 | C2 입력/media 계약과 W11 결과 연결 뒤. C1 카드 전환과 같은 서버 순서/cursor 사용. 생성 실패로 확인을 막지 않음 |

C1에서 `delivery_version=1`은 **전달 snapshot**, 완성된 콘텐츠 snapshot을 뜻하지 않는다.
`content_mode=unbound`를 session 생성 때 저장한다. C1은 국 사실·당시 참가자와 기존 정산
presentation v2만 전달하며 새 win 고정 텍스트/화료 CG는 아직 출력하지 않는다. 기존 정산 텍스트/
asset는 저장된 v2를 그대로 보여 주고 재선택하지 않는다. 이것을 최신 고정 문구/단계별 CG 구현
완료로 보고하지 않는다. 미응답을 '문구 없음/후보 없음'으로 확정한 것이 아니다.
후속 C2는 별도 version과 content_mode를 사용하고 새 대국 생성 시에만 채택한다.

migration은 최신 Alembic head0012 다음 additive revision을 사용한다. **server default/backfill 없음**.
새 로컬 대국 create에서만 `result_delivery_version=1`을 명시하고 `hand_results_version=1`을 요구한다.
웹 신규/기존 NULL legacy 및 B2 기간 marker1 대국의 delivery_version은 NULL 그대로 둔다.
업그레이드 당시 active를 포함해 opt-in하지 않는다. GET/재접속/정산 때 과거 facts를 표시로 변환하지 않는다.
NULL 대국의 기존 결산/ending/선택 복구는 유지하며 새 ack/gate를 걸지 않는다.
같은 generation에서도 NULL 기존 대국을 마친 뒤 새 대국부터 C1 채택 가능하다.
알 수 없는 표시 버전/필수 row 누락은 controlled failure이지 NULL fallback이 아니다.

## 3. additive DB 및 DTO 계약

이름은 아래로 고정하되 revision 번호는 구현 시 최신 head에서 정한다. 실제 DDL은 C1 작업이다.

| 관계 | 필드와 제약 |
|---|---|
| GameSessionRecord 추가 | `result_delivery_version: nullable Integer`(NULL 또는1), server default 없음 |
| GameResultDelivery | `session_id` PK/FK game_sessions.id; `generation:String(36)`, `version=1`, `content_mode=unbound`; `acked_ordinal:Integer>=0` 초기0; `revision:Integer>=0` 초기0; `terminal_ordinal:nullable Integer` |
| GameResultDeliveryEntry | `(session_id,ordinal)` 복합 PK, ordinal>=1; `event_id:String(36)` UNIQUE; `kind=hand|settlement`; `hand_start_log_offset:nullable Integer`, `display_index:nullable Integer`; `payload:JSON NOT NULL`; created_at 기존 UTC 관례 |
| hand unique | `(session_id,hand_start_log_offset,display_index)` unique; start offset/display index 둘 다 nonnull. 대응 facts가 같은 session에 존재함을 writer와 읽기 검증에서 보장 |
| settlement unique | session별 settlement 한 건(부분 unique index). hand 식별 필드는 null, ordinal=terminal_ordinal |

FK 삭제 계약은 기존 session cascade와 같으나 reset은 삭제하지 않는다. generation은 parent와
현재 play state에 대조한다. acked_ordinal은 실제 존재하는 연속 prefix의 끝이며 entry 총수 이하,
terminal_ordinal은 settlement entry가 commit될 때만 설정한다. terminal은 ack 완료 여부가 아니다.
entry payload/event_id/순서는 insert 후 불변. ack는 cursor/revision만 변경하며 facts/entry를 삭제하지 않는다.
전송했다고 cursor를 갱신하지 않는다. idempotent append는 identity·순서·payload 완전 일치만 허용한다.
누락/중복 ordinal·잘못된 permutation·다른 generation·unknown payload version은 오류로 격리한다.

읽기 검증은 남아 있는 entry의 유효성뿐 아니라 원본 facts **전체에 대한 완전한 대응**도 확인한다.
각 fact_sequence/start/end/source_action_version과 원본 payload가 일치하고, 각 국의 entry 수는
`max(1, 화료자 수)`, display_index는0부터 연속이며 각 winner가 저장 permutation대로 정확히 한 번
나와야 한다. 모든 국을 fact_sequence 순으로 붙인 뒤에만 settlement가 올 수 있다.
마지막 entry 삭제처럼 ordinal에 내부 빈칸이 없어도 누락은 오류다. ack된 과거 prefix도 검증하며,
completed는 저장 parent scores/ranks/presentation과 일치하는 settlement 한 건과 terminal_ordinal을
요구한다. active의 terminal 사실은 아직 settlement가 없어도 유효하지만, 그 외 국 entry는 이미
원자 저장돼 있어야 한다. 누락을 GET/ack/replay에서 backfill하거나 cursor를 이동해 숨기지 않는다.

hand payload v1 whitelist:

```text
{version:1, kind:"hand", fact_sequence, hand_start_log_offset,
 hand_end_log_offset, source_action_version,
 fact_snapshot: <B2 payload의 깊은 복사, 원본 배열 순서 유지>,
 winner_display_order:[hora_log_offset,...],
 display_index:0..N-1, displayed_hora_log_offset:null|int,
 content_mode:"unbound"}
```

fact_snapshot은 당시 facts의 전달 사본이며 읽기 검증 때 원본과 대조한다. 실제 raw log/숨은 손패를
추가하지 않는다. 승자가 N명이면 N개의 hand entry, 없으면 1개(display_index0, hora=null, order=[]).
각 승자 카드에서도 전체 화료자·유국·정산 사실을 유지한다. mixed는 원본 draw 정보도 함께 표시하며
draw를 새 승자로 만들지 않는다. 각 CPU의 band/stage/name은 자신의 B2 winner/participant로 얻는다.
human slot은 기본 배경이다. 유국/nagashimangan/triple ron은 facts대로 보여 주고 화료 CG를 만들지 않는다.

복수 화료 순열은 source hora offset 전원의 정확한 순열이다. 서버의 별도 표시 RNG 인스턴스로
한 번 뽑아 같은 국 entry 모두에 저장한다. CPU agent/session RNG·DialogueSelector·음향 RNG를
호출하지 않는다. crash/commit 실패 후에는 공개된 순서가 없으므로 재시도 선택 가능하지만,
commit된 row는 replay/재기동/재렌더로 재추첨하지 않는다. 표시 seed를 게임 seed에 끼워 넣지 않는다.

settlement payload v1은 저장할 최종 scores/ranks/settlement 및 기존 presentation v2, 당시
참가자 이름/seat의 깊은 복사다. 마지막 값은 `GameSessionRecord.players`에서 가져오며 카드의
최종 순위 이름에 사용한다. 현재 CPU 이름/명단을 조회하지 않는다.
최종 국의 stage_at_hand와 stage_after(기존 defeat_stage)를 다른 필드로 유지한다. C1은 stage를
추가 계산하지 않는다. 정산 결과에 stage_changed=true이면 변경 후 CG, 완료 CPU/omake의 stage3
불변이면 새 단계 CG 없음이라는 기존 경계를 유지한다. 최종4위 패배 문구/음성은 유지한다.
C2의 CG는 기존 `cg` kind이고 별도 defeat_cg kind를 만들지 않는다. C1은 기존 v2 asset 참조의
파일 수명 보장을 확대하지 않는다. 새 immutable media UUID/digest 보장은 C2 계약의 책임이다.

외부 envelope v1(REST와 WS 공통):

```text
{version:1, generation, session_id, delivery_revision,
 acked_ordinal, head:null|{ordinal,event_id,kind,payload},
 terminal_ordinal:null|int,
 route:"result"|"human_turn"|"settlement_wait"|"ending"|"selection",
 action_version:null|int}
```

head는 acked+1만 반환한다. renderer가 전체 배열에서 임의 다음 결과를 고르지 않는다.
route는 현재 DB에서 계산하고 future settlement/ending 정보를 미리 수신해도 화면으로 승격하지 않는다.
DTO에 active/recent 식별자만으로 미확인을 추측하는 필드를 만들지 않는다.

## 4. transaction·표시 순서·gate

1. create writer: 선택/이름·stage 확정→기존 engine start→parent flush→B2 시작 facts→delivery state와
   시작 hand entries를 **같은 transaction**으로 저장→commit 후 응답. 시작 자동 결과도 누락하지 않는다.
2. action writer: 기존 local writer intent와 record lock/generation/version 검사→**미확인 head 검사**→
   engine 진행→action indices/facts/새 hand entries를 같은 transaction으로 flush→API commit 후 공개.
   오류면 rollback·진행한 game/cache 폐기. delivery만 따로 commit하여 action과 엇갈리게 하지 않는다.
3. terminal action은 terminal facts/마지막 hand entries까지만 저장한다. 기존 별도 settle transaction이
   stage/점수/presentation/ending과 settlement entry/terminal_ordinal을 함께 저장한다. ack를 기다려
   정산을 지연시키지 않으며 ack가 정산을 호출하지 않는다. settle 재시도는 기존 exactly-once 경계를 유지한다.
4. 표시: 원본 fact_sequence 오름차순의 모든 미확인 국(국 안은 저장 permutation)→마지막 국→
   settlement 카드(stage_after CG/패배 문구)→기존 ending UUID/payload→ending ack 후 omake 선택.
   엔딩 없는 progress/omake는 settlement 확인 후 선택이다. 화료 stage는 정산 후 값으로 덮지 않는다.
5. 서버 action gate: C1 session의 head가 있으면 `result_pending`, engine/CPU/RNG 미호출.
   source action 안에 이미 진행한 다음 국을 rewind하거나 각 국마다 CPU를 멈추지 않는다.
6. 서버 create gate: 현재 generation의 delivery session 중 미확인 entry 또는 아직 settlement가 없는
   terminal 저장 대국이 있으면 `result_pending`. active unique/기존 ending_pending 제한도 유지한다.
   ack 완료된 과거 completed는 새 대국을 막지 않는다. UI만 버튼을 숨기는 것으로 대체하지 않는다.
7. ending ack gate: 해당 generation의 C1 결과가 남으면 `result_pending`. 기존 ending UUID/멱등성은
   유지한다. 화면 복구/ending 음악 load를 ending ack로 해석하지 않는다. reset은 이 gate와 독립이다.

한 generation에 unresolved C1 대국은 writer 직렬화 아래 최대1개다. DB 조회로 소유 대국을 찾고
복수면 임의 최근 값을 고르지 말고 `result_delivery_invalid`로 거절한다. 완료 pending도 조회한다.
조회는 session의 표시 marker를 기준으로 delivery row 유무도 검증한다. delivery table의 inner
join만으로 marker1인데 state가 없는 손상 대국을 누락하여 gate를 해제하지 않는다.
마지막 hand 확인과 settlement commit이 경쟁하면 빈 head만 보고 선택으로 가지 않고
`terminal_ordinal=null`인 terminal 대국을 settlement_wait로 유지한다.

## 5. REST/WS·확인·복구 계약

아래 endpoint는 local runtime에서만 등록, 기존 member/local capability·write intent를 재사용한다.
웹 API/기존 message 동작은 NULL session에 유지한다. 다른 사용자의 session은 404다.

| 인터페이스 | 계약 |
|---|---|
| GET `/api/local/play` additive `result_resume` | null 또는 `{session_id,delivery_version,route,delivery_revision}`. generation 내 active/미확인 completed를 ending/omake보다 우선 찾음. 조회만 하며 정산/backfill/ack 없음 |
| GET `/api/local/play/sessions/{id}/results?generation=...` | envelope v1 조회. 사실/표시 검증, 무쓰기. NULL delivery면 409 result_delivery_unsupported, legacy 복구 사용 |
| POST `/api/local/play/sessions/{id}/results/ack` | body `{generation,event_id,ordinal,expected_delivery_revision}`. 현재 head를 정확히 한 칸 확인하고 cursor/revision 원자 증가. commit 후 최신 envelope 반환 |
| WS additive `result_delivery` | 동일 envelope. 새 결과/복구 시 저장 head 전달. 전송 실패·전송 횟수는 cursor에 영향 없음 |
| WS 기존 human_turn/match_complete | C1에서는 내부 상태 사본으로 보관하되 result_delivery route가 먼저. pending 중 행동 금지. match_complete만으로 socket 종료/최종 화면 전환 금지 |

ack 검사 순서: capability/소유→writer 취득→현재 generation/parent 취소 검사→버전/entry 검증→
이미 ack된 **동일 event_id+ordinal**이면 멱등 성공(과거 expected_revision 허용, cursor 그대로)→
그 외 head identity 및 expected_revision 일치 검사→한 칸 증가/commit. 이미 ack된 ordinal에 다른
ID는 성공 처리하지 않는다. 미래 ordinal·다른 event·stale revision은409 `result_ack_conflict`와
현재 조회를 안내한다. 요청 형식 오류는422, 세대 변경은409 `play_generation_stale`, DB 실패는
WS의 기존 persistence_failed 규약과 REST 503 persistence_failed로 구분한다. 변조/누락 snapshot은503 `result_delivery_invalid`로
gate를 풀지 않고 저장 자료를 보존한다. 누락 미디어는 이 오류가 아니며 확인을 막지 않는다.

renderer는 현재 head의 **다음/확인 버튼**으로 한 entry씩 ack한다. 복수 화료에서는 성공한 ack의
다음 head를 짧은 opacity 전환으로 보여 주며 전원 슬롯을 거쳐야 국을 벗어난다. 첫 구현은 CSS
150ms 전환, reduced-motion이면 즉시 전환으로 제한한다. 자동 타이머/이미지 onload/음악 ended/
unmount가 ack하지 않는다. 서버는 사용자의 실제 시선을 증명하지 않으며 head를 건너뛰는 요청만 거절한다.
각 프레임 cursor를 영속하므로 재접속은 다음 미확인 승자로 복귀한다. timer/애니메이션 진행률은
저장하지 않는다. 실패한 이미지·기본 배경/유국이어도 버튼은 사용 가능하다.

ack 응답 유실은 같은 identity 재시도 또는 GET으로 조정한다. 성공을 추정해 로컬 cursor를 앞당기지
않는다. GET/WS의 같은 generation/session에서 revision이 낮은 envelope는 폐기한다. revision이
같은데 불변 head/entry가 다르면 오류로 재조회한다. ack는 action_version을 증가시키지 않는다.
서버 append 시에도 delivery revision을 증가시켜 같은 revision의 head/cursor가 달라지지 않게 한다.
정산 entry append도 revision 변경이다. route/action_version은 현재 play phase/게임 상태에도
의존하므로 delivery revision만으로 비교하지 않는다. human_turn은 기존 action_version 검사를
함께 사용하고 ending ack/선택 전환은 기존 local request token과 play 재조회로 조정한다.

두 socket은 DB writer/record lock 아래 같은 cursor를 공유한다. 같은 head 동시 ack는 한 번만 증가,
다른 socket의 오래된 action은 서버 pending/version 검사를 통과하지 못한다. socket broadcast 성공을
정확성 조건으로 삼지 않는다. ack 성공 envelope를 받은 화면은 필요하면 기존 socket 재연결/조회로
저장 상태를 갱신한다. 두 socket에서 다음 카드가 보일 수 있지만 전환이 음향 event를 다시 만들지 않는다.

복구 순서:

- bootstrap/play 조회에서 result_resume 우선. active라도 먼저 pending head, completed라도 pending이면
  선택/ending 앞에 결과 표시. C1 결과가 없을 때만 기존 phase/NULL 복구로 간다.
- terminal action 후 settle 전 crash는 기존 socket resume이 done active를 복구하여 별도 settle을
  재시도한다. GET/ack에서 엔진을 만들거나 정산하지 않는다. settle 실패 중에는 저장 hand 확인은
  가능하되 마지막 확인 뒤 settlement_wait에서 기존 복구 재시도, 새 대국/ending은 gate한다.
- completed는 엔진 replay/재정산 없이 facts/entry와 기존 presentation을 읽는다. ending_pending이어도
  settlement 확인 전 ending 재생하지 않는다. ending ack 응답 유실은 기존 omake 멱등 복구다.
- reset은 기존 writer transaction으로 새 generation/취소를 commit하고 소켓을 닫는다. rows/cursor/
  snapshot/media는 보존하되 새 generation의 resume/gate 조회에서 제외한다. 옛 ack/WS/load/전환
  callback은 generation+session+event_id+renderer request token으로 격리한다.
- ack 실패·reset 실패는 서버 재조회로 조정한다. reset과 ack 경쟁은 writer 순서에 따라 하나의
  generation에서만 효과를 낸다. 과거 응답이 새 화면을 바꾸거나 새 세대 gate를 해제할 수 없다.

오디오는 기존 pending_events/action_version/source ordinal/팩 선택 규약 그대로다. C1은 표시 지연과
무관하게 기존 commit 후 전송을 유지한다. 표시/ack/replay/전환에서 ron/tsumo/win/결산 음성이나
SFX를 재발행·재정렬하지 않는다. 따라서 C1은 시각 카드와 음성의 새 동기화 기능을 제공하지 않는다.
음향의 표시 시점 동기화가 필요하면 별도 범위다. ending 음악만 기존처럼 ending 화면 진입 뒤다.

## 6. 후속 콘텐츠 snapshot 경계·미응답

C2는 B2 rows를 수정하지 않고 전달 entry에 별도 content snapshot version을 쓴다. 아직 미구현이다.
대국 생성 시 캐릭터별 고정 문구 원문/revision·당시 이름, 사용 가능한 콘텐츠의 원문/후보 정의/기본값/미디어 참조와 revision을 깊은 복사한
불변 anchor로 저장하고, 각 국 종료 writer에서 event/Level/band별 선택·치환 문구·후보 ID/revision·각 P/N
원문을 고정한다. 최종 패배 문구/CG는 별도 정산 writer의 **stage_after**를 사용한다.
이 방식은 기존 facts에 현재 콘텐츠를 소급 결합하는 것을 허용하지 않는다. 현 CharacterContent/공유 관리 revision은 과거 원문 전체의 조회 API가 아니므로 revision 번호만
저장한 뒤 나중에 현재 row를 조회하여 재구성하지 않는다. 구체 anchor schema/허용 콘텐츠와
결합/생성 시점은 아래 응답 후 C2 구현 계약에서 확정한다. 미응답인 동안 C1 unbound를 나중에 ready로 바꾸지 않는다.

고정 문구는 CPU 소유, win과 defeat_stage_1..3을 분리하고 기존 보충 match_first를 보존한다.
`{{character_name}}` 1회 평문 치환이며 재귀/조사/추가 변수 없음, 원문과 표시문 모두 보존한다.
명시 빈 문자열과 미편집 필드·pack revision/음성 selected/off는 기존 계약을 따른다.
Q-LEGACY A를 선택하더라도 한 캐릭터/event에 기존 행이 여러 개면 어떤 행을 지정할지 명시 매핑을
받아야 한다. random/min(id)/첫 행으로 자동 이전하지 않고 legacy 완료 presentation을 그대로 둔다.
새 고정 문구 관리와 이전 실행은 분리 가능하나 실제 게임 연결은 빈 초기 상태 정책까지 확정 후 한다.

공유 상황은 이미지 연출 P/N이며 텍스트 대사의 소유가 아니다. 세 점수 band와 ron/tsumo 등
명시 event, Level별 후보·지정 기본값을 결합한다. 복장/포즈는 같은 Level 허용 조합 재사용,
상황별 추가 의상 제약은 만들지 않는다. 현재 W08-D의 kind를 미승인 상황 kind로 몰래 확장하지 않는다.

후속 snapshot은 selected candidate ID/revision, 적용 content/pack revision, Level/kind, 원문 P/N,
확정된 최종 P/N, generation/session/event, immutable media UUID/digest를 가진다. 미디어가 없어도
이미 선택한 값은 재추첨하지 않는다. job 상태는 별도 관계로 둬 불변 입력과 가변 처리 상태를 섞지 않는다.
생성 seed/cache/workflow/model/LoRA·endpoint·unknown submit/재시도는 W10/W11의 응답·기술 확인
전 구현하지 않는다. 외부 submit은 DB writer/게임 lock 밖이며 파일/후보 수정이 과거 snapshot을 바꾸지 않는다.

설계에 필요한 남은 질문만 아래로 축약했다. **권고는 승인 아님**, C1은 답변 없이 독립 구현 가능하다.

| 질문 | 짧은 선택·권고 / 차단 |
|---|---|
| Q-LEGACY | 기존 문구는 A 원 행을 보존하고 명시 지정 연결 / B 새 고정 필드는 빈 상태, legacy만 기존 경로? A 권고, 복수 행은 사용자 지정 필요. 자동 이전/새 텍스트 연결 차단 |
| D05-c | A 공유 상황에서 허용 event를 편집 / B event에서 상황 목록 편집? A 권고. band1/2/3 화료 상황 매핑은 명시 등록. S/C2 선택 연결 차단 |
| Q-FRAME·D07-a | 외모→적용 속옷→복장→상황→포즈→종류별 구도 순서, P/N 각각 줄바꿈·원문 유지로 할까? A 권고. 최종 P/N builder 차단 |
| Q-IMAGE·D08 | 최초 기본 3종은 명시 생성(Q-IMAGE A), 같은 최종 입력 재사용(D08-a A), 현재 결과 snapshot 복구(D08-b A), 누락/실패는 안내+명시 재시도(D08-c A)로 할까? 각각 독립 응답 필요. 자동 생성/job/cache·실패 연출 차단 |

D07-b 모델/LoRA 범위와 D09-a endpoint 수명도 기존 미응답 그대로이며 W10 착수 전에만 추가 조율한다.
이미 확정된 player 배경/omake 화료 CG/전원 무작위 순서/단계 정책/대사 소유를 다시 묻지 않는다.

## 7. C1 수용 검사표 — 구현 시 실행, 이번 실측 아님

| 검사 | 필수 기대 결과 |
|---|---|
| 도입 migration | upgrade 반복, 기존 NULL/marker1 active/completed/web 무 backfill·무 gate; 신규 C1만 version1 |
| start/action 원자성 | 시작 version0/여러 종료국 포함. fact/entry serialize·flush·commit 각 실패에 action/facts/entry 모두 rollback·cache 폐기·같은 저장 턴 복구 |
| RNG/복수 승자 | 원본 winners 순서 불변, 1/2/복수 승자 permutation 완전성·한 번 저장·cold 복구 동일. 동일 seed trace/actions/scores/ranks와 CPU/음향 RNG 소비 불변 |
| 원본 결과 | 본장 반복/여러 pending/친자·론쯔모/3band/특수 화료·mixed·유국/triple ron/nagashimangan 원형, human 기본배경 |
| gate | pending 중 다른 socket action·직접 create·ending ack 거절, engine 미호출. 전원 확인 뒤 저장 human_turn/선택 복구, active/ending 기존 제한 유지 |
| ack | 같은 head 두 socket 동시 요청·중복/응답 유실은 한 칸만. 미래/잘못된 ID/ordinal/stale revision 거절, 실패 rollback, action_version 불변 |
| 최종 경계 | terminal action commit 후 crash/settle commit 실패→파일 SQLite cold resume→정산 한 번, 마지막 hand→settlement→ending; hand 확인과 settle 경쟁에서도 선택 노출 없음 |
| completed | engine 미호출, facts/순서/텍스트/기존 presentation 고정. ack 후 재기동에 이미 본 결과 반복 없음, pending completed는 ending/omake보다 우선 |
| 설정/자료 | 이름/stage/content/팩/기존 CG 변경이 저장 사실/순서/presentation을 덮지 않음. C1 unbound는 C2로 보충하지 않음 |
| 세대/실패 | reset 성공/실패·옛 ack/WS/media callback·generation 경쟁, 옛 rows/files/hash 보존; state 누락·마지막/ack된 entry 삭제·국 전체 누락·중복 winner/unknown version/permutation/ordinal 오류에 fallback/backfill 없음 |
| renderer | 전원 카드 저장 순서/150ms 전환·reduced motion, 중간 winner 재시작, failed image에서도 명시 확인 가능, load/ended/화면 닫기 자동 ack 없음 |
| 기존 회귀/배포 | backend 전체·대사 pytest·build·관련 browser 및 NULL legacy/W04/W05 종료·재시작, 정확한 source SHA Windows CI/artifact source/외부 archive·내부 ZIP hash |

packaged 검사는 임시 소유 DB에서 미확인 hand/settlement/ending 전후 재기동과 ack 응답 유실을
확인하고 renderer 종료 후 read-only DB로 facts/entry/cursor를 검사한다. production 진단 API 추가 금지.
실제 CG/오디오 출력·개인 Windows/전원 차단 검사는 mock/hosted CI와 구분한다.

## 8. 저성능 Work 구현 지시문·허용 파일

아래는 **후속 승인 시** 사용할 C1 단독 지시문이며 이번 설계 요청은 구현 승인이 아니다.

```text
최신 main·열린 PR·AGENTS와 루트 기준 문서를 확인해.
TASKS의 W09-C1 및 docs/W09_C_RESULT_DELIVERY_CONTRACT.md 전체를 따라 C1만 수행해.
B2와 계약 설계 PR이 병합되었는지 확인하고 task/w09-c1-result-delivery에서 시작해.
result_delivery_version은 새 local create만1, 기존 NULL/marker1/web는 그대로 둬.
별도 전달 state/불변 entries·독립 RNG 순서·서버 cursor/revision·head 단일 ack를 additive 구현해.
create/action의 facts+entries를 원자 저장하고 terminal action/별도 settle transaction은 보존해.
정산 entry는 stage/presentation/ending과 같이 저장하며 ack가 정산을 호출하지 않게 해.
local play resume·read-only results GET·ack POST·WS envelope와 서버 action/create/ending ack gate를 연결해.
모든 미확인 국/모든 승자→마지막 국→settlement→기존 ending→선택을 복구해.
C1 content_mode=unbound이며 기존 정산 v2 snapshot만 전달해. 새 문구/공유 상황/P/N/CG는 연결하지 마.
전환은 저장된 다음 head 사이 최소 opacity로, 전환/load/음향 callback은 ack/음향을 발생시키지 마.
DB cursor와 revision·generation/session/event/request token으로 두 socket·지연 응답·reset을 격리해.
원본 facts/engine/CPU/RNG/음향 ordinal·legacy 저장·사용자 파일을 보존해.
계약 §7의 수정 전후/파일 DB/cold 복구·관련 browser와 정확한 source Windows W04/W05/artifact를 검사해.
CURRENT_STATE/TASKS/ARCHITECTURE를 실제 검증대로 갱신하고 commit/push·PR 제출까지 진행해.
직접 병합·Release/tag·C2/M/S/W10/W11·콘텐츠 생성/사용자 자료 변경은 하지 마.
```

허용 파일은 `backend/app/db/models/game_session_record.py`, 새 delivery model/exports,
`backend/alembic/versions/`의 다음 additive migration, 새 `services/result_delivery.py`,
`services/game_registry.py`의 저장 접점, `services/local_play.py`, `api/game.py`, `api/local_play.py`,
`schemas/local_play.py`와 필요한 최소 delivery schema, `local_runtime.py`의 router 등록 접점,
`frontend/src/main.tsx`, `api.ts`, `game/types.ts`, 기존 스타일/최소 결과 카드 컴포넌트,
관련 backend/frontend tests·기존 W04/W05 검증 helper/workflow 최소 보강 및 세 기준 문서다.
migration 경로는 현재 `backend/alembic/versions/`이며 착수 시 최신 head를 다시 확인한다.
mahjong/CPU/규칙/B2 collector·사실 schema 변경, 콘텐츠 관리/상황 kind·팩 포맷·생성 adapter,
갤러리/배치/파일 정리·추가 애니메이션/음향 동기화는 허용 범위가 아니다.
