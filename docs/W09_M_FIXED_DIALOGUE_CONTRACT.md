# W09-M — 캐릭터 고정 대사 관리·기존 문구 명시 연결 계약

기준: main `18abe925fceb228db8f30d452761766939256b8a`, 2026-10-30.
사용자 Q-LEGACY **A** 응답을 반영한다. 이 문서는 관리 기능 단독 구현 계약이다.
W09-C1은 이미 수용됐다. 과거 C1 재검토 지시는 다시 수행하지 않는다.

## 1. 범위와 실제 코드

현재 `CpuDialogue`는 정수 PK, cpu_character_id, event_key, text, active의 여러 행이며
`DialogueSelector`는 활성 행에서 무작위 선택한다. seed에도 동일 CPU/event의 복수 문구가 있다.
이 경로를 고정 대사 저장소로 바꾸면 웹/legacy와 저장 결과가 변하므로 그대로 보존한다.

`CharacterContent`는 P/N·측정값·팩 적용 revision/편집 기록을 관리한다.
`LocalContentPanel`의 기존 캐릭터 설정에 고정 대사 관리 영역을 추가하되 별도 revision으로 저장한다.
이미지 프롬프트·음성팩·공유 상황 데이터와 섞지 않는다. 현재 캐릭터팩 v1에는 새 대사 필드를 추가하지 않는다.

구현 대상은 CPU 소유의 `win`, `defeat_stage_1`, `defeat_stage_2`, `defeat_stage_3`,
기존 보충 승리용 `match_first` 다섯 슬롯의 조회·명시 편집·기존 문구 선택 연결이다.
`match_first` 관리는 기존 계약 보존용이며 일반 동풍전 1위 대사를 신설하는 것이 아니다.
ron/tsumo/chi/pon 등 공통 선언 텍스트를 캐릭터 고정 대사 슬롯으로 추가하지 않는다.

**이번에 게임 이벤트/결과 화면에 새 슬롯을 연결하지 않는다.**
현재 local/web 선언·화료·정산·음성 동작, RNG 소비, C1 unbound 결과 및 과거 presentation은 그대로다.
관리 자료의 미설정은 이전 거부나 출력 정책의 확정이 아니다. 실제 새 대국 연결·빈 슬롯 출력은
후속 C2 계약에서 기존 기본값 정책과 함께 명시한다. D05-c와 이미지 정책은 M의 선행이 아니다.

## 2. 저장 계약

최신 Alembic head를 확인하여 0013 다음 additive migration 하나를 둔다.
새 `CharacterFixedDialogue` 모델의 `character_fixed_dialogues` 테이블:
- `cpu_id`: CPU FK/PK, 기존 캐릭터 소유·삭제 관례 사용.
- `revision`: 정수 1 이상. 행이 없으면 API revision=0.
- `slots`: JSON, 아래 다섯 키 중 명시 저장한 슬롯만 포함.
- 기존 TimestampMixin 사용. 다른 테이블/기존 행에는 backfill하지 않는다.

슬롯 값:
`{text: string, origin: null | {legacy_dialogue_id: int, event_key: string, text: string}}`.
origin은 연결 당시 출처 사본이다. 수정 가능한 CpuDialogue를 매번 따라가 표시할 live 참조가 아니다.
선택한 기존 행의 ID와 원문을 보존하고 text를 최초 고정값으로 가져온다.
이후 직접 편집해도 origin은 출처로 남으며 현재 text와 원본을 구분해 보여 준다.
원본 삭제/수정이 고정값을 잃게 하는 FK를 만들지 않는다. 기존 admin 삭제 의미도 바꾸지 않는다.
원 행/과거 완료 presentation/파일은 이번 기능에서 수정·삭제하지 않는다.

미설정(키 없음)과 직접 빈 문자열로 저장한 값은 다르다. null text/임의 타입은 거절한다.
직접 입력한 슬롯은 origin=null이며 기존 origin이 있는 슬롯을 편집할 때 origin은 유지한다.
GET/시작/bootstrap/팩 재검색/팩 적용은 고정 대사를 생성·이전·수정하지 않는다.
팩 갱신은 별도 고정 대사 revision에 영향을 주지 않고, 반대도 동일하다.
진행 reset은 자료이므로 고정 대사와 출처를 보존한다.

## 3. API·원자성

기존 local character router의 인증/로컬 등록·SQLite writer intent를 재사용한다.
웹 관리자 API/공개 endpoint를 새로 열지 않는다.

