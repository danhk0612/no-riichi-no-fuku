# W09-C1 PR #108 — 수용 전 보완

## 최신 재검토 — R5 비동기 재조회 추가 보완이 우선

검토 head `86c4e5079f37faa0a7b4e2daa5a7ec9fe02ac339`, main `ffd21f7`.
R1 CG 로드·R2 code1000·R3 MJAI/band·R4 controlled failure 수정과 추가 검사는 코드에 반영됐다.
아래 최초 재현/요구는 이력으로 보존한다. 현재 병합 차단은 R5의 **충돌 재조회 callback**이다.
최신 head의 W04 run39591103937/W05 run39591095399 success를 API로 확인했지만,
이번 재검토에서 전체187개/build/browser·artifact 다운로드를 다시 실행하지는 않았다.
아래는 Node로 실제 helper 소스를 추출한 독립 재현이며 실제 브라우저 실행은 아니다.

### 남은 원인과 재현

`applyDeliverySnapshot`의 동일 revision/head 충돌 GET callback은 요청 당시의 `previous`에만
fresh를 비교한다. 응답 도착 시점의 resultDeliveryRef·generation·session·request token을
확인하지 않고 ref/화면/오류를 변경한다. 세 입력을 각각 실행한 결과는 다음과 같다.

| 입력 순서 | 현재 실제 결과 | 필요한 결과 |
|---|---|---|
| revision10/head10 → 동일rev 충돌로 GET 대기 → WS revision11/head11 → GET이10/head10 반환 | ref/화면이10/head10으로 역행 | 최신11/head11 유지 |
| old generation의10/head10 → 충돌 GET 대기 → 새 generation의1/new-head → old GET 반환 | 새 ref/화면을 old generation10으로 교체 | 새 세대 ref/화면·오류 유지 |
| revision10/head10 → 충돌 GET → fresh11/head=null/route=human_turn | ref만11, 화면은 여전히 이전 결과 카드 | 기존 active 복구 흐름으로 조정 |

마지막 경우 callback은 result/settlement_wait만 렌더링한다. ending/selection도 기존 복구
경로로 이어지도록 확인한다. 추가 사용자 ack를 해야만 정상 화면으로 돌아오는 것을 수용하지 않는다.

첫 두 입력은 API 응답이 지연되는 동안 다른 socket/상태 갱신이 발생하는 경우를 모델링한다.
기존 browser 검사는 충돌 GET을 즉시 완료시킨 후 낮은 revision을 보내므로 이 경쟁을 검사하지 않는다.

### 최소 수정과 회귀

- 재조회 시작의 generation/session/request token을 캡처하고 완료 시 **현재** 값과 대조한다.
  reset·새 세대·새 대국·새 요청으로 무효화된 callback은 ref/화면/오류/미디어에 영향이 없어야 한다.
- 같은 대국이어도 응답 시점의 최신 resultDeliveryRef와 revision/head/cursor를 다시 대조한다.
  요청 당시 previous와 비교하는 것만으로 통과시키지 않는다. 여전히 충돌하면 최신 카드를
  보존하고 기존 오류 상태를 유지한다. 무한 재조회/자동 ack/로컬 cursor 선행은 금지한다.
- 유효한 최신 fresh의 route 전체를 기존 복구 흐름에 반영한다. human_turn의 action_version,
  ending/selection의 phase/request token 규약은 그대로 유지한다.
- `frontend/tests/result-delivery.browser.mjs` 또는 기존 desktop routed browser에서 GET을
  실제 보류한 뒤 위 세 경로를 검사한다. 추가로 새 generation/새 session 뒤 old GET,
  valid ending/selection 재조정과 ref/화면 일치를 확인한다. 수정 전 실패를 먼저 재현한다.

기존 branch/PR #108에서 `main.tsx`의 이 경계·관련 browser 회귀·상태 문서만 최소 보완한다.
새 전달 schema/API·백엔드 정책·콘텐츠를 추가하지 않는다. R1~R4 수정과 그 검사는 보존한다.
관련 browser/build·기존 backend/대사 및 최종 수정 source Windows W04/W05와 artifact를 검증한다.
검토 전 source의 성공을 수정 후 성공으로 기록하지 않는다. commit/push·기존 PR 갱신까지이며
직접 병합·Release/tag·후속 Task는 제외한다.

---

아래는 최초 검토 head0edc3d2의 재현/보완 계약이다.

기준 main `f1671a6ecfaa62bcb95649df9253dd36b8742383`, 검토 PR #108 head
`0edc3d2f8d0d2aa4255108a0b57a721cda26f435`. 기존 branch는
`task/w09-c1-result-delivery`다. [표시·확인 계약](W09_C_RESULT_DELIVERY_CONTRACT.md)의
동작 보존과 필수 검사를 보완하며 C2/새 문구·CG 생성으로 확대하지 않는다.

## 검토 결과와 검증 범위

- 독립 Linux Python3.12.14/RiichiEnv0.4.8에서 전체 backend unittest180개/99.037초,
  대사 pytest10개/0.13초, frontend production build와 `git diff --check` 통과.
