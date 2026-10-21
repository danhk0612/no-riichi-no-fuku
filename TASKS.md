# 개발 Task

## W09-C1 PR #108 R1~R5 보완 — 제출 및 검증 완료, PR 검토 대기

기존 branch/PR #108에 최신 main `ffd21f7`의 R1~R5 검토 결과를 반영했다. 현재 변경 사항과
실제 검증 결과는 [CURRENT_STATE](CURRENT_STATE.md) 및 GitHub checks/artifacts를 따른다.
제품 코드 SHA `04f4d0077acba3ca820ec766799ee881564375f3`의 Windows W04/W05 run 및 artifact를
확인했다. PR은 열린 채 유지한다.
직접 병합·Release/tag·C2/문구/CG 생성·후속 Task는 포함하지 않는다.

아래는 이번 보완의 실행 계약과 역사 기록이다.

권장: **저성능 Work**. 검토 head0edc3d2/mainf1671a6이며 시작 시 최신 Git을 다시 확인한다.
새 구현/후속 Task가 아니라 기존 `task/w09-c1-result-delivery`와 PR #108을 보완한다.

```text
danhk0612/no-riichi-no-fuku의 W09-C1 PR #108만 보완해.
최신 main·열린 PR·AGENTS와 기준 문서를 확인하고,
docs/W09_C_RESULT_DELIVERY_CONTRACT.md와 docs/W09_C1_REVIEW_FINDINGS.md 전체를 따라.
R1~R5 수정 전 실패를 회귀로 고정한 뒤 기존 CG 표시·연결 종료 잠금·MJAI 국 번호,
전달 실패의 기존 controlled error와 renderer revision 조정을 최소 수정해.
계약의 C1 고유 원자성/동시성/손상·세대 복구 검사와 관련 browser를 보강해.
전체 backend/대사·build·관련 browser, 최종 source Windows W04/W05와 다운로드 artifact
source/hash·내부 ZIP·packaged DB/renderer/종료/재시작을 확인해.
CURRENT_STATE/TASKS/ARCHITECTURE·기존 PR을 실제 검증/미검증대로 갱신하고 commit/push까지 진행해.
직접 병합·Release/tag·C2/문구/새 CG·음향 생성·후속 Task는 하지 마.
```

아래 최초 C1 지시문/설계 기록은 이력이며 위 보완이 우선한다.

## 국 결과 표시·확인 계약 설계 — 검토 수용

main `c197029`/B2 PR #104 수용과 실제 복구 흐름을 확인하고
[표시·확인 계약](docs/W09_C_RESULT_DELIVERY_CONTRACT.md)을 작성했다.
C1 전달·확인과 C2 콘텐츠 snapshot/문구 관리/공유 상황/생성을 분리했다.
PR #107 검토에서 사실 전체↔표시 entry의 완전 대응과 마지막/ack된 entry 누락 검사를 보강했다.
이 기록은 PR #107 당시의 설계 검토 상태다. 병합 상태는 PR #107/Git을 따른다. 이전 통합 W09-B 지시문은
본 계약의 C1/C2 선행·허용 범위로 대체하며 일괄 구현 지시로 사용하지 않는다.

## W09-C1 최초 구현 — 제출 당시 기록

사용자 지시로 prepared main `f1671a6`에서 `task/w09-c1-result-delivery`를 진행한다.
B2와 계약 설계 선행은 main에 반영되어 있다. [전달·확인 계약](docs/W09_C_RESULT_DELIVERY_CONTRACT.md)
§1~8 전체를 적용했고 PR #108을 main에 제출했다. 현재 검증/상태는 CURRENT_STATE와 GitHub PR을 따른다.
content_mode=unbound 및 새 local 대국 opt-in 경계를 지키며 기존 대국에 전달 snapshot을
소급하지 않는다. Windows W04/W05·packaged source SHA 검증을 PR 제출 후 확인한다.
PR review에서 나온 defeat voice 순서·정산 참가자 이름 이슈를 수정해 최신 source로 재검증한다.
문구/P/N·CG·생성 후속 작업은 이 범위에 포함하지 않는다.

## W09-B2 — 최종 검토·병합 완료

PR #104/main3341d4e, 검토 head3bb3307/treef4de724 일치. 독립 backend177개·대사10개와
최종 source의 W04/W05·두 artifact/내부 ZIP hash·packaged 국 사실/종료/재시작을 확인했다.
수용 근거/합성 fixture·실측 경계는 CURRENT_STATE를 따른다. R1/R2/R3 보완은 수용했으며
표시/ack/문구/CG/생성의 완료를 뜻하지 않는다. 아래 구현 지시문은 이력이다.

## W09-B2 PR #104 보완 — 제출 당시 기록

기존 `task/w09-b2-hand-results`와 PR #104에서 보완했다. 최신 main의 PR #105 검토 문서를 병합했다.
R1/R2 최소 수정과 회귀, R3 저장·복구 회귀를 추가했다. Linux backend 177개, 대사 pytest 10개,
frontend production build, W09-B2 핵심 13개, exact source SHA의 Windows W04/W05·packaged read-only
JSON 검증이 통과했다. 상세 run/artifact/hash는 CURRENT_STATE를 따른다. PR #104는 open이며 직접 병합하지 않았다.
로컬 Chromium 미설치로 routed browser는 Windows W05 artifact에서 검증했다.
[기존 계약](docs/W09_B2_HAND_RESULTS_CONTRACT.md)과 [검토 보완 R1~R3](docs/W09_B2_REVIEW_FINDINGS.md)을 따른다.

```text
danhk0612/no-riichi-no-fuku의 PR #104(W09-B2)만 보완해.
최신 main·열린 PR·AGENTS와 루트 문서를 확인하고
docs/W09_B2_HAND_RESULTS_CONTRACT.md 및 docs/W09_B2_REVIEW_FINDINGS.md 전체를 따라.
기존 task/w09-b2-hand-results branch/PR을 이어가며 다른 작업을 덮지 마.
R1 prefix alias와 R2 중복 sequence 검증을 수정 전 실패 회귀로 고정한 뒤 최소 수정해.
R3 표의 start/version0·원자 저장 실패·파일 DB cold 복구·최종 action/정산 실패·모드/legacy
검사를 실제 B2 경로로 보강하고 검사별 계약 대응을 기록해.
전체 backend/대사·기존 build/browser, 최종 source SHA W04/W05 및 다운로드 artifact
source/hash·내부 ZIP·packaged read-only 국 결과 JSON을 확인해.
CURRENT_STATE/TASKS/PR을 실제 검증/미검증대로 갱신하고 commit/push·기존 PR 제출까지 진행해.
직접 병합·Release/tag·표시/ack/UI/gate·문구/CG/생성 후속 Task는 하지 마.
```

아래 최초 구현 지시문은 이력이며 현재는 위 보완이 우선한다.

## 현재 다음 Work — W09-B2 국 결과 사실 저장·복구