| 인터페이스 | 계약 |
|---|---|
| GET `/api/local/characters/{cpu_id}/fixed-dialogues` | schema_version=1, cpu_id, revision, slots. 행 없으면 revision0/slots{}. 무쓰기 |
| GET `/api/local/characters/{cpu_id}/fixed-dialogue-candidates` | 해당 CPU의 위 다섯 event만 ID/event/text/active로 조회. 무쓰기. UI 정렬은 ID 오름차순이어도 선택 의미 없음 |
| PATCH `/api/local/characters/{cpu_id}/fixed-dialogues` | `{expected_revision, edits: {slot: {text} | {legacy_dialogue_id, expected_source_text}}}`. 비어 있는 edits/unknown slot/extra field/null/두 방식 혼합 거절 |

한 요청의 모든 슬롯 검증 후 하나의 transaction으로 저장한다.
해당 CPU가 없으면404, expected_revision 불일치는409 revision_conflict.
기존 연결은 같은 CPU·같은 event_key·현재 active인 행만 허용한다.
다른 CPU/다른 event는422, 선택 후 삭제·비활성·원문 변경은409 legacy_dialogue_conflict로 재조회 안내한다.
클라이언트가 보낸 expected_source_text는 현재 DB 원문과 정확히 같아야 한다.
후보가 없는 win을 ron/tsumo/match_first에서 추정해 채우지 않는다. 직접 입력만 가능하다.

이미 origin이 있는 슬롯에 같은 원본 ID/원문을 재연결하면 **현재 편집값을 덮지 않는다**.
다른 기존 행으로 다시 연결하는 작업은 이번 범위에서 지원하지 않고409로 명시한다.
기존 직접 편집 슬롯(origin=null 포함)에 legacy 연결로 덮어쓰는 것도409로 거절한다.
미설정 슬롯에만 최초 legacy 연결을 허용한다. 따라서 재실행/이중 요청이 중복 row나 초기값 덮기를 만들지 않는다.
expected_revision 검사를 먼저 하므로 응답 유실 후 같은 stale PATCH는409일 수 있다. GET으로 확인한다.
검증/flush/commit 실패에는 전체 rollback, 성공 응답은 commit 뒤 반환한다.
writer 직렬화와 revision 검사를 함께 사용하여 두 창의 stale save가 성공하지 않게 한다.
오류 처리 방식은 기존 local API 관례를 재사용하며 새 범용 예외 framework를 만들지 않는다.

신규 수동 저장과 legacy 연결로 저장할 원문 모두 승인된 D10-a 문법을 검증한다.
허용 토큰은 정확히 `{{character_name}}` 하나다. 단일 중괄호/짝이 안 맞는 중괄호,
다른 변수·템플릿 문법은422로 표시하고 원본은 보존한다. 일반 평문/줄바꿈/빈 문자열은 허용한다.
원문 trim/정규화·한국어 조사 보정·임의 escaping 저장은 하지 않는다.
이름 치환 helper는 원문에서 토큰을 한 번 치환하며 삽입한 이름을 다시 해석하지 않는다.
관리 UI의 미리보기만 현재 선택 캐릭터 이름을 쓸 수 있다. 게임 snapshot 이름 사용은 C2 책임이다.
W06 엔딩 대사에는 이 validator/helper를 적용하지 않는다.

## 4. 최소 UI

기존 캐릭터 설정 안 별도 '고정 대사' 영역과 작은 전용 컴포넌트를 사용한다.
캐릭터 선택, 다섯 슬롯의 라벨·textarea·설정/미설정/직접 빈 값 상태,
허용 변수 설명·평문 미리보기·저장/오류/재조회만 제공한다.
과거 게임 기록과는 별개인 편집 자료임을 짧게 설명한다. 실제 문구 예시를 작성/seed하지 않는다.

각 미설정 슬롯에서 '기존 문구 선택'을 누르면 해당 event 후보를 ID·원문·활성 상태로 보여 준다.
하나여도 자동 선택하지 않는다. 비활성 행은 표시하되 선택 불가, 빈 목록은 후보 없음 안내다.
선택한 원문을 확인하고 명시 저장할 때만 연결한다. 선택 자체는 DB를 쓰지 않는다.
복수 슬롯의 수동 입력/연결을 동일 저장 요청에 담을 수 있다.
조회가 먼저 도착한 캐릭터의 편집을 늦은 이전 캐릭터 응답이 덮지 않도록 요청 identity를 검증한다.
저장 중 입력/캐릭터 전환 등 경쟁 조작은 잠그고, 저장 오류 시 입력을 보존한다.
캐릭터 전환/닫기는 미저장 변경을 기존 설정 UI 관례에 맞게 보호한다.
서버409 후 자동 덮어쓰기/자동 후보 선택/자동 재저장은 하지 않는다.
출처의 ID/당시 원문과 현재 고정값을 구분해 보여 주며, 연결 후 textarea로 직접 편집할 수 있다.
일반 텍스트로 렌더링하고 HTML 해석을 하지 않는다.