- 같은 head의 Windows W04 run39574241877/W05 run39574241870은 success다.
  기존 성공 결과와 아래 결함 재현을 구분한다. 성공한 smoke가 계약 전 항목을 검증하지는 않는다.
- 앞선 자동 리뷰의 defeat voice는 C1 early return 앞 전송으로, 정산 이름은 저장 participants를
  사용하는 방식으로 수정돼 있다. 실제 React SSR에서 저장 이름이 표시됨을 확인했다.
- 로컬 Chromium 설치는 다운로드 archive 오류로 실패했다. 아래 UI 증거는 Vite SSR 또는
  실제 소스 분기를 추출한 callback 실행이며 실제 브라우저 실행으로 보고하지 않는다.
  개인 Windows/전원 차단은 미검증이다.

다운로드한 W04/W05 source-sha.txt는 검토 head와 같고 outer SHA256은 GitHub digest와,
내부 Windows ZIP SHA256은 zip-sha256.json과 일치했다. 각180개·대사10개, W05 renderer33검사와
일반 종료/재시작을 확인했다. read-only hand-results.json은 revision0013, 완료 대국의8개 국 사실과
9개 표시 entry, acked_ordinal8/terminal_ordinal9로 미확인 settlement 보존을 기록했다.

| 성공 증거(수용 완료와 구분) | ID / SHA256 |
|---|---|
| W04 artifact | 12334201673 / 4dc321753a427d6d7dd4896a081316b5d186683f9b0afbd3d7bef67c30a021c4 |
| W05 artifact | 12334206944 / 237c205377a2b75de9a62b508462242a68df5f25ab38543f5b940dcc17862a84 |
| 내부 Windows ZIP | 3b30c91769b2309adb1de6e23b238c51855f5af81cd93c05330584df2079057d |

## R1 — 새 정산 카드에서 기존 CG가 사라짐

`ResultDeliveryCard`는 `presentation.result_dialogues`만 읽고 기존
`presentation.result_asset`을 표시/로딩하지 않는다. CG fetch와 오류/늦은 응답 처리는
`match_complete`→`complete` 화면에만 있는데 C1 WS는 envelope 뒤 return하므로 이 경로를 쓰지 않는다.

독립 SSR 재현: 실제 `MahjongTable`에 `status=result_delivery`, settlement head,
`presentation.result_asset={id:99,url:'/api/game/result-assets/99/file',defeat_stage:1}`과
stage_changed=true를 공급했다. 저장 이름/점수는 출력됐지만 img/CG 로딩/실패 안내는 모두 없었다.
이미지는 생성/등록하지 않았으며 메타데이터 fixture로 출력 경로만 검사했다.

보완: 기존 v2의 저장된 asset 참조로 로드·표시하고 미등록/실패에도 명시 확인은 가능하게 한다.
generation/session/event/참조 identity가 바뀐 뒤 늦은 응답이 새 카드나 오류를 덮지 못하고,
object URL은 기존 수명 규칙으로 해제한다. 현재 설정/CG를 다시 선택하거나 새 CG를 생성하지 않는다.
브라우저에서 등록 참조/미등록/실패/ack 또는 reset 뒤 늦은 응답을 회귀로 고정한다.

## R2 — 미완료 code1000 종료의 행동 잠금·복구 안내 회귀

`main.tsx`의 close handler가 `!completed && event.code !== 1000`으로 변경돼 미완료 대국이
서버 code1000으로 끊겨도 행동 잠금/복구 안내를 하지 않는다. 이는 C1 외 NULL 웹 경로에도 적용된다.

실제 close callback 소스를 추출해 completed=false, code1000으로 실행했다.
기존 main은 actionsDisabled=true와 재로그인/복구 안내를 설정하지만 PR head는 false/null이었다.
기존 `frontend/tests/connection.browser.mjs`에도 code1000/1011의 잠금·복구 검사가 이미 있다.

보완: 의도한 C1 화면 전환/소켓 교체는 명시적으로 구분하면서 미완료 연결 단절은 code1000도
기존대로 잠근다. 해당 기존 browser 회귀를 다시 실행하고 W05에도 빠지지 않게 최소 연결한다.
신규 reconnect 기능이나 연결 정책 변경은 추가하지 않는다.

## R3 — MJAI 국 번호에 +1하여 첫 국을 2국으로 표시

실제 고정0.4.8 adapter seed701의 최초 `start_kyoku`는 `{bakaze:'E',kyoku:1,honba:0}`다.
B2 payload는 이 원본을 복사한다. C1 카드 제목/요약은 `Number(start.kyoku)+1`을 사용해
실제 React SSR에서 kyoku1이 2국으로 출력됐다. observation의 zero-based kyoku_index와 다르다.

보완: 원본 MJAI 번호를 그대로 표시하고 E1/E4·본장 반복·남장 등으로 회귀한다. B2 facts/엔진은
수정하지 않는다. C1 fixture의 kyoku0, 문자열 band/문자열 yaku도 실제 B2 타입에 맞춰 고친다.
band 숫자는 사용자에게 1/2/3만 노출하지 말고 기존 확정된 세 구간 이름으로 표시한다.

