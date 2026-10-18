# W08-M — 캐릭터 신체 메타데이터 독립 구현 계약

기준 main: `7bcec42b8a4122a754b692a8647790329ae18325` (PR #91 병합).
이 문서는 구현 명세이며 제품 구현 완료 보고가 아니다. AI_WORKFLOW의 설계 후 독립 구현 인계 단위다.

## 범위와 확정 근거

사용자가 확정한 Q-META A: 키·가슴·허리·엉덩이는 항목별 선택 입력, cm 단위,
소수 한 자리, 미입력 숨김. 추정값·실제 치수 seed·새 능력치 계산은 없다.
Q-PACK A의 직접 편집값 보존을 이 네 필드에도 적용한다. 캐릭터 이름/성인 여부/성향은
기존 CPU 원본을 유지하고 팩 적용으로 덮지 않는다. 난이도 정책은 PR #91 그대로다.

다음만 구현한다.

- 기존 캐릭터 설정에 네 치수의 조회/명시 저장/항목별 비우기.
- 선택 카드에서 입력된 치수만 간단히 표시. 미입력 전체는 행도 숨긴다.
- 새 캐릭터팩 연결/같은 팩의 새 revision 적용 시 유효한 치수 원본 반영,
  직접 편집한 값과 명시적으로 비운 값 보존.
- 재시작/진행 초기화 보존, revision 충돌·transaction·늦은 응답 검사.

전신/CG 배경·hover 상세·좌석 상세·뷰어/줌·생성은 W11-U/W11로 남긴다.
공유 상황/후보/변수, 모델/LoRA 설정 및 미확정 D05~D10은 이 작업에서 확정하지 않는다.

## 데이터·단위

캐릭터 ID는 기존 CPU 정수 PK, 배포 ID는 기존 slug/character_id다. ID를 바꾸지 않는다.
새 치수는 gameplay CpuChoice/GamePlayer/진행도에 넣지 않고 CharacterContent에 저장한다.

기존 `character_content`에 nullable JSON `measurements_cm` 하나를 추가하는 additive migration을
현재 Alembic head 다음에 만든다. 기존 행 null/미존재는 네 항목 모두 미입력으로 읽는다.
GET으로 행 생성/보정/자동 팩 적용을 하지 않는다. `revision`과 `overrides`는 기존 것을 재사용한다.

| 키 | UI | 표현 |
|---|---|---|
| height | 키 | null 또는 양수 cm |
| bust | 가슴(B) | null 또는 양수 cm |
| waist | 허리(W) | null 또는 양수 cm |
| hips | 엉덩이(H) | null 또는 양수 cm |

wire/저장 정규형은 소수 한 자리의 십진 문자열 또는 null이다. 실제 숫자 예시를 seed하지 않는다.
사용자 입력은 십진 문자열로 보내고 서버에서 Decimal로 검증한다. 정수 형태는 `.0`으로 정규화하되
둘째 소수 자리를 반올림하지 않고 거절한다. bool·0/음수·NaN/Infinity·단위가 붙은 문장은 거절한다.
현실 신체 범위/비율/나이 추정 제한을 새로 도입하지 않는다. 부동소수점 산술/게임 계산에 쓰지 않는다.

## 기존 API 확장

`GET/PATCH /api/local/characters/{cpu_id}/content`를 확장한다. 새 별도 CRUD/팩 관리 시스템은 없다.
GET은 `measurements_cm:{height,bust,waist,hips}`와 필드별 `measurement_overrides`를 반환한다.
`pack_source`에는 적용된 revision의 원본 `metadata`를 그대로 추가해 원본과 편집값을 비교한다.
원본 전체를 정규화된 로컬 치수라고 표시하지 않는다.

PATCH는 기존 `expected_revision`과 optional `measurements_cm` 부분 객체를 받는다.
미포함 키는 보존, 명시 null은 비우기이며 `overrides`의 `measurements_cm.<key>`를 기록한다.
원본과 같은 값을 저장해도 직접 편집이다. P/N과 치수를 한 번에 저장하면 하나의 revision/commit이다.
기존 PATCH 권한·writer·revision 충돌409·유효성422·commit 후 응답을 사용한다.

`GET /api/local/play/roster-candidates`에 읽기용 `measurements_cm`를 추가한다.
새 대국 생성/현재 대국/WS의 CPU 판단 snapshot과 action payload는 바꾸지 않는다.
기존 웹 관리자와 웹 CPU 선택 경로로 신체 편집 기능을 확장하지 않는다.

## 팩 원본과 적용

manifest v1은 이미 `metadata`의 추가 JSON을 보존한다. 이 성질을 바꾸거나 과거 revision의
manifest/digest를 rewrite하지 않는다. 신규 선택 치수의 위치는 `metadata.measurements_cm`이다.
팩 작성자는 네 지원 키에 같은 십진 문자열/null을 사용한다. 블록/항목 누락은 미입력 원본이다.
새 치수 블록 때문에 name/adult/description/style 등 원래 metadata를 복제·이동하지 않는다.

등록 scanner는 기존 opaque metadata 보존 계약을 유지한다. 적용 서비스가 치수 블록을 해석한다.
치수 블록에 지원하지 않는 키/형식이 있으면 **새 팩 적용 전체를 실패**시키고 기존 P/N·치수·음성
연결·revision을 유지한다. 팩 진단과 적용 오류를 구분한다. 기존 등록/이미 적용 원본은 그대로 조회한다.

최초 연결/새 revision의 명시 적용에서 네 필드별로 다음을 사용한다.

- override 있음: 로컬 값 유지. null도 보호.
- override 없음: 새 원본의 정규화 값, 항목 누락/null이면 null.

재검색만으로 적용하지 않는다. 같은 적용 revision 재적용은 기존처럼 no-op이고,
업그레이드 시 예전 opaque metadata에서 치수를 자동 추출/적용하지 않는다.
기존 연결은 수동 편집하거나 같은 팩의 새 revision을 명시 적용한다. 팩 교체/연결 해제 기능은 추가하지 않는다.
팩 적용의 원본 파일/이미지 digest 검증, 음성 default 갱신/selected·off 보존은 기존 계약을 유지한다.

## UI·저장 경계

기존 LocalContentPanel의 캐릭터 선택 아래에 네 입력/단위·미입력 안내와 편집 여부를 붙인다.
빈 입력은 null, 건드리지 않은 입력은 PATCH에서 제외한다. 기존 저장 버튼/dirty 기록을 재사용한다.
팩 적용 전 미저장 편집을 먼저 저장하도록 하는 기존 제한을 유지한다.
실패/충돌은 입력을 보존하고 성공 후 서버 정규형을 표시한다. 캐릭터 전환/닫기/초기화 뒤
늦게 도착한 GET/PATCH/팩 적용 응답은 기존 request/generation token으로 격리한다.

선택 카드에는 존재하는 항목만 cm와 함께 표시한다. B/W/H 중 일부만 있어도 각 이름으로 구분해
미입력 수치를 0이나 임의 수치로 채우지 않는다. 전신/CG나 별도 상세 창은 만들지 않는다.
진행 초기화는 CharacterContent/치수/팩·파일을 삭제하거나 수정하지 않는다.
이름/성향/난이도/진행도/대국 agent/socket·음향 RNG를 재생성하지 않는다.

## 파일 경계와 검증

기존 character_content 모델·현재 head 다음 additive migration, local_content schema,
character_content 서비스/local API·roster-candidates DTO, LocalContentPanel/api/types/CpuSelection,
최소 style, 관련 테스트/Windows smoke·루트 기준 문서만 수정한다.
기존 mahjong agent/난이도 resolver/profile/legacy fixture/정산·오디오 알고리즘은 변경하지 않는다.

검증은 nullable 기존 DB upgrade·반복 startup, 네 키 독립 저장/누락/null/원본과 같은 값 override,
소수 정규형·둘째 자리 거절·잘못된 형식, 읽기 무쓰기, revision/commit 실패·팩 전체 원자 적용,
처음 연결/새 revision/동일 revision no-op·미편집 갱신/명시 null 보호, 과거 manifest/digest·파일 불변,
reset/restart·고정 명단/난이도 snapshot 보존을 확인한다.
브라우저는 미입력 행 숨김/부분 표시/단위·입력/초안 유지·늦은 응답/팩 적용을 확인한다.
backend 전체·대사 pytest·frontend build·기존 브라우저 회귀 및 정확한 head W04/W05 CI,
다운로드 artifact의 source/SHA256·packaged 편집/재시작/reset 보존 smoke를 수행한다.
제품 seed에 실제/임의 치수를 채우지 않고 CG·음향을 생성하지 않는다. 격리 테스트의 검증 수치는
제품 콘텐츠와 구분한다. 개인 PC와 hosted CI는 구분한다.
