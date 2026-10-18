# W08-D — 공유 복장 상태·포즈와 캐릭터별 명시 후보

## 목적과 범위

기준 main `b3bfcb5`(PR #94). W08 전체 중 정책이 확정된 복장 상태/포즈 관리부터 분리한다.
권장 환경은 저성능 Work다. 이 문서는 구현 계약이며 현재 기능이 구현됐다는 뜻이 아니다.

- Level 0..3 각각 공유 복장 상태와 포즈의 label·긍정/부정 원문 편집/저장.
- 기존 CPU별·Level별·종류별 명시 후보와 지정 기본값 관리.
- 삭제/Level 이동 전 연결 영향 표시, 확인 후 연결 해제·유효 기본값 복귀.
- 최소 로컬 관리 UI·API·additive migration·회귀/Windows 검증.

상황/대사·event 연결·변수 실행·기존 대사 이전, 모델/LoRA 설정, 이미지 등록/생성/표시,
팩 manifest 변경/새 팩 종류/자동 export, 새 CPU·게임 규칙/난이도/진행/음향은 제외한다.
상황별 별도 복장/포즈 제약은 만들지 않는다(D06-d A). 실제 문구·이미지·음향 seed도 없다.

## CG 용어와 보존 경계

이미지 종류는 기존 `profile|full_body|cg`뿐이다. CG는 캐릭터별·Level별 자료다.
최종 4위로 단계가 변하면 **단계 변경을 정산한 뒤 변경된 Level의 `cg`를 표시**한다.
별도 `defeat_cg` 종류나 화료용 CG를 만들지 않는다. 완료 보충/오마케는 기존 stage 불변·
추가 CG 이벤트 없음이며 기존 승패 음성은 유지한다. 전체 완료 엔딩은 기존 별도 계약이다.
W08-D는 이 표시 경로를 변경하지 않으며 아직 조합/생성 기능도 연결하지 않는다.

## 저장 관계

기존 `CharacterContent.revision`은 P/N·치수·팩 적용용으로 유지한다. 공유 후보를 거기에
합치거나 game CPU/difficulty snapshot에 넣지 않는다. 다음 새 관계를 로컬 DB에 추가한다.

| 관계 | 필드·제약 |
|---|---|
| SharedPromptItem | UUID PK, kind=`clothing_state|pose`, level=0..3, label, positive, negative, revision>=1, active, timestamps |
| CharacterPromptCandidates | (cpu_id,level,kind) unique, UUID PK, revision>=1. cpu_id는 기존 CPU FK |
| CharacterPromptCandidateEntry | (candidate_set_id,item_id) unique FK. 명시 후보는 같은 kind/Level의 active 항목만 |
| SharedPromptDefault | (level,kind) PK, item_id nullable FK, revision>=1. 기본 항목도 같은 kind/Level의 active 항목만 |

label은 표시명이고 이름 변경으로 ID가 바뀌지 않는다. 종류는 생성 후 불변이다. 다른 종류로
바꾸려면 새 항목을 등록한다. 같은 label의 다른 항목은 UUID로 구분하며 label로 자동 병합하지 않는다.
공유 원문은 공통 행에만 저장하고 CPU마다 복제하지 않는다. P/N은 빈 문자열도 유효하며
줄바꿈·공백·태그를 그대로 보존한다. 조합 순서/구분자·모델 태그 보정은 이번 범위가 아니다.

migration은 기존 head `20261018_0010` 다음 additive revision이다. 기존 PK/성향/명단/진행,
CharacterContent·pack/revision/digest·과거 game/presentation·미디어를 변경하지 않는다.
공유 데이터/기본값/후보는 처음에 비어 있다. 기본 문구나 자동 후보를 bootstrap하지 않는다.
GET은 행을 만들지 않으며 없는 후보/기본 리소스의 revision은0이다. 최초 저장은 expected_revision0.

## 후보와 기본값 의미

1. 신규 항목은 어느 CPU 후보에도 자동 포함하지 않는다. 기존 후보를 등록 목록 전체로 간주하지 않는다.
2. 지정 기본값은 (Level,kind)마다 명시 저장한 item UUID다. 목록 순서/파일명/첫 행으로 추측하지 않는다.
3. 유효한 명시 후보가 있으면 그 목록을 반환한다. 후보가 미설정/비었거나 대상이 없어 유효 후보가
   없으면 해당 (Level,kind)의 유효 기본값을 확인한다. 그것도 없으면 빈 목록과 미등록 상태를 반환한다.
4. 후보를 조회할 때 기본 항목을 후보 행에 자동 삽입하지 않는다. 저장 ID와 effective ID·기본값 사용 여부를
   구분한다. 나중에 기본값이 바뀌면 기본값을 쓰는 CPU의 조회 결과도 바뀌지만 GET 쓰기는 없다.
5. 후보 선택은 전체 ID 목록 교체로 저장한다. 중복/다른 Level·kind/비활성/없는 ID는 기존 계약의422다.
   개별 후보 항목의 P/N 편집은 후보 revision을 올리지 않는다. 공유 항목 revision으로 식별한다.
6. 초기화는 모든 새 공유/기본/후보 자료를 보존한다. 참가 명단 고정 여부와 무관하게 기존 CPU 후보를
   편집할 수 있지만, 현재 대국·저장된 표시를 재계산하거나 바꾸지 않는다.

## API와 transaction

기존 local capability·superadmin 경계, session.rollback() 뒤 mark_write_intent(session),
같은 SQLite writer와 commit 후 응답 방식을 재사용한다. 새 전역 lock/인증 체계를 추가하지 않는다.
새 스키마는 local content와 별도 파일에 둘 수 있으며 기존 v1 manifest 스키마는 확장하지 않는다.

| method / `/api/local` 이하 | 요청/응답 |
|---|---|
| GET `/shared-prompts?kind=&level=` | active 목록, 각 UUID/kind/Level/label/P/N/revision. Level·kind 필터 필수 |
| POST `/shared-prompts` | kind,level,label,positive,negative. revision1 생성 |
| PATCH `/shared-prompts/{id}` | expected_revision, 변경할 label/P/N만. Level 변경은 확인 API 사용 |
| GET `/shared-prompt-defaults/{level}/{kind}` | revision, item_id/null, 유효 상태 |
| PUT `/shared-prompt-defaults/{level}/{kind}` | expected_revision,item_id/null |
| GET `/characters/{cpu_id}/prompt-candidates/{level}/{kind}` | revision, stored_item_ids, effective_items(ID/P/N/revision), uses_default, default_revision |
| PUT `/characters/{cpu_id}/prompt-candidates/{level}/{kind}` | expected_revision,item_ids 전체 교체 |
| POST `/shared-prompts/{id}/change-preview` | expected_revision, action=`move|delete`, move이면 target_level. 아래 영향 확인 결과 |
| POST `/shared-prompts/{id}/change-confirmation` | 같은 action/target_level, expected_revision, preview_digest. 일치한 영향만 원자 적용 |

종류는 clothing_state/pose, Level은0..3만 받는다. PATCH에서 Level 변경/종류 변경을 허용하지 않는다.
변경 없는 PATCH·같은 후보/기본값 저장은 새 revision을 만들지 않는다. 명시 빈 P/N 저장은 유효 편집이다.
표준 오류는 기존 envelope `detail:{code,message,fields?}`와401/403·404·409·422를 재사용한다.
임의 사용자 경로나 원문 전체를 오류에 담지 않는다. commit 실패 시 부분 성공 응답은 없다.

### 삭제/이동의 영향 확인

preview는 읽기 전용이다. 항목의 ID/revision/action/target_level, 연결 CPU ID/이름/Level/kind·
후보 resource revision, 원래 기본값 참조와 revision, 해제 후 적용할 유효 기본값 ID/revision 및
미등록으로 남는 대상을 표시한다. 기본값을 사용해서 간접 영향을 받는 기존 CPU도 목록에 포함한다.

이 정렬된 영향 내용의 canonical JSON SHA256을 preview_digest로 반환한다. 클라이언트에서 영향
목록을 신뢰하여 적용하지 않는다. confirmation은 writer 안에서 현재 영향 전체를 다시 계산해
일치 여부를 검증한다. 항목/후보/기본값·표시 이름 등 확인 대상이 바뀌면409로 다시 확인한다.
미등록 CPU까지 새 후보 row를 만들거나 모든 CPU를 실제 갱신하는 방식은 쓰지 않는다.

확인 성공 시 해당 항목을 참조한 명시 후보에서 제거하고, 원래 범위의 기본값 참조도 해제한다.
나머지 명시 후보가 유효하면 유지한다. 유효 후보가 없어지면 해당 범위의 유효 기본값으로 resolve하며
없으면 출력 생략 상태다. 지울/이동할 자기 자신을 원래 범위의 기본값으로 재연결하지 않는다.
이동된 항목은 새 Level에서 active로 유지하되 새 Level 후보/기본값에 자동 포함하지 않는다.
삭제는 active=false 논리 삭제다. 이번 UI에서 복구/영구 삭제/파일 청소는 제공하지 않는다.

실제로 바뀐 후보/기본값 resource와 항목의 revision을 각각 증가시키고 한 transaction으로 commit한다.
누락/충돌/commit 실패는 모든 관계와 revision을 유지한다. GET·화면 렌더가 삭제/이동을 수행하지 않는다.
preview 이후 기본값 내용·후보가 바뀌거나 항목이 편집됐을 때도 저장된 이전 확인으로 실행하지 않는다.

## 최소 UI

기존 캐릭터 프롬프트·팩 설정에 공유 복장/포즈 관리 탭을 추가한다. 새 독립 앱/갤러리는 만들지 않는다.
- Level·종류 선택, 해당 목록·추가·label/P/N 편집/저장, 기본 항목 지정/해제.
- 기존 CPU와 Level·종류를 선택해 명시 후보 체크/저장. 기본값 적용 결과와 미등록 상태 표시.
- 삭제/Level 이동은 preview 결과의 연결 대상·해제/기본값 복귀를 보여 주고 별도 확인 후 실행.
- 입력/저장 대기·실패/충돌 draft 보존·빠른 탭/CPU/Level/종류 전환의 request token을 유지한다.
- 저장은 해당 리소스만 갱신한다. CPU 선택/진행 초기화·재선택·대국/음향 중단을 일으키지 않는다.
- 복장 상태 문구·포즈를 자동 작성하거나 Level별 의상을 자동 판별하지 않는다. 등록자가 작성한다.

## 검증과 완료 기준

| 범위 | 필요한 검사 |
|---|---|
| 기본 CRUD | GET 무쓰기/revision0, 두 kind×4Level 격리, P/N 원문·빈 값 보존, stale409/권한·형식/commit 실패 |
| 후보·기본 | 신규 자동 포함 없음, 명시 후보 우선·빈/누락 시 지정 기본·없으면 빈 목록, 잘못된 종류/Level/ID 거절, GET 무쓰기 |
| 삭제/이동 | 직접·기본값 경유 영향 목록, 확인 전 불변, 영향 변경 시409, 기본 자기 참조 금지, 새 Level 자동 포함 없음, 부분 commit 없음 |
| 보존 | migration 반복·기존 치수/팩 편집/voice/명단/난이도/진행과 파일 불변, 자료 reset/restart 보존 |
| UI | CRUD·후보/기본 저장, 영향 확인/취소, 저장 오류·충돌 draft, 빠른 선택·지연 응답, 선택 CPU·현재 대국 보존 |
| 통합 | backend 전체·대사pytest·frontend build·관련 browser, 정확한 최종 SHA의 W04/W05 Windows CI·다운로드 artifact source/hash |
| packaged | 실제 설정 UI에서 공유 P/N·후보·기본 저장 후 진행 초기화·engine 재시작 뒤 보존. 임시 테스트 문자열과 사용자 문구 구분 |

변경 파일은 새 model/export·head 다음 migration·shared prompt schema/service/router·local runtime 등록,
기존 LocalContentPanel/api/types/style·관련 테스트·desktop의 필요한 검증 smoke와 기준 문서에 한정한다.
게임 event/대사 resolver·프롬프트 builder·이미지 loader/CG 정산·팩 scanner 코드는 변경하지 않는다.

소유 임시 테스트 데이터만 사용하고 실제 문구·이미지·음향은 커밋하지 않는다. 빈 기본값은 정상이며
콘텐츠 미제공을 임의 seed로 해결하지 않는다. 실패하면 실패 근거·미검증을 기록한다.
개인 Windows PC·실제 리소스 출력은 hosted CI와 구분한다. 직접 병합·Release/tag·후속 Task 착수 금지.