## R4 — 결과 전달 구성 실패가 WS controlled failure로 연결되지 않음

registry의 `append_hand_entries`는 `ResultDeliveryError`를 발생시킬 수 있다. submit_action의
실패 guard는 game/cache를 폐기하고 원래 예외를 다시 올리지만 WS action handler는
HandScoreCaptureError/GameRegistryError/SQLAlchemyError만 처리한다. ResultDeliveryError는 그 하위가 아니다.

실제 임시 SQLite local runtime에서 새 C1 대국을 만든 뒤 WS human_turn을 받고,
registry의 append_hand_entries에 `ResultDeliveryError('injected delivery validation failure')`를
주입했다. 합법 action 후 error envelope 대신 TestClient 바깥으로 원래 예외가 전파됐다.
이는 저장 이후 표시 정책 추가가 아니라 기존 계약의 수집/전달 실패 경계 검사다.

보완: 원본 진행 후 전달 구성/검증 실패를 rollback·game/cache 폐기와 기존
`result_delivery_invalid`/close1011로 연결한다. DB 실패는 기존 persistence_failed로 구분한다.
새 오류 정책을 만들지 않는다. create/action/별도 settle의 실제 writer 실패 경계도 확인하고,
저장 action/facts/entry/cursor/stage 불변 및 같은 저장 턴 cold 복구를 회귀로 고정한다.

## R5 — revision 조정과 계약 필수 회귀 보강

`delivery_revision`은 타입/ack body에만 쓰이고 renderer의 GET/WS/ack 적용 경로에 비교가 없다.
실제 result_delivery message 분기를 추출해 동일 generation/session의 revision9/head2 다음
revision8/head1을 공급하자 화면 상태가 revision8/head1로 되돌아갔다. 전송이 반드시 이 순서로
발생한다는 실측은 아니며, 계약 §5의 이전 snapshot 거절 불변조건이 구현되지 않은 최소 입력 재현이다.

보완: 같은 generation/session의 낮은 revision은 폐기하고, 같은 revision의 불변 head 충돌은
계약대로 재조회한다. action_version과 phase/request token은 별도로 유지한다. 서버 cursor가
최종 기준이며 성공을 추정해 먼저 이동하지 않는다. 각 entry 전환의150ms/reduced-motion도
실제 다음 head에서 동작하는지 검사한다. 초기 CSS animation 선언만으로 전원 전환을 수용하지 않는다.

추가된 C1 unittest는3개이며 정상 GET/직렬 ack·잘못된 요청 일부·create/ending gate를 다룬다.
B2/기존 검사를 자동 ack helper로 통과시키는 것만으로 다음 C1 고유 검사를 대체하지 않는다.

| 계약 §7 | 보완할 의미 있는 검사 |
|---|---|
| 저장/실패 | create/action delivery entries와 별도 settlement append의 serialize/flush/commit 실패 원자성; ack commit 실패 시 cursor/revision 불변·재시도 |
| 순서/완전성 | 0/1/복수 승자·mixed/draw 원형, permutation 전원/불변·cold 복구, state/마지막/ack된 entry/국 전체 누락을 GET과 gate에서 무쓰기 거절 |
| 동시성/gate | 파일 SQLite 두 독립 writer의 같은 head 동시 ack 한 칸, stale revision/잘못된 identity 거절; pending action에서 engine/CPU 미호출 |
| 복구/세대 | terminal hand→settlement→ending 우선순위, ack 응답 유실/두 socket·reset 경쟁/옛 응답과 callback 격리, 완료 복구 엔진 미호출 |
| renderer/호환 | R1~R3/R5의 실제 routed browser, 기존 connection/result-asset 등 관련 회귀, 기존 NULL/B2/web 대국 무소급·무 gate |

기존 fixture/검사에 최소 assertion을 추가해도 된다. 합성/실제 엔진/브라우저/packaged 증거를
구분하고, 누락을 완료로 보고하지 않는다. 새로운 자연 seed 탐색·정책 변경은 없다.

## 다음 Work

권장: 저성능 Work. 최신 main·PR #108 head와 AGENTS/루트 문서, 기존 계약 및 본 문서를 읽는다.
기존 branch/PR #108을 유지하고 main의 검토 문서를 정상 반영한다. 먼저 R1~R5의 수정 전 실패를
회귀로 고정한 뒤 계약의 기존 파일 범위에서 최소 수정한다. 다른 사용자/worker 변경을 덮지 않는다.
backend 전체·대사·build·관련 browser·정확한 최종 source W04/W05와 다운로드 artifact source/
outer hash·내부 ZIP·packaged DB/renderer/종료/재시작을 확인한다. 수정 전 성공 artifact를 수정 후
검증으로 쓰지 않는다. CURRENT_STATE/TASKS/ARCHITECTURE·기존 PR을 실제 결과로 갱신한다.
commit/push·PR 제출까지이며 직접 병합·Release/tag·C2/M/S/W10/W11·새 콘텐츠/생성은 제외한다.