## 5. 필수 검증과 완료 기준

- 파일 SQLite에 migration 신규/반복 upgrade, 기존 CPU/대사/완료 presentation 및
  CharacterContent·voice 선택·파일 참조가 보존됨을 확인한다. GET은 행을 만들지 않는다.
- 다섯 슬롯·명시 빈 값·미설정·변수 반복 치환/재귀 금지·줄바꿈/HTML 평문·잘못된 문법,
  unknown slot/extra/null·CPU/event 불일치/비활성·후보 원문 변경/삭제를 검사한다.
- 동일 CPU/event에 서로 다른 기존 문구 두 개를 두고 사용자가 선택한 ID만 저장됨,
  첫 행/무작위 자동 연결 없음, 두 CPU의 같은 문장도 병합 없음.
- 최초 연결 뒤 직접 편집→동일 연결 재시도로 편집값 보존. 다른 원본/직접 편집 위 연결 거절,
  stale revision·두 writer 경쟁·혼합 PATCH 일부 실패에 무부분저장·commit 실패 rollback.
- 원본 legacy 변경/삭제 후 고정값/출처 사본 불변, legacy 경로는 여전히 기존 자료 사용.
- engine 재시작/진행 reset/동일 팩 갱신 뒤 고정 대사와 revision 보존. 기존 P/N override,
  신체 null/빈 편집·음성 selected/off·참가명단/stage/게임 설정이 바뀌지 않음.
- 실제 routed browser로 캐릭터 변경의 지연 응답, 후보 선택→저장→재조회,
  빈 값 편집/409/저장 실패 입력 보존·출처 표시를 검증한다.
- backend 전체 unittest·대사 pytest, frontend build·관련 기존 local-content/audio/result-delivery browser.
  정확한 제품 source SHA의 기존 Windows W04/W05와 artifact source/hash·내부 ZIP,
  packaged renderer/DB migration/종료·재시작을 확인한다. 실측/합성 mock/개인 PC 미검증을 구분한다.
- CURRENT_STATE/TASKS/ARCHITECTURE에 구현·실제 검증·한계를 기록하고 PR을 제출한다.
  계약 작성만으로 제품 구현/Windows 검증 완료라고 쓰지 않는다.

## 6. 허용 범위와 인계

허용: 새 fixed dialogue model/export, 다음 additive migration, 새 전용 schema/service,
기존 local_content character router 최소 확장, 새 frontend 최소 컴포넌트 및
LocalContentPanel/api의 연결, 관련 backend/frontend 테스트·기존 Windows 검증 helper 최소 보강,
CURRENT_STATE/TASKS/ARCHITECTURE와 필요한 README 사용 설명.
기존 모델/팩 스키마·scanner·character_content merge는 고정 대사를 섞기 위해 변경하지 않는다.
기존 dialogue_service/admin/game registry/API game/engine/CPU·C1 전달 모델/ack/gate는 수정 대상이 아니다.

```text
danhk0612/no-riichi-no-fuku의 최신 main·열린 PR·AGENTS와 루트 기준 문서를 확인해.
docs/W09_M_FIXED_DIALOGUE_CONTRACT.md 전체에 따라 W09-M만 구현해.
task/w09-m-fixed-dialogues에서 CPU별 다섯 고정 슬롯 관리와 Q-LEGACY A 명시 선택 연결을 추가해.
기존 복수 문구/완료 결과를 보존하고 자동 선택·자동 이전·현재 원본 live 참조를 하지 마.
슬롯별 출처 사본·명시 빈 값·revision·writer 원자성·D10-a 검증과 최소 UI를 구현해.
기존 pack P/N/override/음성 선택·게임 이벤트/RNG·C1 unbound 대국은 변경하지 마.
계약의 파일 DB/동시성/실패/재시작/reset/browser 회귀와 전체 관련 검증을 수행해.
최종 source의 Windows W04/W05/artifact를 확인하고 검증 한계를 문서에 기록해.
commit/push·PR 제출까지 진행하고 직접 병합·Release/tag는 하지 마.
S/C2/상황 연결/게임 고정문구 출력/CG·오디오·프롬프트 생성은 추가하지 마.
정책 미확정이나 범위 밖 작업이 필요하면 임의 확장하지 말고 구체 차단 사항을 보고해.
```