권장: **저성능 Work**. 준비 main `67c4335`(PR #102 병합).
[W09-B2 계약](docs/W09_B2_HAND_RESULTS_CONTRACT.md) 전체가 아래 지시문과 함께 적용된다.
표시 queue/ack·문구/CG는 후속으로 남기고 사실 누적·원자 저장·복구를 먼저 구현한다.

```text
danhk0612/no-riichi-no-fuku의 W09-B2만 수행해.
최신 main/현재 branch/열린 PR, AGENTS와 루트 기준 문서를 읽어.
준비 main67c4335의 PR #102 병합과 B1 최종 source315409c 검증을 확인하고
문서 W09_B2_HAND_RESULTS_CONTRACT.md 전체를 따라.
task/w09-b2-hand-results에서 별도 내부 국 결과 collector와 새 로컬 대국의 사실 영속을 구현해.

B1 last_hand_wins를 매 engine step 직후 대응하고 원본 start/end log offset으로
전체 화료자·유국을 묶어 사람 차례 사이의 모든 종료국을 별도 누적해.
기존 pending_events/음향 ordinal을 재사용하거나 callback/CPU RNG를 바꾸지 마.
새 marker1 로컬 대국만 수집하며 NULL 구 저장/웹의 동작과 기존 completed 읽기를 유지해.
최신 migration head를 확인해 다음 additive revision과 GameHandResult/최소 marker를 추가해.
참가자/당시 이름/stage는 저장된 players/cpu_choices에서 가져오고 현재 진행값으로 덮지 마.
create 시작 batch 및 action indices와 사실 rows를 같은 writer transaction에 저장해.
중복 identity는 완전 동일할 때만 유지하고 충돌/점수 누락을 fallback/upsert로 숨기지 마.
flush/commit/수집 실패에는 rollback·cache 폐기·저장 턴 복구를 유지해.
active replay는 저장된 사실 전체와 대조 후 과거 batch를 비우고 GET에서 backfill하지 마.
completed는 replay/재정산 없이 읽고 마지막 action→별도 정산의 기존 경계를 보존해.
reset은 old generation 사실/사용자 파일을 보존해.

문구·prompt/content/media snapshot/무작위 표시순서/ack·새 API/WS/화면·새 행동 gate는 추가하지 마.
설정/규칙/CPU/오디오·ComfyUI·이미지/사운드 생성·사용자 자료 삭제는 제외해.
원본 trace/policy1/2/3·복수 pending/유국/트리플론/특수 화료·중복/변조/누락,
create/action 저장 실패·재시작/정산 전 crash·reset/legacy를 계약 검사표대로 검증해.
고정seed701 Tier0/2×수집전후4대국의 로그/점수/행동 동일성과 수집 비용을 기록해.
전체 backend/대사·기존 build/browser, 최종 SHA Windows W04/W05 및 artifact source/hash를 확인해.
packaged renderer 종료 후 소유 game.db를 read-only로 검사해 새 marker/국 사실/terminal 근거를
artifact에 기록하되 production 진단 endpoint는 만들지 마.
CURRENT_STATE/TASKS/ARCHITECTURE를 실제 구현/미검증대로 갱신하고 commit/push·PR을 제출해.
직접 병합·Release/tag·후속 표시/생성 Task 착수는 하지 마.
```

## W09-B1 — 검토·병합 완료

PR #102/main67c4335, 검토 head315409c/tree841298b 일치.
Linux165개·대사10개와 동일 source Windows W04/W05·두 artifact/내부 ZIP hash를 확인했다.
[구현 계약](docs/W09_B1_HAND_SCORE_ADAPTER.md)의 점수 adapter·controlled failure/복구까지 완료다.
국 사실 저장·표시/CG는 이 완료에 포함하지 않는다. 상세 수용 근거는 CURRENT_STATE를 따른다.

모든 미착수 Task는 계획이며 실행 승인이 아니다. 상태는 구현/검증 사실로만 변경한다.
W00은 초기 분석·기준 문서 준비(완료); 본 파일은 후속 개발 명세다.
Task 목적·금지 범위·완료 기준 변경이 필요하면 사용자 결정 후 갱신한다.

## W09-A — 진단 완료·점수 경로 채택 차단

기준 main `d90cc4d`(PR #98 병합). 제품 코드 변경 없이
[진단 결과](spikes/w09-a-hand-results/README.md)와 작은 재현 근거를 추가했다.
16대국/10.546초, 수집 전후8쌍 trace·최종 점수/순위 동일. 중간 국 WinResult 소실,
observation hora 중복, 복수 론 가능을 확인했다. native replay는 live와 한/역이 달라 채택 중단.
viewer는 최종 화료7건의 한/부/역 일치만 확인했고 본장·특수 화료를 포함한 전체 정확성은 미입증이다.
점수 unknown을 일반 구간으로 처리하지 않는다. 기존 경계 회귀5개 통과, 제안 표시 모델11검사 통과.
Windows/새 국 결과 queue/생성은 미구현·미검증이다. source/hash/예산은 spike evidence 참조.

### 현재 다음 단계 — 점수 경로 추가 진단 전 범위 확정

- 점수 gate: 기존0.4.8 공개API의 정확한 중간 국 판정값 보존 경로를 별도 한정 진단해야 한다.
  native/viewer 실패를 고친 것으로 가정하지 않는다. 공개API로 불가능하면 엔진 변경/업그레이드의
  별도 사용자 결정을 요청하며 이번 승인으로 우회하지 않는다. 추가 자연 표본 실행 예산도 별도다.
- 복수 화료 배경은 사용자 결정으로 전원 **무작위 순서·전환 효과**로 표시한다. 결과별 순서를
  한 번 저장하고 재진입/재시작에 재추첨하지 않는다. 원본 화료/정산 순서와 별개이며 플레이어 슬롯은 기본 배경이다.
  원본순 표시/한 명 대표 권고는 채택하지 않는다. 남은 기술 차단은 정확한 전 국 점수 경로다.
- 생성 입력/후보 선택/캐시/대기·실패 정책과 ComfyUI 실제 기술 확인은 W10/W11 선행이며 미응답을 유지한다.
- W09-A 완료는 진단 제출물 완료다. **W09-B/기존 W09 전체 또는 점수 수집 성공으로 표시하지 않는다.**

## W09-A 진단 후 구현 분해 — 실행 승인 아님

### 관리 — 3점수구간 P/N·캐릭터 고정 문구 (저성능 Work)

```text
최신 main·열린PR·AGENTS·루트 문서와 W09-A spike README를 읽어.
이 지시문이 별도 승인된 경우에만 관리 부분을 독립 branch에서 수행해.
만관 미만/만관·하네만/배만 이상3구간의 포즈·배경 상황P/N과 캐릭터 고정 문구 편집을 분리해.
대사 소유자는 캐릭터이며 공유 문장풀/무작위 문장 후보를 만들지 마.
파일 범위는 기존 CharacterContent/SharedPrompt 관리 model/schema/service/local API와
CharacterContentSettings·types/api, 필요한 최소 additive migration 및 관련 테스트야.
기존 외모/속옷/단계구도 P/N·voice 연결/override/빈 값·pack revision 보존을 유지해.
공유 상황과 Level·후보의 구체 관계/D05-c 중 미응답은 임의 채택하지 말고 차단으로 남겨.
캐릭터 고정 패배 문구는 defeat_stage_1..3, win 문구와 분리하고 character_name 변수만1회
평문 치환해. 저장 검증/원문·표시snapshot을 구분하며 W06 ending 평문에는 적용하지 마.
기존 cpu_dialogues의 여러 행 중 하나를 몰래 골라 이전하지 말고 원본/완료presentation을 보존해.
기존 행 대응/새 고정문구 초기 연결(Q-LEGACY)은 승인된 범위에서만 수행해.
새 실제 문구/P/N/이미지 seed·생성·게임event 연결은 제외해.
수정/빈문자열·미편집값/voice 독립·삭제/이동 영향·revision 충돌·reset/restart 보존을 검증해.
backend/build/관련 browser와 정확한 SHA의 W04/W05 Windows CI·artifact source/ZIP hash를 확인해.
CURRENT_STATE/TASKS/ARCHITECTURE를 갱신하고 commit/push·PR만 제출해.
직접 병합·Release/tag·W09-B/생성/결과UI 착수는 하지 마.
```

### W09-B — 국 결과 영속·텍스트·표시 순서/복구 (점수/표시 정책 gate 후 저성능 Work)

```text
최신 main·열린PR·AGENTS·루트 문서와 W09-A README 전체를 확인해.
점수 경로 검증이 선행이야. 미검증이면 제품 구현을 멈춰. 복수 화료는 확정된 무작위 순서·전환 효과로 전원 표시야.
기존0.4.8 및 규칙/CPU/seed/actions/policy1/2/3·pending 음향 ordinal을 보존해.
파일 범위는 mahjong adapter/session의 별도 결과수집, game_registry·game API,
최소 result DTO/영속model·additive migration, types/api/main의 최소 텍스트결과 queue와 회귀야.
MJAI start/end log offset으로 모든 국/화료자를 고정해. 같은국 복수hora/ryukyoku를 함께 보존하고
다음 국 observation의 현재stage/oya를 종료국에 쓰지 마. delta로 등급을 추정하지 마.
대국시작 cpu_choices→actor/CPU/stage/name과 당시content revision·고정문구를 snapshot해.
create/start와 각 action transaction에 새 국 결과를 함께 고정하고 실패하면 rollback/cache evict해.
최종action→기존별도정산 경계는 유지하며 표시ack가 정산/stage 변경을 다시 실행하지 않게 해.
모든 미확인 국→마지막 국→최종 결산·stage_after CG/패배문구→기존ending ack→자유대국 순서야.
표시cursor/ack는 generation/session/event로 멱등·건너뛰기 거절·응답유실/재시작 복구를 지원해.
시작 시 ending_pending보다 미확인 결과queue를 우선하고 다음대국이 queue를 건너뛰지 않게 해.
reset/stale socket/응답은 기존세대로 격리하고 과거snapshot/파일은 보존해.
legacy queue 없는 active/completed는 원형식으로 복구하고 현재content로 과거결과를 생성하지 마.
플레이어/유국은 기본배경, omake는stage3/난이도10·기존대사/음성·화료CG 허용이야.
CG는 mock/미등록 상태로만 연결하고 생성/새리소스/ComfyUI·시각연출은 제외해.
매국/복수화료·본장/리치봉·친자/론쯔모·구간경계·특수화료와 기존policy replay,
복수pending·마지막화료/유국→결산→엔딩·action/정산 commit실패·ack응답유실·reset·legacy를 검사해.
회귀·build/browser·정확한SHA Windows W04/W05·artifact source/hash와 packaged재시작을 확인해.
문서 갱신·commit/push·PR 제출만 하며 직접 병합·Release/tag·W10/W11 구현은 하지 마.
```

### W10/W11 — 독립 생성 경계 (정책/실제 기술 확인 후 별도 Task)

```text
최신 main/열린PR/AGENTS/루트 문서와 W09-A·W09-B 결과를 확인해.
W10은 adapter/설정·소유job/status/result 및 mock계약, W11은 W09 snapshot→선택/P/N/생성파일
연동으로 나눠 별도 승인/branch/PR에서 수행해. Q-IMAGE/Q-FRAME/D07~09 미응답은 임의 확정하지 마.
실제 사용자의 ComfyUI object_info/workflow/node/model·LoRA 지원과 결과수신 기술을 먼저 확인해.
게임정산/RNG와 독립, 외부submit은 writer/lock 밖, snapshot/독립seed/cache identity 고정,
unknown submit/응답유실·재시작·늦은job·새대국/reset을 구분하고 원본/과거파일을 보존해.
화료 현재stage/점수3구간과 최종패배 stage_after CG를 혼동하지 마.
기본대국은 미연결/실패/무이미지에서도 계속돼야 해. 자동모델다운로드/전역interrupt/무단삭제 금지야.
mock와 실제로 승인된 Windows/ComfyUI 검증·정확한SHA artifact를 구분하고 문서/PR에 남겨.
직접병합·Release/tag·후속UI/추가콘텐츠 제작은 하지 마.
```

### W11-U — 국 결과 배경·최종 단계 CG 연출 (W09-B/W11 후 저성능 Work)

```text
최신 main/열린PR/AGENTS/루트 문서와 W09-A/B·W11 DTO를 확인해.
파일 범위는 main/MahjongTable/types/api/style와 최소결과/뷰어 컴포넌트야.
서버에 한 번 저장한 무작위 화료자 표시순서로 전환 효과를 넣어 전원 표시해. 재렌더/재진입에 재추첨하지 마.
renderer가 승자/점수/정산을 계산하거나 CG 전환으로 대사/음향을 다시 발행하지 마.
각국 화료자 현재복장+점수구간 배경, 마지막국 결과 후 최종결산·변경후stage CG/고정패배문구,
그뒤 기존엔딩을 표시해. 플레이어/유국은 기본배경, omake는화료CG만 같은규칙으로 연결해.
미등록/로딩/깨진이미지는 진행/표시ack를 막지 않고 자동ack하지도 않게 해.
CG전용/복귀/줌팬·reload/재조회가 재정산/추첨/submit을 만들지 않게 해.
stale image/job·generation/session/selection token·다음대국/reset·ack응답유실/재시작과
마지막국→결산→엔딩 순서를 browser/정확한SHA Windows packaged흐름으로 검증해.
실제이미지 없는검증과 제공리소스실측을 구분하고 문서·commit/push·PR만 제출해.
직접병합·Release/tag·갤러리/추가연출·새생성정책 구현은 하지 마.
```

## 수행 이력 — W08-D 공유 복장 상태·포즈 관리

W08-M PR #93과 정책 PR #94가 병합됐다. 사용자 CG 재확인은 REQUIREMENTS 최신 절을 따른다.
W08 전체 중 확정된 복장 상태/포즈 원문·캐릭터별 명시 후보·기본값·확인 후 삭제/이동부터 분리한다.
구현 계약은 `docs/W08_D_SHARED_PROMPTS_CONTRACT.md`이며 권장 환경은 저성능 Work다.
상황/대사 이벤트 연결·기존 대사 이전·모델/생성은 남은 정책 확정 후 별도 순서로 수행한다.
구현 브랜치 `task/w08-d-shared-prompts-impl`에서 제품 코드·회귀를 제출했다. exact-head Windows CI/artifact와 packaged 보존 검증은 PR #96의 최종 source 기록을 따른다.

```text
danhk0612/no-riichi-no-fuku의 W08-D만 수행해.
최신 main·현재 branch·열린 PR·AGENTS.md와 루트 기준 문서를 확인해.
W08-M PR #93·정책 PR #94 및 W08-D 설계 PR의 병합을 확인하고
TASKS와 docs/W08_D_SHARED_PROMPTS_CONTRACT.md 전체를 따라.
task/w08-d-shared-prompts-impl에서 기존 사용자/다른 브랜치 변경을 덮지 말고 작업해.

Level별 공유 복장 상태·포즈의 label/P/N CRUD, 기존 CPU의 Level/종류별 명시 후보,
지정 기본값과 fallback, 삭제/Level 이동 영향 확인·확인 후 기본값 복귀를 구현해.
공유 원문은 한 번만 저장하고 신규 항목을 기존 CPU 후보에 자동 포함하지 마.
원문·빈 P/N·ID/revision·GET 무쓰기·같은 writer의 원자 commit·자료 reset/restart 보존을 지켜.
기존 캐릭터 설정에 최소 관리 탭을 추가하고 CPU 선택·현재 대국·음향을 보존해.

상황/대사/event 매핑·변수 실행·기존 대사 이전·모델/LoRA·생성/이미지/CG 표시,
팩 manifest/scanner·새 팩 종류·CPU/규칙/난이도/진행/정산은 변경하지 마.
CG는 캐릭터별·단계별 자료이며 패배로 단계 변경 후 변경된 단계의 CG를 표시한다.
별도 패배 CG kind/화료 CG 기능을 추가하지 마. 실제 문구/이미지/음향을 작성·seed·커밋하지 마.

계약의 migration/API/후보/기본값/삭제·이동/브라우저 회귀와 backend 전체·대사pytest·build,
정확한 최종head W04/W05 Windows CI 및 다운로드 artifact source/hash,
packaged UI 저장·초기화·engine 재시작 보존 검증을 마쳐.
CURRENT_STATE/TASKS/ARCHITECTURE와 사용자 README를 사실에 맞게 갱신해.
commit/push·PR 제출까지 진행하되 직접 병합·Release/tag·후속 Task 착수는 하지 마.
```

## W08-M 제출 이력 — PR #93 병합 완료

W-DIFF-B는 PR #91로 병합됐다. W08-M은 준비 main `8e44eb1`에서 구현했으며,
CharacterContent nullable 치수 JSON·기존 revision/override·팩 명시 적용·선택 카드·기존 편집 UI를
계약에 맞춰 확장했다. Linux backend 143개, 대사 pytest 10개, frontend build 및 브라우저 4종을 통과했고
PR #93을 제출했고 현재 병합 완료다. 아래는 당시 checkpoint이며 최신 검토는 CURRENT_STATE를 따른다. 당시 source `efbe2ce0247b45b8f521820ff36be6dfcdf40ecc`의 Windows Server 2022 x64 W04/W05가
통과했다. W05 artifact source SHA·ZIP SHA256 및 packaged 치수 저장/초기화/재시작 smoke 근거는 CURRENT_STATE에 기록했다.
개인 Windows PC 실기는 미검증이다. 세부 범위와 보존 조건은 `docs/W08_M_METADATA_CONTRACT.md`를 따른다.
공유 관리/변수/생성 정책과 W08-M을 분리한다.

### 수행에 사용한 지시문 — W08-M (기록)

```text
danhk0612/no-riichi-no-fuku의 W08-M만 수행해.
최신 main·현재 branch·열린 PR·AGENTS.md와 루트 기준 문서를 확인해.
PR #91 및 W08-M 설계 PR 병합을 확인하고 docs/W08_M_METADATA_CONTRACT.md 전체를 따라.
task/w08-m-character-measurements에서 기존 사용자/다른 브랜치 변경을 덮지 말고 작업해.

Q-META A의 선택 입력 키·B/W/H(cm·소수1자리·미입력 숨김)를 기존 캐릭터 설정에 구현해.
CharacterContent additive JSON·기존 revision/override를 사용하고 local content GET/PATCH,
팩 명시 적용의 필드별 Q-PACK A, 기존 편집 UI와 선택 카드 최소 표시만 확장해.
manifest v1 opaque metadata/과거 revision·digest는 보존하고 scanner에서 소급 정규화하지 마.
새 팩 적용의 잘못된 치수는 P/N/voice까지 부분 반영하지 말고 전체 이전 상태를 유지해.
미포함 필드는 보존하고 명시 null/원본과 같은 값 저장도 직접 편집으로 보호해.
초기화·재시작 보존, 늦은 응답/캐릭터 전환·revision/commit 경계를 지켜.

실제 치수/이미지/프롬프트/음향을 임의 seed·생성하지 마.
CPU 난이도·성향·게임 snapshot/규칙/정산·음향 RNG, shared 상황/후보/변수/생성,
전신/CG/hover 상세/뷰어, 팩 교체·해제 기능은 변경하지 마.

계약의 migration/API/팩/브라우저 회귀와 backend 전체·대사pytest·frontend build,
정확한 최종head W04/W05 Windows CI 및 다운로드 artifact source/hash,
packaged 치수 편집·재시작·초기화 보존 검증을 마쳐.
검증 사실/미검증과 CURRENT_STATE/TASKS/ARCHITECTURE/REQUIREMENTS/README를 갱신해.
commit/push·PR 제출까지 진행하되 직접 병합·Release/tag·후속 Task 착수는 하지 마.
```

## 순서와 우선순위

2026-10-18 추가 승인 범위: **CPU 무늬 계산 오류 직접 교정**. 사용자 결정으로 이번 오류의
구버전 동작을 보존하지 않는다. Tier1/2의 물리ID→패 종류→무늬 계산만 고치고 관련 회귀와
정확한 head의 Windows CI를 확인한다. 새 policy/호환 분기·다른 평가식/난이도1~10 채택·
기존 사용자 자료 삭제는 포함하지 않는다. 연구별 원본 불변 조건은 당시 source 기준으로 보존한다.
구현·검증 결과는 CURRENT_STATE와 해당 교정 PR의 최종 source 기록을 따른다.

| ID | 작업 | 우선순위/상태 | 선행 | 권장 환경 |
|---|---|---|---|---|
| W01 | 기존 기능·회귀 기준 확정 | P0 / 기준 확정 완료(브라우저 환경 차단) | W00 | 저성능 Work |
| W02 | Windows 실행·엔진 번들 기술 검증 | P0 / 기술 검증 완료(Windows CI, 사용자 실기 미검증) | W01 | 고성능 Work |
| W03 | 실행·저장·프로필 정책 확정 | P0 / 정책·W04/W05 계약 확정 | W02 | 고성능 Chat |
| W04 | 로컬 저장·복구 기반 전환 | P0 / 완료(PR #61 병합) | W03 | 저성능 Work (구조 설계 필요 시 고성능 Work) |
| W05 | Windows shell·오프라인 게임 통합 | P0 / 구현·Windows hosted 검증·최종 검토 통과(개인 실기 미검증) | W04 | 저성능 Work |
| W06 | 고정 참가 명단·진행/오마케·초기화·사운드 | P0 / A·B·C 최종 검토 통과(D11 실측 대기) | W05, D04 | A 고성능 Work → B/C 저성능 Work |
| W07 | 콘텐츠·팩·이미지/음성/UI 계약 설계 | P1 / 정책 독립 계약 구체화·미응답 게이트 유지 | W01, D05~D10 조율 | 고성능 Work + 정책 조율 Chat |
| W08-A | 팩 등록·revision·immutable 파일 기반 | P1 / 독립 구현·회귀·Windows CI/artifact 검증 완료 | W05, PR #75~#78, 사용자 독립 승인 | 저성능 Work |
| W08-B | 기존 캐릭터 기본/구도 P/N 편집·로컬 편집 기록·팩 목록 UI | P1 / 완료(PR #81 병합) | W08-A 병합, Q-PACK A | 저성능 Work |
| W08-C | 기존 CPU의 명시 캐릭터팩 연결·같은 팩 갱신 | P1 / 완료(PR #82 병합) | W08-A/B 병합, Q-PACK A | 저성능 Work |
| W08 | 캐릭터·공유 후보·단계별 이미지 편집/적용 | P1 / 정책 의존 부분 대기 | W08-A, W07 관련 결정 | 저성능 Work |
| W08-D | 공유 복장 상태·포즈 원문/후보/기본값 관리 | P1 / 완료(PR #96 병합, 최종 검토는 CURRENT_STATE) | PR #93/#94 및 W08-D 설계 병합 | 저성능 Work |
| W08-M | 캐릭터 선택 신체 치수·편집·팩 원본/override | P1 / 완료(PR #93 병합, 최종 검증은 CURRENT_STATE) | Q-META A, Q-PACK A, PR #91·#92 | 저성능 Work |
| W08-S | 폴더 음향팩·단일 선택·fallback·캐릭터 음성 연결 | P1 / 완료(PR #83 병합, 최종 검증은 PR 참조) | W07 팩/event 계약, W08-A/B/C 병합, Q-PACK/Q-AUDIO/D-WIN/Q-OMAKE-VOICE | 저성능 Work |
| W-DIFF-A | 난이도 1~10 설계·격리 기술 검증·구현 인계 | P1 / 공개1수 선읽기 격리검증 완료·강도 개선/10구간 미입증 | PR #83/#84 병합, 2026-10-18 사용자 승인 | 고성능 Work |
| W-DIFF-B | 단계+게임 설정의 최종 난이도·저장·설정 UI 적용 | P1 / 정책·독립 재검증·구현·Linux 회귀 완료, 최종 Windows 근거는 제품 PR 참조 | W-DIFF-A 검토 | 저성능 Work(판단 구현 복잡 시 고성능 Work) |
| W09-A | 국 결과/화료 등급/표시 순서·복구 기술 진단 | 진단 완료 / 후속 B1 경로 수용 | PR #96/#97 및 진단 준비 문서 | 고성능 Work |
| W09-B1 | 검증된 화료 점수 adapter | 완료 / PR #102 병합 | W09-A2 | 저성능 Work |
| W09-B2 | 국 결과 사실 누적·원자 저장·복구 | 계약 준비 / 구현 전 | W09-B1 | 저성능 Work |
| W09 | 국 결과·캐릭터 고정 대사·변수 연결(최신 요구) | P1 / 대기 | W08 | 저성능 Work |
| W10 | 독립 ComfyUI·Anima adapter | P1 / 대기 | W03, W07 | 저성능 Work |
| W11 | 이벤트 랜덤 조합·생성/파일 연동 | P1 / 대기 | W06, W09, W10 | 저성능 Work |
| W11-U | 선택·대국 상세·단계 결과/뷰어 UI | P1 / 새 후속 범위 | W08 데이터, W09 event, W11 이미지 API | 저성능 Work |
| W12 | Windows 통합·팩 배포 준비 | P2 / 대기 | W11, W11-U, W08-S, D11 | 저성능 Work |

순차 경로: W01→W02→W03→W04→W05→W06.
W07 설계는 W02와 독립적으로 진행 가능하나 정책 결정은 필요하다.
W10 adapter는 W08/W09 관리 기능과 계약 확정 후 병렬 가능하다. 실행 host/API transport 파일은
W05가 먼저 확정한다. W08/W09는 공유 schema·UI를 만지므로 순차 진행한다.
병렬 작업 시 공통 models/API/main.tsx 및 기준 문서 수정 담당을 먼저 분리한다.

## 2026-10-16 중간 요구 배분 — 기존 계획보다 우선

사용자가 후속 작업에 순서대로 배분하도록 지시했다. 이번 작업은 요구/계약/인계 갱신이며 제품 구현은
아니다. Level 0~3 일대일·각 Level 3종 이미지·선택/좌석/결과 화면·팩 분류/선택/폴더 정책은 확정이다.
`D04-count`/`D10-text-voice`는 사용자 재확인으로 종료했다. 나머지 미응답 정책/기술 계약은 계속 대기하며, 원본은 REQUIREMENTS R20~R29 및 재확인 절이다.

| 순서/Task | 배분한 작업 | 완료/검증 게이트 |
|---|---|---|
| 1 W07 | 영문 배포 ID·캐릭터/SFX/BGM/음성팩 manifest/폴더 구조·공유 의존성, Level/3종 asset·prompt/event/slot·텍스트/음성 분리·기존 W06 이전과 화면 API 계약 | 4단계 × 3종 매핑, 단일 선택/default fallback·voice 무fallback, 미제공 기본팩 무음, 판 승리 범위·필드/단위·생성 시점·수명/팩 교체를 문서로 명시. 미확정은 구현 게이트로 남김 |
| W06-D 불필요 | 사용자 정정으로 기존 미완료 `<3` 유지. 미완료 3명 이상이면 완료 NPC 제외, 1~2명일 때 보충 허용 | 새 진행 코드/추가 migration 작업 없음. 기존 Tier0·stage 불변·전체 완료/omake 회귀는 후속 변경에서도 보존 |
| 2 W08 | 캐릭터 영문 ID·이름/치수·마작 정보의 기존 성향/난이도 표시 관계, 단계별 profile/full_body/CG 참조·prompt CRUD, 공유 후보, 배포 가능한 캐릭터팩 데이터/폴더 등록 기반 | 중복 ID/참조·shared 의존·팩 재인식/재시작·초기화 보존. 실제 치수나 콘텐츠를 임의 seed하지 않음. voice pack 기본/선택 ID는 이미지팩과 독립 |
| 3 W08-S | W08-A registry 재사용. SFX/BGM 각각 단일 pack 선택·지정 기본 pack·slot fallback. CPU별 기본/selected/off voice 연결과 새 character revision 기본 voice 적용. 기본 선언과 actor voice, 매 국 별도 `win`, 최종 4위 변경 후 단계별 defeat 음성 연결. Q-AUDIO A로 W06 legacy 자료/재생 보존 및 domain별 신규 선택 시 원자 전환, 최소 설정 UI에 `legacy`/`pack` 상태 표시 | 선택→기본→무음, voice 팩 자체 누락→기본 voice·유효 팩 슬롯 누락→무음·명시 off, 잘못된 actor·파일실패·동시 변경·늦은 play·중복/재접속 차단. 기존 자료·pending snapshot·reset/restart 보존, 오마케 기본 선언/화료/최종 4위 음성 유지·단계 불변. 승리 문장 목록/상황 관계는 W09 |
| 4 W09 | 치/퐁 등 간단한 공통 화면 텍스트, actor 캐릭터 선택팩 음성, 캐릭터별 Level 패배 텍스트·상황/변수 연결. 각 판 승리의 범위를 먼저 명세 | 공통 텍스트와 캐릭터 선택 voice pack 독립, 누락 음성에도 텍스트/대국 진행, 단계 변경 패배 대사의 CPU/Level 대응·중복 방지. W08-S에서 확정·연결한 오마케 기본 선언/화료/최종4위 음성 규칙과 stage/Tier/추가 진행/CG 제한 보존 |
| 5 W10→W11 | 편집 가능한 prompt 조합·독립 ComfyUI adapter, 4단계 × 3종 이미지 생성/파일/재사용/늦은 결과 연결. 결과 단계 증가 후 asset 선택 고정 | 종류·Level·CPU 식별과 캐시 분리, 기존 생성 독립 RNG/기본 게임 지속, 실제 자료/ComfyUI 출력과 mock 구분. 자동 생성 시점/seed는 미응답 정책 결정 후 |
| 6 W11-U | 캐릭터 선택: 정사각 프로필 목록·hover/선택 시 상단 정보+CG/전신. 대국: 좌석 프로필·클릭 상세. 결과: 단계 변동 애니메이션→변경 CG→전신·하단 프로필/대화, CG만 보기·줌/팬 | 이미지 API 계약 뒤 mock으로 UI 개발 가능, 실제 수용 검증은 W11 연결 후. hover/클릭/줌이 재추첨·중복 생성/정산을 일으키지 않음. 빠른 hover/이전 단계 load·reset·CG 전용 복귀·좌석/정보 대응 검사 |
| 7 W12 | 캐릭터/음향/음성팩 폴더 배포·추가 인식·이전과 Windows 통합. 사용자 제공 기본 오디오의 저장소 반영은 별도 리소스 PR | 사용자가 실제 업로드한 사운드의 파일/권리/고지·slot 대응 확인 뒤 반영. 콘텐츠 미제공 시 대기. 외부 제작 프로그램/API 통합·임의 생성/샘플 seed·미승인 Release 없음 |

W08-S와 W11-U는 기존 W08~W11을 작은 범위로 나눈 후속 구현 Task다. 새 범용 팩 매니저나
갤러리·ZIP 설치기·다운로더를 추가하는 승인이 아니다. 캐릭터팩 배포는 폴더 규격으로 준비하며
자동 ZIP export UI는 이번 요청에 포함하지 않는다. 새 기본 음향 슬롯과 화면 BGM 팩은 W06에
소급 완료 표시하지 않는다. W07에서 경로/DTO·migration·파일 수정 범위를 먼저 확정한 뒤 인계한다.

### 추가 Task의 구현 경계

- **W08-S:** W07 승인 schema/팩 registry·scanner·음향 resolver/service/API·최소 설정 UI와
  기존 `api/game.py`/renderer의 확정 SFX·voice event 연결, 관련 tests·Windows smoke. CPU 판단/규칙/
  기존 action index·정산 RNG·legacy fixture는 수정하지 않는다. 기본 사운드가 없으면 무음으로 검사한다.
- **W11-U:** 기존 CpuSelection/main/MahjongTable·선택 상세/좌석 상세/결과 연출·이미지 뷰어와
  필요한 최소 API/types/style·browser 검사. 새 신체 능력치 계산이나 마작 AI 튜닝은 하지 않는다.
- 기존 W08~W11의 최초 파일 범위 표는 아래에 보존하되, 새 중간 요구를 빠뜨린 지시로 사용하지 않는다.
  구현 시작 전에 W07 최종 계약과 Task별 파일 경계를 구체화해야 한다.

## W-DIFF-A 결과와 다음 착수 조건

기준 main `8fb9b80`에서 production/policy1/2/legacy fixture를 유지한 채
`spikes/w-diff-a`의 profile·seeded 비교·합법성/재현/격리 replay 검사를 수행했다.
명령/실측/한계는 해당 README와 CURRENT_STATE, 구체 저장/API 경계는 ARCHITECTURE를 따른다.
기존 알고리즘만으로 10개의 **행동 설정**은 만들 수 있지만 모든 인접 구간의 실전 강도가
구별된다고 입증하지 못했다. 이를 10단계 제품 구현 완료로 표시하지 않는다.

v2 보정은 준비 main `a50f13b`에서 사전 단일 후보/예산을 고정하고 독립4,608대국으로 검증했다.
낮은 레벨의 과도한 실수 감소·성향6값/비discard/fold 보존·공통입력/전체복구 재현은 확인했지만
실용 차이 권고 통과는 인접27비교 중0이며 역전/포화가 남는다. v2도 제품 채택 비권고다.
측정/한계/최종도구는 CURRENT_STATE와 `spikes/w-diff-a/calibration/README.md`를 따른다.
v1 코드·근거는 그대로 보존했다. 보정 수행을10개 강도 완료나 B 착수 승인으로 간주하지 않는다.
추가 보정/표본/탐색 범위를 임의로 확대하지 않는다. PR #86 뒤의 계속 지시는 후속 설계에
반영했으며 실제 진단/제품 착수와 구분한다. ARCHITECTURE의 판단 축 분리 설계가 최신 권고다.

v2 보정 당시 다음 조건은 REQUIREMENTS의 DIFF-* 사용자 결정과 profile 강도 보정 검토였다. 최신 다음 조건은 아래 판단 축 진단 후 현재 게이트를 따른다.
보정 자체가 새 판단 방식/범위 확대를 요구하면 먼저 별도 범위를 확정한다. B 구현 중 임의로
profile을 튜닝하거나 설정 공식을 확정하지 않는다. W08/W09 및 신체 UI는 계속 별도 범위다.

## 판단 축 진단 후 현재 게이트

준비/최신 main `e8a70b5`에서 별도8조합+원Tier2 진단1,728대국과 두 프로세스·추출27대국·
8조합 전체 JSON 복구를290.074초/전체20분 안에 완료했다. 실패/제외/재시도0.
성향6값/원 비discard/fold/000 RNG는 보존했지만 최대값 선택의 버림패 성향 표현은 크게 축소했다.
점수/순위 효과는 상대별로 달랐고 대조48지표 보정구간은0을 포함했다. 원자료/비용/한계는
`spikes/w-diff-a/decision-probe/README.md`, 실제 검증은 CURRENT_STATE를 따른다.

현재3축으로 성향을 유지하는10강도 profile을 설계할 근거가 부족하므로 추가튜닝·최적조합 채택·
holdout·B에 착수하지 않는다. 다음은 사용자의 별도 범위 승인 후 성향 표현 수용 기준·점수/순위 목표·
판단 평가/선택 확장 범위와 새 독립 검증 예산을 정하는 설계다. 이번 진단 결과를 새 탐색 구현/
DIFF-* 정책 승인으로 해석하지 않는다. 기존 v1/v2 및 제품은 보존했다.

### 2026-10-18 추가 승인 — 제한적 공개 1수 선읽기

PR #88 검토 후 사용자가 공개 정보만 이용하는 제한적1수 선읽기 **설계·격리 검증**을 승인했다.
위 진단의 새 탐색 금지는 이 별도 연구에 한해 해제한다. `task/w-diff-a-one-step`와
`spikes/w-diff-a/one-step`에서 PLAN을 측정 전에 고정하며 기존 agent/연구/제품은 보존한다.
최댓값 최종 선택 대신 성향 가중 추첨을 유지하는 단일 후보를 비교한다.
32공개관측×8성향 비용/보존 gate→통과 시3label×3context×8seed×4좌석=288대국→
추출9대국/두profile 전체 JSON 복구를 전체20분 안에 수행한다. 실패/과다 비용이면 중단한다.
완료/미검증/중단 사유는 CURRENT_STATE에 기록한다. 이번 연구로10강도·제품 채택/B·
DIFF-*·리치/울기/fold 확장·더 깊은 탐색/추가 실험을 승인하지 않는다.

수행 결과: gate/288대국/추출9대국/두profile 전체복구를112.509초에 완료했다.
계산 비용/합법성·baseline 동일성·재현은 확인했지만8seed의 강도 개선은 미입증이다.
이번 승인 연구는 완료했으며 새 계수/후보/seed/표본을 더 실행하지 않는다.
원자료와 다음 제품 게이트는 CURRENT_STATE 및 one-step README를 따른다.

## 수행한 Work 지시문 — W-DIFF-A 판단 축 진단 (2026-10-18 사용자 승인)

권장 환경: **고성능 Work**. 이번 설계로 제품 구현/B나 새 대규모 실험을 자동 승인하지 않는다.
사용자가 아래 격리 진단을 승인해 수행했다. 아래는 이번 수행 범위를 보존한 지시문이며 재실행 승인이 아니다.

```text
danhk0612/no-riichi-no-fuku의 W-DIFF-A 판단 축 진단만 수행해.
준비 main은 PR #86 병합 9cc6255이며 시작 시 최신 main·현재 branch·열린 PR·AGENTS.md와
루트 기준 문서를 다시 확인해. ARCHITECTURE의 “후속 판단 확장 설계” 전체를 따르고,
새 task/w-diff-a-decision-probe에서 별도 spikes/w-diff-a/decision-probe만 구현해.

v1/v2·원본 Tier0/1/2·policy1/2·legacy fixture·제품 파일은 보존해.
수용패수 정밀도·위험 추정 요소·후보 선택의 2수준×3축8조합과 원 Tier2 대조를 사용해.
이 조합은 L1~L10이 아니며 성능 순서/제품 profile/공식/기본값을 임의 확정하지 마.
대조 조합의 원 Tier2 동일성, 비discard/fold 보존·같은 성향6값/계수와 공개 정보 경계를 지켜.
원본 코드의 다른 오류 수정·새 선읽기/탐색·외부 AI·리치/울기/fold 정책 변경은 하지 마.

실행 전에 후보/후보순서/물리copy/동점/RNG·seed/예산/실패 조건을 PLAN에 고정해.
공통 공개 관측160개×8성향으로 합법성·대조 동일성·행동상 성향·축별 행동/비용부터 확인해.
이 단계가 실패하면 대국 비교로 넘어가지 마.
통과하면 9조합×3상대조합×seed2000..2015×4좌석=1,728대국만 실행해.
8worker 이하·전체20분 deadline·대국5,000step, PR #86 방식의 timeout/작업 종료를 유지해.
실패/지연을 보존하고 seed 제외/재시도/표본 확대/결과 후 후보 수정은 하지 마.

4좌석을 한 seed 블록으로 원 Tier2 대비 점수/순위·불확실성·성향/상대별 차이와 비용을 보고해.
최댓값 선택·정교한 위험 추정이 강하다고 미리 가정하지 마. 휴리스틱 EV는 실제 기대 득점이 아니야.
두 독립 프로세스·추출 전체 trace·각조합 JSON 저장 후 전체 잔여 대국 재현을 확인해.
현재 설정 실제 전달→복구는 저장profile 우선/새 대국만 변경설정 적용도 유지해.
production policy3/파일DB 복구 완료로 표시하지 마.

진단 결과에 따라 10profile 후보 설계가 가능한지/어느 축이 유효한지/확장 필요 여부를 보고해.
이 작업 안에서 10profile 추가 튜닝·최적 조합 채택·독립 holdout·W-DIFF-B를 시작하지 마.
DIFF-*·신체 UI·정산/CG/오디오·W08/W09는 변경하지 마.
문서/재현 근거/정확한 source hash·미검증을 갱신하고 commit/push·PR 제출까지 진행해.
직접 병합·Release/tag는 하지 마.
```

## 이전 Work 지시문 — W-DIFF-A 보정 (PR #86 수행 범위)

권장 환경: **고성능 Work**. v1 연구 기록은 보존하고 제품에 채택하지 않은 채 같은 1~10 목표의
후보 보정만 수행한다. DIFF-* 정책 선택과 독립적으로 진행 가능한 기술 검증 범위다.

```text
danhk0612/no-riichi-no-fuku의 W-DIFF-A 후보 보정만 수행해.
최신 main·열린 PR·AGENTS.md와 루트 기준 문서, PR #85 최종 검토를 확인하고
새 task/w-diff-a-profile-calibration에서 기존 spikes/w-diff-a 도구를 재사용해.

v1은 낮은 레벨 포화·일부 역전·인접 구간 불확실성이 남아 제품 채택 불가야.
기존 성향 6값은 보존하고, 과도한 균등 무작위 버림패가 성향 표현을 약화하는 문제를 줄여.
허용된 공개 관측과 기존 판단을 재사용해 후보 실수율/후보 선택 범위를 검토하고
profile version을 구분한 v2 후보를 만들어. 기존 v1 근거/원본 agent/policy1/2는 보존해.
새 탐색 엔진·외부 AI·숨은 정보 사용·게임 규칙/제품 구현 확대는 하지 마.

조절용 seed와 독립 검증 seed를 분리하고 기존 좌석 교대/seed-block 비교를 유지해.
중립뿐 아니라 기존 성향과 여러 기존 상대 조합에서 합법성·같은 seed 재현·강도와 비용을 확인해.
10개 레벨의 행동 차이와 실제 강도 차이를 구분하고 표본 내 결과에 맞춰 이름을 재정렬하지 마.
인접 평균 차이/불확실성·실용 차이의 권고 기준과 한계를 기록해. 입증이 부족하면 그대로 보고해.
예산/대국 수·seed 범위를 먼저 정해 기록하고 무제한 탐색/표본 늘리기를 하지 마.

최종 도구로 근거 자료를 다시 계산하고 별도 프로세스 재현을 확인해.
현재 설정을 실제 전달한 저장 profile 우선/새 대국 현재 설정 분기·전체 복구 검사를 보존해.
게임 설정 기본값/단계별 기본/조합 공식/특수 모드/적용 시점은 여전히 권고이며 임의 확정하지 마.
W-DIFF-B·UI/DB/정산/CG/음향/신체 정보 편집은 착수하지 마.

관련 기준 문서·재현 명령/측정/미검증을 갱신하고 commit/push·PR 제출까지 진행해.
직접 병합·Release/tag·W-DIFF-B 착수는 하지 마.
```

## 수행 기준 이력 — W-DIFF-B (최신 승인/상태는 상단 우선)

권장 환경: **저성능 Work**. 성능/보정/복합 저장 판단이 해결되지 않으면 고성능 Work로 분리한다.
아래 지시문은 구현 인계 초안이며 지금의 실행 승인이 아니다.

```text
danhk0612/no-riichi-no-fuku의 W-DIFF-B만 수행해.
최신 main·현재 branch·열린 PR·AGENTS.md와 모든 루트 기준 문서를 확인해.
W-DIFF-A PR의 최종 head/측정, REQUIREMENTS DIFF-* 실제 사용자 승인과 승인된 immutable
profile 표/강도 검증 결과를 먼저 확인해. 후보나 권고만 있고 승인/강도 보정이 없으면 구현하지 말고
남은 조건을 보고해. 이전 -1/0/+1, A의 3/6/9·기본5·실수율 표를 승인으로 간주하지 마.
기존 브랜치/다른 PR 변경을 덮지 말고 task/w-diff-b-difficulty에서 작업해.

ARCHITECTURE의 W-DIFF-A 계약을 따라 성향6값/CG stage0~3/게임 설정/최종1~10을 분리해.
순수 난이도 resolver와 승인된 versioned profile agent를 신규 policy3 경로로 구현해.
기존 Tier0/1/2와 policy1/2 RNG·종반 판정·seed*10+seat·legacy fixture·액션 순서를 고치지 마.
기존 Tier2를 재사용한다면 내부 policy2를 전달하고 새 seed 소비 규칙을 별도로 고정해.
v1 분모10 설계 예시와 v2 분모1000·후보폭/가중치/정렬 규칙을 혼합하지 마.
승인된 version별 immutable 표만 사용하며 이번 v2도 아직 채택/강도 검증 게이트를 통과하지 못했어.
10이 기존 Tier2보다 강하다고 표시하지 마. 승인된 보정표/정의와 실제 행동 차이를 확인해.

CpuChoice에 nullable difficulty_snapshot만 추가하고 신규 local 대국만 policy3로 시작해.
rules_snapshot version2와 effective_tier0/1/2는 기존 진행/호환 의미로 유지해.
GameSetting key local_cpu_difficulty의 version/revision/setting, local GET/PUT /api/local/difficulty를
구현해. 기존 JSON 열/key-value로 가능하면 새 schema migration/테이블은 만들지 마.
현재 공식/프로필/설정 revision/reason/level/파라미터·성향·stage를 대국 시작 시 고정해.
현재 대국/구 저장은 설정 변경 뒤에도 재계산하지 마. unknown/malformed 새 snapshot은 명시 오류로
멈추고 최신/기본/legacy로 대체하거나 사용자 기록을 rewrite하지 마.

writer에서 설정과 start를 직렬화하고 revision 검사→commit 후 응답을 지켜.
GET은 읽기만, 저장 실패는 이전 설정/active game 보존, start 실패는 cache eviction/원본 복구.
설정 변경이 기존 game/agent/socket/콘텐츠 RNG를 재생성하지 않게 해.
완료 CPU 보충/omake 우선순위와 초기화 뒤 설정 보존은 승인된 DIFF-MODE/TIMING을 따라.
정산/CG unlock/명단/HP 없음/엔딩·음향·voice 동작은 변경하지 마.

선택 preview는 서버 resolve, 현재 대국 표시는 저장 snapshot에서 API/WS로 제공해.
기존 화면에 최소 난이도1~10 선택·저장/다음 대국 안내와 최종 난이도 표시만 넣어.
CG Level/성향/최종 난이도를 별도 명칭으로 표시해. legacy는 가짜 1~10으로 환산하지 마.
기존 generation/load token으로 늦은 응답을 막고 표시 숫자 때문에 CPU/CG를 다시 선택하지 마.

파일 범위: backend/app/mahjong의 새 profile agent, services/game_setup.py/local_play.py/
game_registry.py 및 최소 difficulty service, schemas/game.py와 local 전용 schema/router,
local_runtime.py의 router 연결, frontend/src/api.ts/game/types.ts/main.tsx/CpuSelection.tsx와
최소 설정 component/style, 관련 backend/browser/Windows smoke와 기준 문서만 변경해.
기존 agent/legacy fixture/정산·음향 알고리즘/신체 UI/팩·생성 기능 수정은 범위 밖이야.

검증: 승인된 resolver 전 조합(stage0~3×설정1~10×progress/omake), 보충 자격·특수 모드,
6성향 불변·최종난이도/CG 독립, 새 profile 전 레벨 합법성·동일 seed/action trace golden,
설정 저장/start 경쟁·commit 실패/응답 유실·reset 보존, 12행동 후 변경/재시작과 완료 결과 동일,
pre-versioned golden 매 턴·policy1/2 원본·unknown version 거절·완료/cancelled 보존을 확인해.
기존 backend unittest/대사 pytest/frontend build·관련 browser 및 정확한 수정 SHA의 W04/W05
Windows CI와 다운로드 artifact source/ZIP hash·packaged 설정/복구 smoke를 확인해.
CI/Windows hosted/개인 PC·실전 강도 표본을 구분해. 부족한 검증을 완료로 기록하지 마.

REQUIREMENTS/ARCHITECTURE/CURRENT_STATE/TASKS와 필요한 사용자 README를 실제 결과대로 갱신해.
commit/push·PR 제출/관련 CI는 허용한다. 직접 병합·Release/tag·후속 Task 착수,
실제/더미 CG·음향 생성·사용자 자료 수정/삭제·ComfyUI 실행은 하지 마.
```

## 이전 입력 지시문 — W-DIFF-A 난이도 확장 설계·격리 검증

```text
danhk0612/no-riichi-no-fuku의 W-DIFF-A만 수행해.
준비 main은 PR #83 병합 467c706이다. 시작 시 최신 main·현재 브랜치·열린 PR을 확인해.
AGENTS.md와 루트 기준 문서를 읽고 task/w-diff-a-difficulty-spike에서 작업해.

확정 목표:
- 성향 6값은 캐릭터 고유값. 캐릭터 stage/CG Level 0~3은 유지.
- 최종 CPU 난이도는 캐릭터 단계의 기본 난이도와 게임 설정을 조합한 1~10.
- 기존 Tier 0~2를 기반으로 판단 설정을 세분화하고 실질 차이를 검증.
- 완료 보충의 매우 쉬움·엔딩 후 최고 난이도 정책은 임의 폐기하지 않음.
- Q-META 신체 A는 별도 승인됐지만 이번 Task에서는 편집 UI/DB를 구현하지 않음.

기존 알고리즘의 실제 성향/판단/난수 사용과 선택·복구 경계를 조사해.
격리 spikes/w-diff-a에서 profile 후보와 seeded 비교 도구를 만들고
레벨별 조절 지점·합법성·동일 입력 재현성·CPU 시간·표본 순위/점수를 검증해.
기존 production agent/policy 1/2와 legacy fixture를 고치지 마.
숫자만 10개로 분할하거나 기존 최고보다 강하다고 검증 없이 표시하지 마.

게임 설정 범위/기본값·단계별 기본 레벨·조합 공식·특수 모드 우선순위·변경 적용 시점은
구체 예시/권고와 사용자 결정 항목으로 제시해. 이전 -1/0/+1 제안은 승인되지 않았어.
특히 진행 중 대국 snapshot, 구 저장 복구, 새 profile/policy version 경계와
화면에 표시할 최종 난이도의 의미를 ARCHITECTURE에 구체화해.

반복 대국 표본 수/seed/좌석 교대·비용·한계를 기록하고 핵심 기존 회귀를 확인해.
제품 설정/DB/CG/정산/음향/콘텐츠 생성은 변경하지 마.
REQUIREMENTS/ARCHITECTURE/CURRENT_STATE/TASKS를 정리하고
잔여 결정 후 저성능 Work에서 독립 수행할 W-DIFF-B 구현 지시문을 작성해.
commit/push·PR 제출까지 진행하되 직접 병합·Release/tag·W-DIFF-B 착수는 하지 마.
```

이 Task는 복합 CPU/저장 호환 설계가 필요하므로 고성능 Work를 사용한다. W08의 나머지
metadata/공유 후보·W09·ComfyUI 작업을 이번 범위에 함께 넣지 않는다.

## Task 명세

### W01 — 기존 기능·회귀 기준 확정

- 결과: `5762267e2366fa5bdbdd69bc6f38672d141dcbc8`에서 unittest 72개, 대사 pytest 10개,
  frontend npm ci/build 통과. browser 4개는 Chromium 부재로 미검증. 코드→검사 대응·policy 1/2·
  legacy 보존·검증 누락/후속 조건은 [CURRENT_STATE.md](CURRENT_STATE.md)에 기록했다. 제품 변경 없음.

- 목적: 전환 중 보존해야 할 실제 동작과 재현 검증을 저성능 Work가 독립 사용하도록 정리.
- 범위: 기존 unittest·browser/live integration·legacy fixture를 읽고 실행 가능한 기존 검사 재현,
  규칙/CPU/HP/stage/복구/정산/CG 실패의 코드→검사 대응표를 CURRENT_STATE에 간결히 반영.
  누락은 기존 검사로 보장되지 않는 항목으로 기록. 실제 결함 수정은 별도 Task로 제안.
- 선행: W00 문서 PR 반영 또는 그 정확한 head에서 시작한다는 명시.
- 완료: 정확한 baseline SHA, 실행 명령/환경/결과/미검증과 보존 불변조건이 재현 가능;
  policy 1/2·seed/action replay, 중복 정산, CPU 부족/HP 0 보류 조건이 빠짐없이 인계됨.
- 금지: 제품 코드·의존성·migration·CPU 가중치·규칙·진행 정책 변경, 이미지 생성/바이너리,
  Windows 구현, 본 Task를 빌드 오류 수정으로 확대, 직접 병합/배포.
- 환경: 저성능 Work. 설계 선택 없이 코드/테스트 대조·기존 검사 실행·Git/문서 작업 중심.

### W02 — Windows 실행·엔진 번들 기술 검증

- 결과: code `a9268d4b3b5eed3b55b8b40e2f06bbf28a549cb5`, Windows Server 2022 x64 CI
  [38567208066](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38567208066) 전체 통과.
  Python 3.12.10/RiichiEnv 0.4.8 frozen + Electron 44.7.2, 한글/공백 ZIP 해제·health·same-origin
  REST/WS 108행동·12행동 복구·완료 정산 보존·포트 충돌/owned child 종료 확인.
  원본 source/frozen 72 unittest·10 대사 pytest 및 기존 browser 4개 통과.
  격리 spike/전용 CI뿐이며 제품 통합·기술 채택 없음. 정확한 hash/용량/조건은 CURRENT_STATE.
  clean Windows 10/11·OS 인터넷 차단·사용자 X 클릭/강제 종료 등은 미검증;
  사용자 증거는 PR #59 또는 Work 채팅, 실행법은 `spikes/w02/README.md`.

- 목적: 기존 엔진이 Python 사전 설치 없는 Windows에서 재사용 가능한지 증거 확보.
- 범위: 격리 spike에서 RiichiEnv 0.4.8/Python 3.12 x64 번들, Electron 우선 shell,
  대안의 WebView2 오프라인 요구 비교. dependency package 발견 오류, native DLL·migration/seed
  포함, 같은 origin REST/WS, ready/port/owned process 종료 검증. 제품 구조를 확정하지 않음.
- 선행: W01, Windows 실행 환경 또는 사용자 실기 결과 경로. 없는 환경은 미검증으로 남김.
- 완료: 실제 Windows 압축 해제 기동·health·동풍전·저장 재시작 증거 또는 정확한 차단과 재개 조건,
  후보별 재사용 범위/배포 부담/변경 파일 경계 및 W03 권고. 인터넷 차단 조건 구분.
- 금지: 라이브 사용자 DB/미디어 수정, 본 게임 재작성, 정식 패키징/Release, 자동 기술 확정.
- 환경: 고성능 Work. native/host/runtime/저장 경계가 얽힌 최초 검증.

### W03 — 실행·저장·프로필 정책 확정

- 결과: 2026-10-14 사용자 승인으로 여섯 정책 확정. REQUIREMENTS/ARCHITECTURE의
  로컬 저장·권한·writer·host 경계 계약을 따른다. 제품은 아직 미구현이다. 지원 OS/배포용
  Python patch 공급 조건은 W05 준비에서 확인하고 W12 전 확정한다.

- 목적: W04/W05가 설계 선택 없이 구현할 수 있도록 사용자 결정 확보.
- 범위: D01~D03와 관리 UI 통합/분리(D09), 지원 Windows·배포/데이터 경로·인증/프로필/슬롯·
  기존 데이터 이전 범위를 선택지/영향으로 제시. 채택된 실행/저장/수명/보안 계약을 문서화.
- 선행: W02 실제 증거/제약.
- 완료: 사용자 결정과 구조 경계·검증 기준·보류 기능·각 구현 파일 범위가 명시됨.
- 금지: 사용자 대신 기술/삭제/이전 정책 확정, 제품 기능 구현.
- 환경: 고성능 Chat. 좁혀진 선택의 집중 검토/상호작용. 복합 재설계 필요 시 고성능 Work.

### W04 — 로컬 저장·복구 기반 전환

- 목적: 확정 로컬 저장에서 행동 commit과 복구·진행 보존을 유지.
- 범위: W03 저장/프로필 계약 구현, Alembic/bootstrap/paths, 로컬 writer/동시 요청 제어,
  외래키/index/rollback·마지막 행동 후 정산 재시작, policy 1/2. 기존 데이터 이전은 승인 범위만.
- 선행: W03 확정 정책/구현 계약, W01 baseline. Windows UI/번들 버전 확정은 W05에서 다룸.
- 완료: schema/migration 재현, 진행/세션 동등 복구와 exactly-once, 동시·commit 실패 회귀 통과;
  사용자 자료 보존/전환 실패 재개 기준. 전원 차단 검증은 실측한 범위만 기록.
- 금지: CPU/룰/HP·완료 규칙, 공유 콘텐츠, ComfyUI, 미승인 기존 DB 덮어쓰기.
- 환경: 저성능 Work. ARCHITECTURE의 확정 경계로 구현하고 계약을 바꿔야 하면 별도 검토.
- 기존 검증 이력: PR #61 code SHA `3081dc56a2be95dd30ce0fa78a413da9b4bfeb29`에서
  Linux backend unittest 78/대사 pytest 10/frontend build와 Windows Server 2022 x64 hosted
  CI run [38572718064](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38572718064)이
  통과했다. artifact `11897978928`의 source SHA/test 로그 확인은 CURRENT_STATE에 기록돼 있다.
  이후 PR head `70c6d8bdc031803a713a324889e2f241c95750ac`도 Windows run 38573281946 및 기존
  78/10 성공이었으나 2026-10-15 검토에서 이름 저장·capability·read/write lock 결함이 재현됐다.
  이 기존 성공 이력은 보존하되 결함 보완/현재 수정 SHA의 검증으로 간주하지 않는다.
- 보완 검증: local profile의 PATCH→GET→별도 DB→runtime 재시작, REST/member/admin 및 WS의
  malformed capability 거절/4401, 기본 engine 동작 보존·local read/write 경계, 동시 writer/stale
  action/admin write, 파일 DB 정산 commit 실패 rollback/cache eviction/재기동 exactly-once를 추가한다.
  Linux Python 3.12.14 현재 검사 backend unittest 81, 대사 pytest 10, TypeScript/Vite build가
  통과했다. 정확한 code SHA `d46782bef4947ff448b2d40555ac4b387b2bc25a`의 Windows Server 2022
  x64 hosted run [38659727577](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38659727577),
  unittest 81/pytest 10/frontend build가 통과했다. artifact ID `11938706685` source SHA 및 ZIP
  SHA256 `c4f778a5cb4fcf51bc73ac59404dd2043c14968c6b77ca2956cb508d0e335bff` 검증은 CURRENT_STATE에 있다.
  기존 PR #61은 열린 상태다. Windows 사용자 UI·LocalAppData·OS 인터넷 차단·전원 차단 검증은 미실행이다.

### W05 — Windows shell·오프라인 게임 통합

- 목적: 기본 게임을 한 Windows 프로그램에서 실행.
- 범위: W03 확정 host에 React build/로컬 엔진 묶기, 기동 준비·포트·owned child 종료·오류 표시,
  확정 프로필 진입·복구 연결. 기존 테이블과 transport를 우선 재사용.
- 선행: W04, W02 증거와 W03 계약.
- 완료: Python/Node/Docker/PostgreSQL/ComfyUI 사전 설치와 인터넷 없이 기본 대국·결과·
  재실행 복구, UI 종료 시 owned 프로세스 처리, 사용자 데이터 보존을 실제 Windows에서 검증.
- 금지: UI 전체 재설계, ComfyUI 자동 기동, 다른 프로세스 종료, 진행 정책 변경, Release.
- 환경: 저성능 Work. 승인된 실행 계약 구현; 범위 밖 구조 판단은 인계.

### W06 — 고정 참가 명단·진행/오마케·초기화·사운드

REQUIREMENTS D04/R16~R19가 확정 정책이다. CPU HP는 별도 시스템이 아니며 기존 stage를 유지한다.
제품 구현은 저장/정산/초기화·엔딩/사운드의 계약을 좁힌 뒤 순차 진행한다.

#### W06-A — 저장·복구·리소스 구현 계약 설계 (검토 통과)

- 결과: main `e48aae9` 소스와 저장/정산/UI를 대조하고 ARCHITECTURE의 W06-A 계약을 작성했다.
  제품·migration 실행·새 Windows 검증은 없다. 2026-10-15 재검토에서 최초 명단 후보 API와
  local mutable HTTP의 response 전 commit/실패 검증을 명확히 했다. B는 A 병합 후 착수한다.
- 환경: 고성능 Work. 제품 코드 변경 없이 문서 설계/작업 분해/소스 대조.
- 범위: 게임 공통 자료와 고정 참가 명단·한 플레이의 진행 상태·대국 snapshot/action log·상시 사운드
  선택 설정의 최소 관계, schema/migration/API/UI, DB writer/transaction/cache 경계.
  초기화 확인/현재 대국 종료/이전 socket·요청 차단/자료 보존, 기존 저장 호환,
  엔딩 pending/표시/오마케 전환과 재접속·리소스 참조/재생 계약. 등록 CPU 삭제/비활성화가
  고정 명단·전체 완료 판정에 미치는 처리도 사용자 정책을 보존하는 최소 방식으로 설계한다.
- 완료: ARCHITECTURE에 구체 필드/관계·요청/응답·transaction/기존 저장 전환과 상태별 예시,
  TASKS에 독립적인 B/C 파일 범위·의존·검증·전체 지시문. 미확정 콘텐츠 D05~D11과 분리한다.
- 금지: 제품 구현/migration 실행, 무관 구조 정리, 실제 CG/음악/대사·더미 콘텐츠 생성,
  사용자 자료 초기화·삭제, 외부 오디오 생성 API/ComfyUI 기능, Release/tag·직접 병합.

#### W06-B — 진행·명단·초기화 구현 (A 검토 후)

- 환경: 저성능 Work. W06-A에서 확정한 최소 코드·migration/UI/API·회귀 구현.
- 범위: 참가 명단 확정/고정 및 대국 상대 선택, 플레이어 HP 제거, 완료 CPU Tier 0 보충,
  모든 참가 CPU 완료 판정·엔딩/오마케 상태, 오마케 Tier 2/진행·추가 이벤트 없음,
  확정 초기화와 저장/기존 세션 호환. 엔딩/사운드 실제 재생 연결은 C 계약과 분리한다.
- 완료(당시 계약): 미완료 인원 3/2/1/0, 참가 명단 밖 CPU 배제, 사람 4위 후 계속 플레이,
  완료 전 보충 CPU 승패 무변동/대사와 오마케 추가 진행/CG 이벤트 억제, 정확히 한 번의 완료 판정.
  2026-10-16 결정으로 오마케 기본 선언/화료/최종4위 대사는 재생한다.
  초기화 동시 요청·오래된 socket/지연 응답 차단·재기동 및 자료 보존 검사.
  기존 policy 1/2/legacy·local writer/정산 실패 회귀·정확한 SHA Windows CI/artifact 확인.
- 실행 기록: 2026-10-15 기준 main `24ed576`; 구현은 `task/w06-b-progression` PR로 제출한다.
  Linux backend unittest 90개, 대사 pytest 10개, frontend build와 임시 자료 보존 검사가 통과했다.
  Windows Server 2022 exact code head `d2740c80a29b694b1f2f00889db46c2cdf19a2a2`의 CI run
  [38701271329](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38701271329)와 packaged smoke가 통과했다.
  artifact source SHA와 API ZIP digest는 CURRENT_STATE의 W06-B 항목에 기록한다.

#### W06-C — 사운드 자료·설정 및 엔딩 리소스 연결 (A 및 B 검토 후)

- 환경: 저성능 Work. A의 등록/파일/API/재생 계약을 구현.
- 범위: 효과음 세트/배경음 목록 등록·관리, 설정의 상시 효과음 세트/사용 BGM 목록 변경,
  엔딩 CG/음악/대사 참조와 재생·완료 후 오마케 진입. 기존 캐릭터 고정 데이터·공유 후보
  관리 UI(W08)를 미리 전부 구현하지 않는다. 최소 등록/참조 경계는 A가 명시한다.
- 완료: 선택 설정 재시작 보존, CPU 명단과 독립 변경, 누락 리소스의 확정 처리,
  엔딩→오마케의 재접속/재기동·중복 이벤트 억제, 초기화 후 공통 등록/파일 보존.
  실제 제공 리소스 검증과 mock/미등록 경로를 구분한다. 실제 자료 없으면 실측 대기는 명시한다.
- 금지: 콘텐츠/모델/오디오 생성, 외부 생성 서비스 통합, 임의 seed/사용자 파일 삭제,
  새로운 플레이어/CPU HP·Tier 튜닝·대국 인원 변경·이미지 Level 자동 대응·ComfyUI 구현.

### W06-B/C 파일·검증 인계

계약 원본은 ARCHITECTURE의 W06-A 절이다. 아래는 구현 경계이며 별도 정책을 추가하지 않는다.

| Task | 수정/추가 가능한 파일 범위 | 선행/분리 |
|---|---|---|
| B | `backend/app/db/models/`의 local play/roster 및 session 모델·exports, `backend/alembic/versions/`의 0004 다음 migration, `services/game_setup.py`, `game_result.py`, `game_registry.py`, 새 `services/local_play.py`, `api/game.py`, 새 `api/local_play.py`, `schemas/game.py`, 새 `schemas/local_play.py`, `local_runtime.py`, `services/admin.py`의 명단 참조 보호 | A 검토/병합. local 경로만 새 규칙, 웹 legacy 유지. CPU agent 파일 수정/튜닝 금지 |
| B UI/검사 | `frontend/src/main.tsx`, `api.ts`, `CpuSelection.tsx`, `game/types.ts`, `game/MahjongTable.tsx`, 필요한 최소 `style.css`/새 명단·초기화·미등록 엔딩 컴포넌트, `backend/tests/` 관련 검사, `frontend/tests/`, `desktop/main.cjs`의 기존 smoke 경로, 기존 Windows workflow의 B branch trigger/검증 범위 | host 수명/보안 변경은 제외. 현재 smoke는 main.cjs 내부 구현이며 별도 파일로 분리하지 않음 |
| C | 새 `db/models/` media/effect-set/track 및 exports·B 다음 migration, 새 `services/local_media.py`, `local_sound.py`, 새 `api/local_sound.py`, `schemas/local_sound.py`, `local_runtime.py` route 연결, B `services/local_play.py`의 ending payload resolve, `api/game.py`의 commit 후 기본 SFX 전달 | B 검토/병합. B의 세대·정산·ack 계약 재작성 금지 |
| C UI/검사 | `frontend/src/api.ts`, `main.tsx`, `game/types.ts`, 새 최소 사운드/엔딩 설정·재생 컴포넌트, 필요한 style, 관련 backend/frontend tests·desktop smoke·Windows workflow, README | 최소 관리 화면만. W08 캐릭터/공유 후보 편집·외부 서비스·새 SFX hook 제외 |
| 공통 문서 | `ARCHITECTURE.md`, `CURRENT_STATE.md`, `TASKS.md` | 실제 구현/검증과 차이를 기록, 기존 검증 이력 보존 |

`db/session.py`의 W04 writer·인증·desktop/quit 계약은 우선 재사용한다. 계약상 불가능한 변경이
필요하면 해당 지점만 근거/영향을 보고하고 범위 밖 수정으로 우회하지 않는다.

| Task | 반드시 추가/보존할 검증 |
|---|---|
| B | 당시 완료 검사: 최소3·고정 명단/중복 확정·active 변경 참조 보호·명단 밖/추가 CPU 배제, 미완료 3/2/1/0·stage와 effective tier, 사람4위 HP 불변·보충CPU 1/4위 대사·오마케 추가 진행/CG 억제. 2026-10-16 결정으로 승패 대사 억제 계약은 수정됨 |
| B 저장 | 0004 파일 DB upgrade/반복 bootstrap/legacy active·completed/HP0·원 snapshot/policy1/2/108행동, 정산 commit 실패/rollback/evict/재시작, 두 start/두 reset/action·정산·reset 경쟁, stale WS/캐시/지연 응답 차단, cancelled/recent 필터, 초기화 자료 hash 보존 |
| B 엔딩 | 전체 완료/명단 확정 시 이미 완료인 경우, pending event 1개, 표시 중 재시작/중복 ack/ack 응답 유실·다른 event 거절, 미등록 안내로 omake 진입 |
| C | format/size/path/auth·한글/공백 파일명·업로드/metadata commit 실패 기존 파일 불변, 등록/설정 재시작·독립 변경/비활성 참조·빈 목록, B reset 후 등록/설정/파일 hash 보존 |
| C 표시 | event 중복·replay 무음·대사 없는 SFX·오마케 기본 SFX, BGM 목록 변경/엔딩 음악 분리, pending snapshot 불변·누락/실패/autoplay 거절·늦은 audio callback·명시 ack 후 omake 복구 |
| B/C 공통 | backend unittest·대사 pytest·frontend build·관련 browser/live-game·W04 writer/인증/정산 실패·W05 renderer/일반 종료/재시작. 정확한 head SHA Windows hosted CI/artifact source와 ZIP hash. 개인 PC/전원 차단은 별도 미검증으로 표시 |

기존 W05 workflow의 push trigger는 `task/w05-windows-shell`뿐이다. B/C에서 해당 작업 branch도
검증하도록 최소 확장하고 PR workflow의 exact head checkout을 유지한다. packaged smoke는 `desktop/main.cjs` 내부에 있다. 기존 smoke를 갱신하며 새 중복 smoke를 만들지 않는다.
C에 실제 제공 리소스가 없으면 mock/미등록 검사와 실제 CG·음악 출력 미검증(D11)을 분리한다.

### W07 — 콘텐츠·이미지 이벤트 계약 설계

- 목적: R07~R14를 구현 가능한 데이터/선택/표시 계약으로 좁힘.
- 범위: character P/N, 공통 Level/ID/label, 후보 참조, 상황→대사, 변수·삭제/빈 후보·신규 포함,
  event→상황, stage/Level·재렌더/복구·생성 지연·cache 및 파일 보존, 모델/LoRA·UI 경계 설계.
- 선행: W01. D05~D10은 사용자와 결정하며 미해결 경계는 구현 불가로 표시.
- 완료: 승인된 schema/API/UI 책임·migration/구 seed 호환·선택과 표시 불변조건·검증 예제가
  ARCHITECTURE/REQUIREMENTS에 있고 W08~W11 구현에 임의 정책 결정이 필요하지 않음.
- 금지: 실제 콘텐츠/CG 생성, 제품 구현, 규칙/CPU 정책 변경, 관리 부가 기능 추가.
- 환경: 고성능 Work, 좁은 사용자 정책 조율은 고성능 Chat.

### W07 정책 조율 결과와 후속 실행 지시

main `eaaae74`에서 #72~#74 병합과 열린 Docker 문서 #35를 확인했다.
ARCHITECTURE의 “W07 구체 기술 계약”에 팩 v1·ID/폴더/scan·immutable 파일,
Level×kind·DTO·event ordinal·W06 보존과 조건부 생성/job 계약을 구체화했다.
REQUIREMENTS의 기존 미응답 질문 및 D-WIN/Q-META/Q-IMAGE/Q-FRAME/Q-AUDIO/Q-OMAKE-VOICE/Q-LEGACY는
사용자 응답 대기다. Q-PACK은 사용자 위임에 따라 A로 결정했으며 재질문하지 않는다. 단 D-DEFAULT·D06-b A·D06-c 삭제 처리는 후속 사용자 응답으로 확정됐다.
D06-a A(신규 명시 연결)/D06-d A(같은 Level 허용 후보 조합)와 외모/상의 속옷/하의 속옷 P/N도 확정됐다.
Q-UNDER도 확정됐다: 1 상의 겉옷 탈의·브래지어 노출/하의 겉옷 유지, 2 겉옷 없이 속옷 세트, 3 전체 탈의.
Level 이동/소속 변경 및 다른 미응답 정책은 계속 대기한다.
**W07 전체 미완료, 아래 후속은 구현 지시 템플릿이며 실행 승인이 아니다.**

시스템 구축을 우선하며 실제 프롬프트 작성은 기능 검증에 필요한 최소 범위만 수행한다.
콘텐츠 문구 완성을 W08/W10/W11의 시스템 구현 선행으로 요구하지 않는다.
편집·저장·연결·조합·전달을 검증하고 실제 문구 작성/보강은 차후 사용자/다른 AI에게 맡긴다.
새 AI 작성 기능/임의 모델 보정 태그·콘텐츠 seed를 추가하지 않는다.

W08은 외모/상의 속옷/하의 속옷 P/N 독립 저장·편집과 명시 후보 집합을 구현 범위로 삼는다.
겉옷은 공유 복장 상태에서 정의하며 기존 기본 복장 문구를 속옷으로 자동 이전하지 않는다.
새 공유 항목 추가 시 기존 후보 불변, 같은 Level 허용 후보 조합, 상황별 추가 제약 없음도 검사한다.
W10 builder/W11 입력 snapshot·cache는 적용 속옷 부분과 각 P/N revision을 반영하고
미적용 부분은 P/N 모두 제외한다. Level 1 브래지어/하의 겉옷 유지, Level 2 속옷 세트만,
Level 3 양쪽 속옷 P/N 제외의 누적 상태와 일치하도록 복장 상태/조합 검증에 반영한다.
정확한 조합 순서는 D07-a/Q-FRAME 대기이며 실제 프롬프트·seed를 만들지 않는다.
W08은 지정 기본 참조·미설정/대상 누락 resolve·기본까지 없을 때 출력 생략과 삭제 영향 목록 확인→
자동 해제/기본 재연결의 원자 commit을 계약에 포함한다. W08-S는 선택 팩 자체 없음→지정 기본팩과
유효 voice 팩 슬롯 없음→무음을 구분한다. 명시 off·명단 고정·과거 snapshot/파일을 보존하며
기본 자료 배포 목표만으로 미제공 리소스를 seed하지 않는다. 검증에는 기본값 없음/자기 삭제/
영향 변경 재확인/commit 실패 rollback/폴더 제거 뒤 유효 복사본을 포함한다.

공통 시작 지시: 대상 저장소의 최신 main·현재 branch·열린 PR·AGENTS와 루트 기준 문서를 읽는다.
해당 Task의 정책 응답이 REQUIREMENTS에 기록되고 ARCHITECTURE 조건부 필드가 최종 계약으로
갱신됐는지 확인한다. 누락되면 그 의존 범위는 착수하지 말고 질문 ID를 보고한다.
허용된 Task만 `task/<id>-<scope>`에서 구현하고 commit/push·PR까지 제출한다.
CPU/규칙/seed/action replay·legacy fixture 변경, 실콘텐츠 생성·사용자 자료 삭제,
직접 병합·Release/tag는 금지한다. 문서에 미검증을 완료로 쓰지 않는다. 권장 환경은 저성능 Work다.

| Task | 선행 정책·병합 게이트 | 허용 파일 범위·구체 구현 지시 | 완료 검증 |
|---|---|---|---|
| W08 | W05·W07 최종 계약, D05-c/D06 전체/D07-b/D10-a, Q-META/Q-PACK/Q-LEGACY | `db/models/`·exports·head 다음 additive migration, 새 `services/content_packs.py`/`character_content.py`·`schemas/local_content.py`·`api/local_content.py`, `local_runtime.py` 등록, `services/admin.py` 참조 보호. 기존 CpuSelection/main/api와 새 최소 캐릭터/공유 편집 UI. v1 scanner·stable ID·4단계 3종 참조/P/N·공유 관계·후보·메타데이터·voice 기본 참조 구현. bootstrap은 승인 legacy 대응만, 모델 override는 승인 범위만. generation/event resolver 구현 금지 | ID/중복/버전/의존 누락/경로·불완전 scan·metadata 실패·반복 upgrade/bootstrap; Level/kind/FK·후보/삭제 승인 사례·편집/재시작/reset 보존·기존 PK/파일 hash |
| W08-S | W08-A/B/C 병합, Q-PACK/Q-AUDIO/D-WIN/Q-OMAKE-VOICE 확정, D-WIN의 화료음성 연결과 최종 1위 미추가 | W08-A registry·immutable media 참조 재사용. audio/voice selection API·최소 UI·재생 resolver와 승인 hook을 구현. 기본 선언 다음 `win`, final 4th는 변경 후 `defeat_stage_N`(오마케/stage3도 stage3), 기존 보충 CPU `match_first` 대사는 기존 계약만 유지하고 최종4위 `match_last` 대신 단계별 대사를 사용. 새 동풍전 최종 1위 대사는 추가하지 않음. 새 `win` voice slot 등록 검증을 허용하며 legacy W06 플레이어·자료는 보존. shared dialogue text/context list는 W09. CPU 판단/규칙/seed/replay 계약 변경 금지 | W06 selection/file/pending/reset/restart 호환·Q-AUDIO 원자 전환, per-domain single pac