# 현재 상태

## W08-B — 프롬프트 편집·팩 목록 UI 구현

2026-10-16 KST 최신 `main`은 준비 SHA `469aa36`와 일치했고 PR #80이 병합됐다. 열린 PR은
기존 Docker 문서 #35뿐이었다. `task/w08-b-character-editor`에서 0007 다음 additive migration 0008,
기존 CPU PK별 기본 P/N 및 Level 0..3 × profile/full_body/cg 구도 P/N 저장, 문자열 필드별 override,
revision 검사와 로컬 API를 추가했다. GET은 저장 전 빈 값을 revision 0으로 반환하며 행을 만들지 않는다.
PATCH는 요청에 명시된 문자열만 기록하고 빈 문자열도 override로 보존한다. 캐릭터 팩과 로컬 편집을
자동 연결·병합하지 않아 팩 재검색이 편집을 덮지 않는다. 기존 CPU PK 전체를 대상으로 하는
로컬 관리자 CPU 목록에서 편집 대상을 선택한다.

Electron 데스크톱 설정에 기본/구도 P/N 편집·필드별 편집 기록 UI와 팩 목록·정상/미해결/충돌 진단·
명시 재검색 UI를 추가했다. 팩 탭 진입은 POST rescan, 목록 GET은 DB만 조회한다. 캐릭터 전환 stale
응답은 현재 폼에 반영하지 않으며 저장 실패/충돌 시 초안은 보존한다. 실제 프롬프트·콘텐츠·이미지·
사운드 seed, 이미지 파일 업로드/생성, CPU 연결 및 팩 적용은 추가하지 않았다.

로컬 검증: Python 3.12.14/RiichiEnv 0.4.8의 backend unittest 119개, dialogue pytest 10개,
frontend `npm run build`, Electron 종료 회귀 3개 통과. 신규 API 회귀는 GET 무쓰기, 빈 문자열/필드별
override, 서로 다른 구도, stale revision, 권한, commit 실패 rollback, reset/restart 보존, 팩 재검색 후
로컬 편집 불변을 확인한다. 이번 문서 갱신 시 정확한 최종 source SHA의 Windows hosted CI와 artifact는
아직 대기 중이며 확인 후 이 절을 갱신한다. 개인 Windows PC·실제 이미지/오디오 출력·ComfyUI는 미검증이다.

W08-B는 W08-A 기반 편집/목록 UI 범위만 다루며 W07 전체 완료나 W08 전체 구현 완료를 뜻하지 않는다.

## Q-PACK A 결정 및 W08-B 인계 — 문서 작업

2026-10-16 KST main `0068eb6`에서 PR #79 병합을 확인했다. 별도 열린 PR은 Docker 문서 #35다.
사용자가 팩 업데이트 최적안 선택을 위임해 A(직접 편집 유지·미편집만 새 원본 반영)를 채택했다.
Q-PACK을 재질문하지 않으며 필드별 명시 override·빈 문자열 보호·기본 음성/selected/off 경계를
계약에 반영했다. 다음 독립 단위 W08-B는 기존 캐릭터 기본/구도 P/N 편집·편집 기록과 팩 목록 UI다.
팩 실제 적용/새 CPU 연결·공유 후보·생성 등은 분리하며 다른 미응답 정책을 자동 승인하지 않았다.
이번 변경은 문서 5개뿐이며 제품 코드·migration·실제 프롬프트·사용자 자료 변경은 없다.
문서 공백·내부 링크·fence·범위를 검증하고 제품 테스트/Windows CI는 실행하지 않는다.

W08-A 최종 head `f529c96`의 W04 `38850325569`/W05 `38850325453`은 성공했다.
다운로드 artifact의 source SHA/압축 hash를 확인했고 Windows unittest 115·대사 10·renderer 22개,
일반 종료/같은 data root 재시작을 대조했다. 자세한 source/ZIP hash는 PR #79 본문에 보존했다.
아래 검토의 이전 성공 이력은 수정본 성공과 구분하며 실제 리소스/개인 PC/ComfyUI는 미검증이다.

## W08-A 최종 검토 보완 — Windows 팩 ID 이식성

PR #79 원본 head `0742a9d`를 검토했다. W04 `38845782594`/W05 `38845782569`는
원본 정확한 head에서 성공했고 artifact identity/digest도 대조했다. Linux 원본 unittest 114개를
75.929초에 재현했다. 팩/캐릭터/voice namespace의 Windows 예약 장치명 허용을 추가 발견했다.
수정 전 새 회귀 1개에서 110개 subcase 실패를 재현하고 기존 상대 파일 경로 검증을 EnglishId에도
적용했다. 제품 보완 source `ad12e6f`의 registry 검사 15개는 9.723초에 통과했다.
이후 변경은 검토 문서이며 수정본 정확한 head의 Windows 검사/최종 artifact는
[PR #79](https://github.com/danhk0612/no-riichi-no-fuku/pull/79)의 최신 check run과 PR 본문을 따른다.
기존 CI 증거를 수정본 증거로 대체하지 않는다. 실제 파일 decode/오디오·개인 Windows·전원 차단·
ComfyUI는 계속 미검증이며 팩 실제 적용/새 이벤트/UI/콘텐츠는 추가하지 않았다.

## W08-A — 팩 등록 기반 구현·검증

기준 main `01da78461a8e58bebc8e05d583fac2c5a0a9b38c`, PR #75~#78 병합 및 열린 별도 Docker 문서 #35를 확인했다.
`task/w08-a-pack-registry`에서 migration 0007, 4종 manifest v1 검증, startup/rescan·DB 목록 API,
pack/revision·manifest/content digest·파일별 immutable UUID 복사를 구현했다. 같은 manifest의 파일 bytes
변경은 새 revision, 동일 content 재검색/과거 버전 재인식은 unchanged다(인식 포인터는 해당 버전으로 갱신). 실패/누락/충돌 시 기존 등록·파일은 보존한다.
마지막 성공 인식 revision은 별도 FK로 저장한다. A→B→A 복원 시 기존 A를 다시 가리키며
새 revision/파일을 추가하지 않는다. 자동 리뷰의 해당 지적은 수정 전 회귀 실패 1건을 재현한 뒤 보완했다.
적용 pointer는 null이며 기존 CPU/명단/로컬 편집/재생 설정에 연결하지 않는다. 원본과 과거 revision은 수정하지 않는다.
외모·상의 속옷·하의 속옷 P/N 및 4 Level×3종 이미지/구도 P/N은 manifest snapshot으로 보존한다.
실제 콘텐츠/CG/오디오·기본 팩을 생성·seed하지 않았다. W07 전체 미완료, W08 전체 구현 착수도 아니다.

Linux Python 3.12.14/RiichiEnv 0.4.8에서 backend unittest 114개(신규 registry 14개 포함),
대사 pytest 10개, frontend npm ci/build, Node 종료 회귀 3개가 통과했다. 신규 검사는 0006→0007
업그레이드/반복 migration·startup scan·reset/restart·한글/공백 경로·W06 행/설정/파일 bytes 보존,
중복/경로 이탈/link·불완전/비지원 manifest·변경 중인 파일·동시 scan·DB commit/파일 복사 실패를 포함한다.
모든 자료는 소유 임시 signature fixture이며 실제 이미지 decode/오디오 출력 검증이 아니다.
제품 source `ca2c2efdeca564ca142c904efa4aa4d7d9206c38`의 Windows Server 2022 x64 CI가 통과했다.
W04 [38845126341](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38845126341)와
W05 [38845126360](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38845126360) 모두 exact head checkout이다.
W04 artifact `12022728009`의 source SHA·archive SHA256
`f03a9dcc88ece661e3f7f7d3718d02b13600b90ce42b656deb9ba636ab1d8a76`, unittest 114·대사 10 결과를 대조했다.
다운로드한 W05 artifact `12023410265`의 source SHA·archive SHA256
`be3a402c0c38636df7786df2ed71e959b7a549a2d14eda49568e3fd4ff8c1192`와 내부 Windows ZIP SHA256
`d1d101549a866fe3af9d3f370125d1a6fc02d6fa88d6c2559174ff1a5f7cec7f`를 CI 기록과 대조했다.
renderer smoke 22개·일반 모드 child/창/host 종료 순서·같은 data root 재시작,
기존 W06 sound browser·Windows unittest 114/대사 10도 확인했다. 제품 파일은 위 source로 고정하며
후속 증거 문서 commit의 head/CI 상태는 [PR #79](https://github.com/danhk0612/no-riichi-no-fuku/pull/79)를 따른다.
개인 Windows PC/전원 차단·실제 리소스 출력·ComfyUI는 미검증이다.

Q-PACK은 새 revision 적용/로컬 편집 병합, Q-META는 편집/표시 필드, Q-LEGACY는 기존 대사 이전,
Q-AUDIO는 W08-S 재생 전환, D-WIN/Q-OMAKE-VOICE는 새 음성 hook, D05-c/D06-c/D10-a는
event/후보 이동/변수, D07~D09/Q-IMAGE/Q-FRAME은 생성/표시 계약을 막는다. 등록/보관은 독립 구현했다.
공유 registry가 아직 없어 shared_dependencies는 unresolved로 보관하며 연결/적용하지 않는다.
후속 설정 UI는 목록 진입 때 POST rescan을 호출해야 한다. W08-A에는 UI를 추가하지 않았다.

## W07 단계별 착의 상태 확정 — 문서 반영

2026-10-16 KST main `73b79de`(PR #77 병합)와 열린 별도 Docker 문서 #35를 확인했다.
Q-UNDER를 사용자 응답으로 확정했다. 1단계는 상의 겉옷을 벗어 브래지어가 보이고 하의 겉옷은 유지,
2단계는 상·하의 겉옷 없이 속옷 세트만 착용한 누적 상태다. 0 정상/3 전체 탈의는 유지한다.
후속 사용자 지시의 시스템 우선·실제 프롬프트 작성 최소화·사용자/다른 AI의 차후 작성 원칙도
요구/후속 작업/AGENTS에 반영했다. 콘텐츠 문구 완성을 시스템 구현 선행 조건으로 삼지 않는다.
REQUIREMENTS 상태표·ARCHITECTURE 프롬프트 계약·TASKS 후속 검증·AGENTS 요약에 반영했다.
구체 프롬프트/이미지/오디오를 생성하지 않았으며 제품 코드·사용자 자료·migration 변경은 없다.
문서 범위/공백·내부 링크·fence·legacy fixture 불변을 검증한다. 제품 테스트/Windows CI/ComfyUI는
이번 문서 변경에서 실행하지 않았다. 다른 미응답 정책과 W07 후속 구현 게이트는 유지한다.
아래는 이전 정책 조율 이력이며 Q-UNDER의 응답 대기 기록은 위 최신 확정으로 대체한다.

## W07 명시 후보·조합·기본 P/N 응답 반영 — 문서만 갱신

2026-10-16 KST main `b3867c8`(PR #76 병합)와 별도 열린 Docker 문서 PR #35를 확인했다.
D06-a A(신규 공유 항목 명시 연결), D06-d A(같은 Level 허용 복장 상태/상황/포즈 조합),
캐릭터 기본 프롬프트 외모/상의 속옷/하의 속옷의 독립 P/N을 기준 문서에 반영했다.
기존 기본 복장 P/N 제안은 대체하며 겉옷 표현은 공유 복장 상태가 담당한다.
미적용 속옷은 P/N 모두 제외, 전체 탈의 Level 3은 양쪽 제외한다. Level 0~2 속옷 적용표는
Q-UNDER로 남겼고 단계 2 누적 의미·D07-a 결합 순서·다른 정책을 임의 확정하지 않았다.
문서 범위/공백·내부 링크·fence·legacy fixture 불변을 검증한다. 제품 코드·migration·실제
프롬프트/이미지/오디오·사용자 자료 변경은 없다. 제품 테스트/Windows CI/ComfyUI는 실행하지 않았다.
W07 전체 미완료이며 후속 구현 착수 게이트는 유지한다. 아래는 이전 검토 이력이다.

## W07 기본값·후보·삭제 정책 응답 반영 — 문서만 갱신

2026-10-16 KST main `2c416fa`(PR #75 병합)를 확인했다. 열린 PR #35는 별도 Docker 문서다.
D-DEFAULT(미설정/대상 누락 시 지정 기본값), D06-b A(기본값까지 없으면 해당 출력 생략),
D06-c 삭제(영향 목록 확인 후 해제·기본 재연결)를 REQUIREMENTS와 계약/후속 검증에 반영했다.
기본값은 stable ID로 식별하고 표시 순서와 분리한다. 음성은 팩 자체 누락과 슬롯 누락을 구분한다.
명단 고정·과거 snapshot/파일·W06 자료는 보존한다. 신규 공유 항목 자동 포함·이동/소속 변경·
D06-d 및 나머지 미응답 정책은 계속 보류다. W07 전체 완료/후속 구현 착수로 표시하지 않는다.
문서 공백·내부 링크·fence·변경 범위·legacy fixture 불변을 검증한다. 제품 코드/자료/seed 변경,
제품 테스트·Windows CI·실제 ComfyUI 실행은 이번 범위에 없다. 아래는 이전 검토 이력이다.

## W07 정책 조율·계약 구체화 — 부분 설계, 응답 대기

2026-10-16 KST 시작 main은 준비 SHA `eaaae74`와 일치했다. #72~#74는 병합됐고
열린 PR은 Docker 문서 #35뿐이었다. `task/w07-policy-contracts`에서 승인된 기준 문서
4개만 갱신했다. AGENTS 및 루트 문서, 실제 CPU/media/sound schema·API·pending event/
정산·replay 경계를 대조했다. 기존 W06 자료/제품 코드는 변경하지 않았다.

- ARCHITECTURE: v1 영문 ID/팩 manifest·폴더·scan/중복/immutable 복사·참조/오류,
  단계별 3종 P/N/asset, event source ordinal·선언/voice 분리, W06 additive 보존,
  선택/좌석/결과 DTO·세대 격리, 정책 조건부 cache/job·기술 검증 경계를 구체화했다.
- REQUIREMENTS: 이미 확정된 사항은 재질문하지 않았다. 기존 미응답 D05~D10과 함께
  각 판 승리·치수/마작 표시·3종 최초 생성·구도 결합·팩 갱신·W06 오디오/대사 이전을
  예시/선택지/권고/영향으로 정리했다. 답변받은 새 정책은 없다.
- TASKS: W08/W08-S/W09/W10/W11/W11-U의 정책/병합 선행·파일 범위·구현 지시·
  검사/금지를 구체화했다. 전체 W07 및 후속 구현은 차단 상태를 유지한다.
- 검증 범위는 문서 diff·공백·로컬 링크·4개 파일 제한·legacy fixture byte 불변·최신 main/PR 재확인이다.
  backend/build/browser/Windows CI·artifact·migration/ComfyUI는 실행하지 않았다.
  새 제품 성공 증거는 없으며 기존 W06 exact-SHA 결과는 아래 이력 그대로다.
- PR #75 검토에서 manifest JSON digest와 참조 파일을 포함한 content digest를 분리했다. JSON이
  같아도 이미지/음성 bytes 변경은 새 revision 후보이며, 동일 content digest만 no-op다. 배포용
  voice 참조는 namespace까지 포함한 `{character_id,id}`, DB는 pack UUID로 대응한다. 이미지팩과
  선택 voice pack의 캐릭터 ID를 강제로 일치시키지 않는다. 오마케 기본 선언 voice 억제는
  미승인 단정 대신 Q-OMAKE-VOICE로 분리했다. 문서/링크/범위를 재검증하며 제품 구현은 없다.
- 다음: REQUIREMENTS 미응답 ID별 정책 조율 후 조건부 schema/API를 최종화하고 후속 착수 게이트를
  재검토한다. D11 콘텐츠/권리·개인 Windows/전원 차단·실제 이미지/오디오/ComfyUI는 계속 미검증이다.
  제품 구현·콘텐츠 생성·사용자 자료 변경·직접 병합·Release/tag 없음.

## 2026-10-16 중간 검토 반영 — 요구/작업 배분 완료, 제품 미구현

기준 main `2000c5141e218700e256ff63ede76938c3bd6c34`(W07 준비 PR #72 병합)에서 사용자
추가 요구를 R20~R29·중간 검토 및 TASKS 배분에 기록했다. stage=Level 0~3 의상 의미는 확정됐고,
각 Level profile/full_body/CG·영문 ID 루트의 배포 폴더·선택/좌석/결과 연출과 뷰어를 후속 범위에 포함한다.

SFX/화면 BGM 각각 단일 팩·파일별 기본 팩 fallback·없으면 무음, 이미지와 독립인 캐릭터별 단일
음성팩·누락 무출력을 새 목표로 반영했다. 사운드 생성은 외부 프로그램, 사용자 제공 기본 음향만
이후 별도 리소스 반영이다. 아직 제공 파일/권리를 확인하거나 이미지/오디오를 생성·seed하지 않았다.

W06의 현재 UUID 업로드·6개 선언 SFX/BGM 순환 목록을 새 폴더팩/voice/패 타격 이벤트의 구현으로
간주하지 않는다. W07 계약→W08 등록/팩 기반→W08-S 음향팩→W09 대사/음성→W10/W11 생성→
W11-U 선택/대국/결과 UI→W12 배포/실기 순으로 배분했다. 기존 회귀와 저장/파일은 보존한다.

사용자 재확인 반영: D04-count는 기존 미완료 `<3` 유지(미완료 1~2명일 때 완료 NPC 허용)로 종료했고
조건부 W06-D 변경은 불필요하다. D10-text-voice는 기본 선언의 간단한 공통 화면 텍스트와
actor 캐릭터 선택 음성팩 재생으로 확정했다. 이 분리는 W08-S/W09의 후속 계약/검증에 반영한다.
단계별 이미지 생성/캐시 시점, 각 판 승리 event와 기타 미응답 W07 선택지도 계약 단계에 남긴다.

두 재확인도 AGENTS/REQUIREMENTS/ARCHITECTURE/TASKS/CURRENT_STATE에 반영했다.
이번 변경은 이 기준 문서 5개뿐이다.
공백·링크·변경 범위 검증을 수행하며 제품 코드·DB·사용자 파일/콘텐츠 변경과 새 Windows CI는 실행하지 않는다.
제품 테스트를 새로 통과했다고 주장하지 않고 기존 W06 exact-SHA 검증은 아래 이력으로 보존한다.

## W07 설계 준비 — 문서 작성·정책 응답 대기

- 확인일 2026-10-16(KST), 분석 main `1b548ae8ca901e97407cd02ccc45973a1539add7`.
  Git main과 GitHub PR #70의 `merged=true`/merge commit을 대조했다. PR #70은 병합 완료이며
  W06-C 최종 source `efd5a03`의 검증 기록은 아래에 보존한다. 열린 PR은 #35(기존 Docker 문서)이며
  이번 분석 당시 W07 동일 브랜치/PR은 없었다. #35는 수정하지 않았다.
- `task/w07-content-contract`에서 루트 기준 문서와 CPU 대사·CG·event·replay·local media/진행·
  frontend 및 관련 tests를 읽고 R07~R14를 대조했다. 현재 CPU별 대사/단계 CG·W06 presentation은
  재사용 가능하지만 공유 Level/후보/P/N/선택 저장·ComfyUI/cache는 없다.
- REQUIREMENTS에 D05~D10 질문별 예시/선택지/영향/권고·막는 Task를 정리했다. 확정 정책은
  재질문하지 않으며 모든 권고는 미승인이다. ARCHITECTURE에 새 관계/API/UI 책임·이전/seed 호환·
  RNG 분리·event identity/지연 결과 격리·파일 보존·승인 뒤 검증 예제를 작성했다.
  TASKS는 W07 준비와 전체 완료를 구분하고 W08~W11 구현 경계·착수 게이트·다음 문서 지시문을 남긴다.
- 소스 대조에서 기존 “match_first/last 연결 없음”은 웹/초기 baseline 설명이며 현재 local 보충 CPU는
  해당 승패 대사를 정산 presentation에 고정한다. 아래 구현 표를 웹 baseline로 명시해 혼동을 줄인다.
  기존 CG slot은 교체 가능한 참조이며 W06 immutable media와 다르다. 생성 cache로 무조건 전용하지 않는다.
- 이번 검증은 문서 diff/공백·로컬 링크 38개·질문 ID 15개/관계·기준 SHA와 변경 범위 확인이며
  모두 통과했다. 기존 legacy replay fixture의 원본 byte 일치와 승인된 문서 4개만 변경됨도 확인했다.
  제품 코드·의존성·migration·workflow 변경/실행 및 새 backend/browser/build/Windows CI·artifact
  검증은 하지 않았다. 기존 W06 검증을 이번 W07 결과로 재분류하지 않는다.
- 제품 구현·콘텐츠 생성·사용자 자료 작업·ComfyUI 실행·직접 병합·Release/tag 없음.
  W07 전체는 미완료다. 사용자 응답 후 구체 schema/API/동시성·생성 입력/job 수명 계약 검토가 필요하다.
  D11 실제 콘텐츠/권리, 개인 Windows PC·전원 차단 및 실제 CG/오디오/ComfyUI 출력은 계속 미검증이다.
- PR #72의 설계 준비 문서를 검토했다. 변경은 기준 문서 4개뿐이며 제품 diff 없음·공백 검사·질문 ID와
  참조 소스를 대조했다. 미승인 권고와 확정 정책의 구분을 유지하며 문서 준비 결과만 검토 통과다.
  병합 상태/SHA는 PR #72/Git을 따른다. 일부 질문 응답이나 문서 병합은 나머지 권고의 승인이 아니다.

## W06-C PR #70 — 최종 검토 통과

확인일 2026-10-16(KST), 최신 main `4b170f83545f338c66f2888a6d641f00ba908444`.
최초 검토 head는 `b8065358e60c43314ac16c599013158f7c019c96`(제품 `567a1a3`)이다.
기존 `task/w06-c-sound-ending`과 열린 PR #70을 유지했다. 아래 수정 전 재현을 보존하고,
회귀·Windows 검증을 통과한 보완을 PR #70에 갱신했다. W06-A 정책과 콘텐츠 범위는 변경하지 않았다.

### 재현·코드 대조 결과

| 우선 | 항목 | 확인한 동작과 기대값 |
|---|---|---|
| P1 | 한 곡 BGM 반복 | 실제 `BackgroundMusic` 함수를 Vite Oxc로 변환해 hook/Audio 모의 실행. A 한 곡 재생 후 ended를 전달해도 Audio 인스턴스 1개·play 1회에 멈춤. 같은 trackId setState가 다음 재생을 만들지 않음. 한 곡도 계속 순환해야 함 |
| P1 | BGM 변경/늦은 callback | A 재생 중 [A,B]→[B,A] 변경 시 기존 A pause 1회·새 Audio 생성으로 곡을 재시작. 폐기한 A의 ended를 나중에 호출하면 현재 A가 B로 바뀜. 현재 곡을 유지하고 이전 audio callback을 무효화해야 함. 같은 ID의 media URL 교체도 현재 dependency로는 새 재생에 반영되지 않는 경로가 있음 |
| P1 | 마지막 론·쯔모 효과음 취소 | 실제 `connectGame`/`stopGameAudio`를 모의 WebSocket/지연 media Promise로 실행. sound_effect(ron)→match_complete→media 응답 순서에서 play 0회·blob revoke. backend도 SFX 뒤 match_complete를 보내므로 결과 처리의 stopGameAudio가 마지막 정상 SFX를 취소함. 정산된 마지막 효과음도 한 번 재생되어야 함 |
| P2 | 비활성 BGM 선택 해제 UI | 임시 실제 runtime에서 선택 곡 비활성화 후 GET은 ID 보존·available=false, 그대로 PUT은 400. `LocalSoundPanel` 코드는 active/available 곡만 checkbox로 제공하고 선택 순서 목록에는 이동 버튼만 있어 그 ID를 제거할 수 없음(코드 대조, 실제 DOM 미실행). unavailable 참조를 명시적으로 해제하고 선택을 저장할 수 있어야 함 |
| P2 | 비활성화 후 새 엔딩 음악 | 임시 실제 API에서 엔딩 음악 등록→track 비활성화→전원 stage3 명단 확정 시 새 ending payload가 비활성 track의 asset을 snapshot하고 resolved music.available=true. 새 재생의 unavailable/무음 계약을 확인·보완해야 함. 비활성화 전에 이미 만들어진 pending payload의 immutable 참조는 계속 유지해야 함 |

위 모의 검사는 실제 source 함수 실행이며 브라우저 DOM/실제 codec/실기 오디오 출력의 증거가 아니다.
기존 `local-sound.browser.mjs`는 SFX 중복 검사를 담고 있으나 작성 당시 로컬에서 미실행이고,
Windows packaged smoke의 추가 두 검사는 설정 화면/무음·미등록 기본값이다. 위 BGM·지연 SFX
실패를 검증하지 않은 21 checks 성공을 실제 재생 회귀 통과로 간주하지 않는다.

### 성공 증거와 범위

- 재검증 Linux: backend unittest 100개/40.720초, dialogue pytest 10개/0.09초, frontend production build,
  Node 종료 회귀 3개 통과. 사용자 자료 대신 소유 임시 runtime/file fixture를 사용했다.
- head `b806535`의 Windows W04 run `38812476825`, W05 PR `38812477096`/push `38812469230` success.
  PR artifact `12009995428`(203,331,514 bytes)의 `source-sha.txt`가 head와 일치한다.
  다운로드 archive SHA256 `8c82a3ae15b2713fe88643a65d7beb88e2ad879817d876c088877fed1bb62770`,
  내부 Windows ZIP SHA256 `33d17fa62395c0483614d11aec7350812e44c04d100549edf27d9a56414efc81`를 대조했다.
  artifact unittest 100개/79.698초 OK, renderer passed=true/21 checks를 확인했다.
- 개인 Windows PC/전원 차단 내구성·실제 CG 표시/오디오 출력(D11)은 계속 미검증이다.
  현재 결함은 실제 사용자 파일 없이 재현 가능한 제어 흐름 문제이므로 D11 대기로 미루지 않는다.

### 보완 후 검증

- 보완 source SHA `e9918fec249e909faa135227399e96136d2b984e`는 이 문서 기록 전의 제품·검사 head다.
  BGM 1곡 반복/순서 변경 시 현재 곡 유지/동일 ID의 media 교체/낡은 callback 차단, 파일 실패와
  autoplay 재시도, 비활성 효과음·BGM·엔딩 선택 해제, 최종 SFX와 `match_complete` 순서 및 reset 뒤
  지연 SFX 차단, 새 ending의 비활성 음악 미참조와 기존 pending snapshot 보존을 추가 검사했다.
- Linux: backend unittest 100, `test_local_sound` 6, dialogue pytest 10, frontend production build,
  Node 종료 회귀 3 통과. 브라우저 테스트는 로컬 Chromium 미설치/CDN archive 손상으로 실행하지 못했으며,
  Windows hosted Playwright Chromium에서 실제 renderer DOM과 mock Audio를 실행했다.
- Windows Server 2022 x64 exact source: W04 PR run [38823272350](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38823272350),
  W05 push run [38823267255](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38823267255) 통과.
  W05 PR run [38823272327](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38823272327)도 같은 SHA에서 통과했다. push artifact
  `12012999384`의 `source-sha.txt`가 SHA와 일치한다. artifact ZIP SHA256
  `839804e93f47eadc5ffbbb8c488fc3b3667a312819b2da3b48bdc2732a2961f3`, 내부 Windows ZIP SHA256
  `deca88e1ab2ee99b44e7f3773ccedebbafc12aa30e315ace9740af0dbde716e4`를 대조했다. artifact는
  unittest 100/77.065초, dialogue pytest 10, renderer `passed: true`/22 checks, 한 곡 mock 재생,
  일반 대국/재시작/종료 smoke를 기록한다. 업로드 artifact digest와 다운로드 archive SHA가 일치한다.
- 실제 CG/음악 콘텐츠·기기 출력과 개인 Windows PC/전원 차단 내구성(D11)은 미검증이다. 열린 PR #70은
  병합하지 않았고 Release/tag/W07은 수행하지 않았다. 이후 문서 전용 commit의 exact-SHA Windows 결과는
  아래 추가 기록으로 남긴다.

문서 전용 head `46478adf02f82b8ed90d6e9e4a4f71e55d340c04`에서도 W05 push run
`38824131192`가 통과했다. artifact `12014620725` source SHA는 해당 head와 일치하고 outer archive
SHA256 `741e25cb2b30cbf501624e9c3235bfcad6918997a7d6471a12f83546c4cf4541`, 내부 Windows ZIP SHA256
`7eb0393d43d2158c95d83f29655125f3b587346f7952335ebc8eb4d8ff40c0ee`를 대조했다. 이 문서 추가는
제품 코드·검사 경로를 바꾸지 않는다.

### 최종 재검토 (2026-10-16 KST)

최종 검증 source는 `efd5a0316ff4f3f6f51c05d24566c0b1b5829157`이다. 이전 보완 source의
핵심 5개 항목을 source 함수 모의 검사·API·실제 Windows browser 검사로 다시 대조했다.
검토에서 수동 BGM 재생 응답과 SFX play rejection에도 현재 Audio/세대 검사를 추가했다.
교체 전 BGM 재시도 실패와 초기화 전 SFX 실패가 나중에 새 화면의 오류를 켜지 않는 회귀를 보강했다.
지연 SFX fetch 검사는 응답 완료까지 기다려 초기화 뒤 Audio가 만들어지지 않음을 판정한다.

- Linux unittest 100개/38.172초, dialogue pytest 10개/0.09초, 수정 renderer production build,
  Node 종료 회귀 3개 통과.
- Windows Server 2022 W04 PR run `38826559169`, W05 PR `38826559160`/push `38826553799` 모두 success.
  최종 browser mock 재생·packaged renderer·일반 종료/같은 data root 재시작을 통과했다.
- artifact/source/내외 ZIP 및 renderer/browser 증거: push artifact `12015980287`(203,332,722 bytes, 2026-10-30 만료)의 source SHA가 위 source와 일치.
  API digest와 다운로드 archive SHA256은 `149c355acba76e972c03f0daa6880d9fee16d1218d547bb1b2fd95065e1777a3`,
  내부 Windows ZIP SHA256은 `973ebb7d481c1fa69c3d013b9ef65b26544fa6c71d690479a1f24f56a32fda56`.
  artifact unittest 100개/80.676초 OK, browser PASS, renderer passed=true/22 checks와
  두 일반 모드 종료/재시작 JSON의 engine→창→host 종료 순서를 대조했다.
- 중간 source `04cae5f`는 browser를 통과했지만 PR run `38826086985`의 packaged 검사에서
  stale-confirm reset 직후 다음 명단 선택 대기에 실패했다(artifact `12015024353`). 같은 source의
  push run `38826082557`은 전체 통과했다. 제목만 확인하던 harness를 실제 enabled CPU 카드
  3개 이상까지 기다리도록 보완했으며, 제한 시간·검사 범위·제품 복구 동작은 바꾸지 않았다.
  위 최종 source의 PR/push 모두 통과한 결과로 다시 확인했다. 이전 실패/성공 이력은 보존한다.

최종 검토를 통과했다. 이 source 뒤 문서 commit과 병합 상태/SHA는 PR #70/Git을 따른다.
실제 콘텐츠/기기 출력(D11), 개인 Windows PC와 전원 차단 내구성은 계속 미검증이다.
W07 제품 구현·콘텐츠 생성·Release/tag는 수행하지 않았다.

## W06-B PR #68 — 최종 검토 통과

확인일 2026-10-15. 최신 기준 main은 `1646bd9580d7aaa34d1d793b7272d74163fc57f2`;
기준 문서 병합 충돌은 작업 브랜치의 `ece3a08b639d1da4b67db8ca543ede728ebbb59d`에서 정리했다.
기존 `task/w06-b-progression` 및 PR #68에서 최종 검토를 통과했다. 병합 상태/SHA는 PR과 Git을 따른다.
W06-A 계약과 정책은 변경하지 않았다.

### 보완 전 재현과 수정

| 회귀 | 보완 전 확인 | 보완 |
|---|---|---|
| reset 후 legacy 취소 대국의 늦은 정산 | 임시 파일 DB에서 `rules_snapshot=NULL` legacy record를 reset해 cancelled/stage 0으로 만든 뒤, 완료 객체의 `settle/commit`이 completed/stage 1로 되돌리는 것을 재현 | cached settlement 반환 전 DB status/generation 검증. legacy·version 2 모두 현재 generation과 active record 확인. reset/정산 순서, commit 실패·재시작을 회귀로 고정 |
| 웹 member HP 0 대국 생성 | 보완 전 `POST /api/game/sessions`가 409 대신 201 반환 | 웹 legacy 경로의 member/HP precondition 복원. 새 local 규칙은 기존대로 HP에 의존하지 않음 |
| 완료 명단 확정 | 실제 renderer 함수 harness에서 `ending_pending` 응답 후 상대 선택 화면에 남음 | ending/ack 화면으로 전환하고 실제 packaged renderer smoke에서 검증 |
| reset/ack 오류·응답 유실 | commit 후 reset 응답 유실 때 GET play는 새 generation인데 화면/연결 불일치. 미commit 오류 뒤 기존 active turn 복구와 ack 유실 복구 누락 | GET play 권위 상태로 roster/active/ending 화면과 연결 복구. reset 반복 전송·사용자 자료 삭제 없음 |
| 초기화 뒤 오래된 응답 | 지연된 이전 generation start 응답이 reset 후 새 roster 화면/연결을 덮는 것을 harness로 재현 | start/confirm/ack 및 화면 load를 generation+request token으로 검증. busy 상태와 별개로 강제 순서 회귀 |

보완 전 legacy DB reset/settlement와 HP=0 API 실패를 기록했고, frontend harness에서 ending/reset/stale
start 불일치를 재현했다. 수정 후 backend·dialogue·frontend 검사와 Windows packaged smoke가 통과했다.
기존 성공 이력 run `38702603775` / artifact `11956942201`은 보존했다. 보완 전 성공만으로 위 결함이
해소됐다고 간주하지 않았다.

### 최종 검토와 exact-SHA 증거

최종 검증 source는 `300892a93d923e0565c9c668ffb8a1a7b635cfd6`이다. 제품 수정은 기존
`9bab63ecdfe7775130f98791f44b306e8eaac429`와 같고, 검토에서 desktop smoke만 보강했다.
기존 smoke는 미commit reset 뒤 화면을 즉시 검사하고 renderer를 reload했으므로 복구된 socket의
실제 행동 성공을 충분히 입증하지 못했다. 주입 실행·busy 해제·행동 가능 상태를 기다리고,
reload 없이 다음 행동을 완료한 후 기존 전체 대국/재기동 검사를 이어가도록 바꿨다.

- Windows Server 2022 W05 [push run 38808520631](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38808520631),
  [PR run 38808528623](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38808528623),
  W04 [run 38808528770](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38808528770) 모두 success.
- 다운로드한 push artifact `12007637653`(203,293,872 bytes, 2026-10-29 만료)의 `source-sha.txt`가
  위 SHA와 일치한다. API digest와 다운로드 archive SHA256은
  `7e720ec8322b41dd65face8ac2a0bd3e713e4bfbbeb9d737b058f4b47bafb8d9`;
  내부 Windows ZIP SHA256은 `c71f7abc7f942a353b14cf95ba6d2701e51913e68bc2bbf44654d451153705a7`.
- artifact unittest 94개/73.997초, dialogue pytest 10개/0.15초 통과. frontend 및 Electron build 통과.
  renderer `passed: true`, 19 checks 중 `next action completed after reset failure recovery without renderer reload`를 확인했다.
  reset/ack 응답 유실, stale confirm/start 차단, 완료 명단 ending 화면, 정상 전체 대국,
  active/completed 재기동·정산 중복 없음도 통과했다. 일반 모드 종료와 같은 data root 재실행의
  engine 종료→창 파괴→host 종료 순서를 JSON에서 대조했다.
- Linux에서도 unittest 94개, dialogue pytest 10개, frontend production build 및 Node 종료 회귀 3개가 통과했다.
- 이전 `9bab63e` run `38778254234`/artifact `11994663467`, 문서 head `cf197c7` run `38780085847`/
  artifact `11995014249`와 최초 run `38702603775`/artifact `11956942201`은 검증 이력으로 보존한다.
  `778970f`의 일반 대국 실패와 이후 reload 우회는 위의 무reload 검사 성공으로 다시 검증했다.

테스트는 사용자 LocalAppData가 아닌 소유 임시 root를 사용했다. 개인 Windows PC, OS 전원 차단
내구성, 실제 ending CG/음악 재생은 미검증이다. 실제 사운드/엔딩 리소스 연결은 W06-C에 남긴다.
Release/tag는 수행하지 않았다. 이 source 뒤 문서만 변경한 commit은 PR/Git으로 확인한다.

## 기준

- 확인일: 2026-10-15. W05 보완 기준 main `4f09869`; PR #63 수정 source SHA는 `7d9a20b97f7ef60b5dda4a43a24d3cbf08723ffb`.
- W04 제품 코드 검증 SHA는 `455d400c4a8ddf11eaa0e3d676317c80b9a553b2`이다. PR #61은 main에 병합됐다. W05 PR #63은 최종 검토와 Windows 검증을 마쳤다. 최신 병합 상태/SHA는 PR #63 및 Git을 따른다.
- PR #56(W00)·#57(W01)·#58(인계)는 main에 병합됐다. 열린 #35는 기존 Docker 문서이며 건드리지 않는다.
- W01 baseline 이후 W04는 local runtime·DB 연결/권한 경계·관련 회귀만 추가/수정했다.
  CPU/규칙/정산 핵심·legacy fixture·기존 frontend는 보존했다.
- W02 PR #59를 병합했다. 검증 code SHA 이후 변경은 기준 문서 4개뿐이며,
  CI job/다운로드 artifact의 source SHA·내외 ZIP hash·browser/frozen/renderer 증거를 다시 대조했다.
  이번 검토는 기존 Windows 실행 증거 검토이며 Windows를 새로 실행한 결과가 아니다.
- 로컬 저장/runtime은 W04, Windows 실행창·번들·로그인 없는 진입은 W05 PR #63에 구현됐다. 정확한 W05 Windows 결과와 남은 사용자 PC 제한은 아래에서 구분한다.
- Wayward 참고는 W00의 `5d80f118c590319881be34faba8214a0c3765fc2` 조사뿐이다.
  W02는 참고 코드 복사·ZIP 분석·이미지 생성·사용자 데이터 연결을 하지 않는다.

## W06-A — 기술 계약 검토 통과

분석 기준 최신 main은 준비 SHA와 같은 `e48aae94e37f19fc445717f456b18321354b30a2`이다.
W05 PR #63 및 정책 문서 PR #66이 병합돼 있다. 열린 PR #35는 기존 Docker 문서이며 수정하지 않았다.
REQUIREMENTS D04/R16~R19는 확정 정책이고, ARCHITECTURE의 W06-A 절에 다음을 설계했다.

- 공통 자료/현재 플레이 명단·stage/대국 snapshot/상시 사운드 설정 관계와 additive migration.
- local 전용 진행 규칙 version과 effective_tier snapshot, 기존 active 원본 replay/정산·completed 보존.
- 세대 기반 API/WS·cache·UI 지연 응답 차단, writer 순서·정산 exactly-once·자료 보존 초기화.
- 전체 완료의 pending event/payload·명시 ack→omake·재시작, 최소 media 등록/사운드 선택·재생/누락 계약.
- 명단 참조 CPU 비활성화 차단, 오마케 캐릭터 이벤트 억제와 기본 마작 SFX 분리.

TASKS에 B/C 파일 범위·의존·회귀표와 저성능 Work용 전체 지시문을 작성했다. B 검토/병합 후 C를
순차 수행한다. D05~D11 콘텐츠/생성 정책은 미확정으로 유지한다. 추가 제품 정책은 확정하지 않았다.

당시 W06-A 문서 검토의 검증은 소스/문서 대조와 diff·링크/필수 항목 확인뿐이었다.
이 절은 W06-B 구현 전의 역사적 상태를 기록하며, 당시에는 제품 변경·migration 실행·사용자 자료 수정·
새 Linux/Windows 실행을 하지 않았다. 당시 제품은 HP/완료 CPU 제외 규칙이었고 고정 명단·초기화·
엔딩/오마케·사운드 관리는 미구현이었다. 실제 리소스도 생성/등록하지 않았다.
2026-10-15 검토에서 완료 CPU도 포함하는 최초 명단 후보 API와 local HTTP의 response 전 commit·
실패 응답 검증을 명확히 했다. 이후 W06-B 보완 결과는 이 문서 앞의 “W06-B PR #68 보완” 절을 따른다.
실제 CG/오디오 출력은
C에서 자료가 제공된 범위만 검증하고 없으면 D11 실측 대기로 남긴다.

## W05 최종 검토 — 종료 및 실제 포트 충돌 검증

일반 종료 보완을 재검토하고 Node 종료 순서 회귀 3개를 다시 통과했다. 이전 final head
`5b3c58a45ff8289d6ea91d0d26a4bc17860900c5`의 Windows run 38688037360/artifact 11950014750을
내려받아 source SHA, archive SHA256 `1a66154bdb9275157f01ff44b136cd2d59e309fbf24ba1281c9f16df234168a8`,
내부 ZIP `cbcaf0da8e3752e92d83cd2860e2e100c229af44c3cce4af82a95a44beddbe76` 및
두 일반 모드 실행의 engine close→window destroy→host exit(0)를 확인했다.

추가 검토에서 포트 충돌 smoke의 collision-data 폴더가 없어 engine bind 전에 spawn/cwd 오류로
통과할 수 있음을 발견했다. 같은 spawn 조건의 Node 검사에서 ENOENT/engine 미실행을 재현했다.
`a45abce5856bba4870d9a1ebe99690204808468c`는 시험 폴더를 먼저 만들고 실제 Windows bind
오류(10048/address already in use)와 무관 listener 생존을 모두 확인한다. 제품 게임 동작 변경은 없다.
Linux 실제 engine 점유 포트 시험도 bind 오류로 실패하고 무관 listener는 유지됐다.
Linux source unittest 81개(35.923초), 대사 pytest 10개(0.09초), Node 회귀 3개 통과.

최종 code의 Windows Server 2022 x64 [push CI 38691436063](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38691436063)은
unittest 81/pytest 10·React build·engine freeze/Electron package·renderer smoke·일반 모드
종료/동일 data-root 재실행·ZIP 생성 모두 success다. exact-source artifact `11951374188`
`w05-windows-a45abce5856bba4870d9a1ebe99690204808468c`의 archive SHA256은
`3e710f282b37c67c13cb044dcc43f9882f34a82c2c80f0e77ad0ab17852eb38f`이며 2026-10-29 만료다.
다운로드 archive/source-sha 및 로그의 unittest 81(62.085초)/pytest 10(0.14초)을 대조했다.
내부 Windows ZIP SHA256 `821052f34c1b0c207807dd5a5e1eecf19f15e423bc739e344317fea3ff916e55`도
기록과 일치했다. Renderer evidence에서 실제 Errno/WinError 10048과 무관 listener 보존,
일반 모드 두 실행의 child close→창 파괴→host exit(0) 순서를 다시 확인했다.
기존 검증은 아래에 보존한다. 후속 문서 commit은 이 code와 동일한 제품/검사에 한해서만
위 결과를 이어받는다. 개인 PC/물리 X·Alt+F4/OS network-off/clean-machine VC runtime/전원 차단과
장기 Python patch는 미검증이다. W05 검토를 통과했으며 다음은 D04 정책 결정이다.
W06 구현·Release/tag는 하지 않는다.

## W05 PR #63 — 일반 모드 종료 보완 및 Windows 검증

검토 기준은 당시 PR head `5d249962dd1aff9d943cc2f4fc0e62a0a6a4735f`였다. source 제어 흐름에서
`finishQuit()`가 마지막 창을 파괴한 뒤 `window-all-closed → app.quit()`가 엔진 정지보다 먼저
허용되는 것을 확인했다. 당시 Windows `--smoke` 증거는 해당 분기를 실행하지 않아 이 결함을
보장하지 않았다. 기존 검토와 code `c9cb8515`의 성공 근거는 아래에 보존한다.

보완 source `7d9a20b97f7ef60b5dda4a43a24d3cbf08723ffb`는 종료 요청을 단일 공유 Promise로 조정한다.
창 닫기와 `app.quit()`/`window-all-closed`가 같은 경로를 사용하고, 즉시 창 입력을 막은 뒤
소유 engine의 graceful close/종료를 기다린다. 정상 close 또는 timeout 후 해당 소유 child를 회수한
뒤 창을 파괴하고 최종 Electron 종료를 허용한다. child 회수에 실패하면 종료를 허용하지 않고
다시 시도할 수 있다. 다른 프로세스에는 종료 신호를 보내지 않는다.

로컬 Linux/Python 3.12.14에서 backend unittest 81개, 대사 pytest 10개, `npm ci && npm run build`,
Node 종료 조정 회귀 3개와 JS syntax 검사가 통과했다. 변경 전 재현은 기존 검토 당시 Node
VM/EventEmitter source-control-flow 실행 결과이며 Windows 실기 결과와 구분한다.

수정 SHA의 Windows Server 2022 x64 push run [38687286437](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38687286437)은 전체 성공했다. Python 3.12.10 x64 / Node 24.19.0에서 backend unittest 81,
대사 pytest 10, React production build, frozen engine, Electron package와 두 packaged 실행 경로가
통과했다. artifact `11950398716` (`w05-windows-7d9a20b97f7ef60b5dda4a43a24d3cbf08723ffb`)의
`source-sha.txt`는 정확히 수정 SHA와 일치했다. 내부 Windows ZIP SHA256은
`8b5ba202b3d5d12f46b09dd95948cf309f003004f8663b85e0fe43a1b4e23baa`이며 artifact 기록값과
내부 archive를 내려받아 직접 계산한 값이 일치했다.

기존 packaged renderer smoke도 유지했다: 로그인 없는 진입·프로필 이름 저장·active 대국 엔진
재시작 복구·실제 대국 완료·완료 결과 재접속/중복 정산 방지 등 11개 check가 모두 통과했다.
별도 명시 임시 data root에서 실행한 packaged 일반 모드(`--smoke` 없음)는 programmatic
`window.close()` 후 반복 `app.quit()`을 받았다. 두 실행 모두 Windows evidence에서
`engine PID close → window destroyed → host PID exit(0)` 순서가 확인됐고, nonresponsive 테스트
child는 별도 PID로 timeout 강제 회수됐다. 같은 data root로 두 번째 packaged 실행도 성공했다.

기존 성공 code `c9cb8515a50c4a2387ca70a5be42b11cf9a7029e`의 run `38666626946`/artifact
`11942211016` 이력은 보존한다. 그 artifact는 종료 결함을 검사하지 않았다. 새 결과와 혼동하지 않는다.
Windows 10/11 개인 PC, 물리 title-bar X/Alt+F4, OS 수준 internet-off, clean-machine VC runtime,
전원 차단 durability, 장기 Python 보안 patch 공급은 미검증이다. PR #63은 열려 있고 병합·Release/tag는
하지 않았다. 당시 D04 미결로 W06은 시작하지 않았으며, 이후 확정 정책은 위 W06 절을 따른다.
## W04 PR #61 — 최종 검토·보완 결과

2026-10-15 W04 보완과 재검토를 수행했다. 사용자 프로필 수정은 요청 Session과 공유하고,
local 읽기/쓰기 경계를 분리하며 파일 DB 정산 commit 실패 복구를 검사한다.
최종 재검토에서 기본 SQLite engine에 남은 조회 잠금과 고립 surrogate 토큰 예외를 추가 재현했다.
해당 두 회귀 검사는 수정 전 각각 database is locked/UnicodeEncodeError로 실패했다.
`455d400`은 SQLite 설정을 local opt-in에만 설치하고 모든 비ASCII 토큰을 정상 거절한다.
기본 engine의 원본 main 동시 읽기·FK 의미, local의 FK/쓰기 직렬화·이름/정산 복구를 함께 검증했다.
최종 Linux Python 3.12.14/RiichiEnv 0.4.8 unittest 81개(35.752초), 대사 pytest 10개(0.10초) 통과.
Windows 최종 검증: code `455d400c4a8ddf11eaa0e3d676317c80b9a553b2`의 push
[CI 38660753146](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38660753146) 전체 success.
Windows Server 2022 x64(build 20348)/Python 3.12.10/Node 24.19.0에서 unittest 81개
(48.885초), 대사 pytest 10개(0.10초), frontend build를 통과했다. artifact `11937654546`
`w04-windows-455d400c4a8ddf11eaa0e3d676317c80b9a553b2`의 다운로드 ZIP SHA256
`3c628bcf53b70c10538b43732277400a790cc253a5805afae13a2cdb407b0631`이 Actions digest와
일치하고 source-sha 및 로그의 81/10 통과를 대조했다. 이후 인계 commit은 문서만 바꾸며
이 code SHA와 동일한 제품/검사/workflow에 한해 위 결과를 이어받는다.
기존 성공 이력은 아래에 보존한다. W05 shell/사용자 Windows/전원 차단 성공으로 해석하지 않는다.

이전 W04 검증 이력: code SHA `3081dc56a2be95dd30ce0fa78a413da9b4bfeb29`에서 Linux backend
unittest 78/대사 pytest 10/frontend build를 통과했다. Windows Server 2022 Datacenter x64
(build 20348), Python 3.12.10, Node 24.19.0의 run 38572718064에서 unittest 78(54.438초),
pytest 10(0.13초), frontend build가 통과했다. artifact `w04-windows-3081dc56a2be95dd30ce0fa78a413da9b4bfeb29`
(ID `11897978928`, SHA256 `a4bb5b49a4a4886c415c0883e4b20b7601371d139abda261f3edba8c4e5bdca8`,
2026-10-28 만료)의 source SHA와 test 로그를 확인한 기록을 보존한다. 기존 결과는 새 수정 SHA 검증이 아니다.

이번 보완 코드는 local auth dependency가 요청 transaction의 User를 그대로 반환하도록 바꾸고,
capability의 ASCII 형식을 확인해 비교한다. local session에 쓰기 의도를 명시해 해당 연결을 조회 전에
`BEGIN IMMEDIATE`로 시작하며 일반 읽기는 writer reservation을 얻지 않는다. 기본 engine의 기존
SQLite transaction 기본값은 유지한다. profile PATCH→GET→재시작, member/admin/REST 및 WS의
malformed·비ASCII·누락·이전 실행 capability 거절, 동시 읽기·writer·stale action, admin write,
파일 DB 최종 행동 commit 후 정산 commit 실패/rollback·cache eviction·재기동 후 반복 재접속
검사를 추가했다. 아래 결과는 이번 로컬 실행 결과이며 정확한 GitHub Windows CI/artifact 검증은
push 후 별도로 확인한다.

| 발견 | 보완 결과 |
|---|---|
| 이름 편집 비영속 | 보완 완료: local auth와 endpoint가 같은 요청 Session의 User를 공유하고 PATCH→GET→별도 DB/runtime 재시작 후 이름을 확인 |
| 잘못된 토큰의 비정상 예외 | 보완 완료: ASCII 확인과 상수 시간 비교로 REST/member/admin 및 WS에서 비ASCII·잘못됨·누락·이전 실행 토큰을 거절하고 WS 4401 close 확인. 응답에 secret을 내보내지 않음 |
| 조회 transaction의 배타 잠금 | 보완 완료: 로컬 read는 deferred transaction, local HTTP write/WS action·settlement는 첫 DB 조회 전 BEGIN IMMEDIATE. 별도 writer 예약 중 read 성공, 동시 active writer 및 stale action 검사 |

정산 검사는 local runtime의 파일 DB에서 마지막 행동 commit 이후 정산 commit 실패만 주입했다.
실패 시 행동 log/status/HP/stage 원자성과 cache eviction을 확인하고, 새 runtime의 재접속/반복
재접속에서 같은 결과 및 한 번의 진행도 변경만 남는지 검사한다. 기존 마지막 행동 후 미정산 복구
검사와 별도다. 기존 78+10/Windows 성공 이력은 보존하며 이번 Linux 검사에서 Windows/browser를
실행했다고 기록하지 않는다.

이번 Linux/Python 3.12.14 임시 venv: backend unittest 81개(35.058초), 대사 pytest 10개(0.11초),
frontend `npm ci && npm run build` 통과. 정확한 보완 code SHA `d46782bef4947ff448b2d40555ac4b387b2bc25a`의
Windows Server 2022 Datacenter x64(build 20348), Python 3.12.10, Node 24.19.0 push CI
[run 38659727577](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38659727577)도
unittest 81(68.606초), pytest 10(0.14초), frontend production build와 artifact 수집이 통과했다.
artifact `w04-windows-d46782bef4947ff448b2d40555ac4b387b2bc25a` (ID `11938706685`, SHA256
`c4f778a5cb4fcf51bc73ac59404dd2043c14968c6b77ca2956cb508d0e335bff`, 2026-10-29 만료)의
`source-sha.txt`는 정확히 `d46782bef4947ff448b2d40555ac4b387b2bc25a`이며, 다운로드 ZIP hash와
Actions artifact digest가 일치하고 unittest/pytest 로그를 확인했다. PR-triggered run
38659729790도 전체 성공이나 artifact의 source SHA는 pull_request merge ref이므로 exact branch
검증 근거로는 위 push run을 기록한다. 이는 이전 code SHA의 검증 이력이다. 전원 차단
durability 및 사용자 Windows UI/LocalAppData는 여전히 미검증이다.

## 코드로 확인한 구현 — 웹/초기 baseline

이 표는 W01 당시 웹 경로다. 현재 Windows local 진행/명단/사운드 구현은 앞의 W04~W06 절을 따른다.

| 영역 | 상태/근거 |
|---|---|
| 기본 대국 | RiichiEnv 0.4.8, 사람 1 + CPU 3, `4p-red-east`/Tenhou 기본 규칙 |
| CPU | Tier 0/1/2, 6개 성인 seed, 성향 6개, 선택·stage 난이도 연결 |
| 진행/정산 | 최종 4위만 HP 또는 해당 CPU stage 변경, stage 3 제외, HP 0 게임 오버 |
| 복구 | seed/사람 행동 log/CPU·좌석 snapshot, 각 승인 행동 commit, 재생·중복 정산 방지 |
| 정책 호환 | 새 CPU snapshot policy 2, 기존 누락 policy 1, 108행동 legacy replay fixture |
| 대사/CG | CPU별 이벤트 대사·노출 정책, 결과 stage 대사, 단계 CG 관리자 API 및 회원 해금 표시 |
| 프런트 | 인증·CPU 선택·합법행동·meld/국번호·말풍선·결과·다음 선택·재로그인 복구 |
| 저장/실행 | PostgreSQL/Compose 기본, SQLAlchemy/Alembic 4개 migration; SQLite 테스트 경로 존재 |

6개 행동 이벤트 `riichi/chi/pon/kan/ron/tsumo` 및 defeat-stage 결과가 연결되어 있다.
`game_start`, `match_first/last` seed 문장은 있으나 그 시작/순위 이벤트 표시 연결은 없다.
프로필 key가 없으면 문자 avatar를 표시한다. 프로필 이미지 업로드 및 관리자 웹 UI는 없다.
기본 대국 기능을 재사용할 수 있는 상태이지만 최종 진행 루프/완성 콘텐츠/Windows판 완료가 아니다.

## W02 Windows runtime spike — 기술 검증 완료, 사용자 실기 미검증

기준 main `7523d4177140d303c5f4681c5ff94d92610db227`; W01 제품 baseline과
backend/frontend tree가 동일하다. 격리 코드: `spikes/w02/`, 전용 workflow:
`.github/workflows/w02-spike.yml`. PR #59가 Windows artifact·사용자 결과 첨부 경로다.
제품·CPU/진행·migration/fixture·사용자 자료 변경 없음; D01~D03/D09 기술/프로필 채택은 W03,
당시 CPU 부족/HP 이후 정책은 미확정이었다. 현재 D04 확정은 위 W06 절을 따른다.

### 실측 환경과 명령

Linux: Ubuntu 24.04.3 x64 / Linux 6.18.44, Python 3.12.14, uv 0.12.23,
Node 24.19.0 / npm 11.9.0. 코드 검증 대상 `ec6123616aa389ebba0e5eb3c0aaee6667dd9fab`.
backend 선언 의존성 + test extra/pytest 9.1.1/PyInstaller 6.22.3/setuptools 80.9.0을
`/tmp/nrnf-w02`에 설치했다. W01 의존성 해석 결과와 주요 버전이 같으며 uvloop 0.23.0 등
OS별 의존성은 Windows 환경과 같다고 가정하지 않는다.

```sh
uv venv /tmp/nrnf-w02
uv pip install --python /tmp/nrnf-w02/bin/python -r backend/pyproject.toml --extra test \
  pytest==9.1.1 pyinstaller==6.22.3 setuptools==80.9.0
# backend에서
/tmp/nrnf-w02/bin/python -m unittest discover -s tests -v
/tmp/nrnf-w02/bin/python -m pytest tests/test_dialogue_service.py -v
uv pip install --python /tmp/nrnf-w02/bin/python --no-build-isolation -e .
# 마지막 명령은 알려진 flat-layout 발견 오류 재현용이며 설치 실패가 예상 결과
# frontend에서
npm ci
npm run build
# 루트: Linux에서는 build.py의 engine 수집 단계까지만 별도 실행(Windows shell 아님)
# 생성된 native Linux 엔진 검사
spikes/w02/out/engine/w02-engine/w02-engine regression
```

| Linux 검사 | 실측 결과 | 범위 |
|---|---|---|
| source unittest / 대사 pytest | 72개/32.018초, 10개/0.09초 통과 | 원본 검사 그대로 |
| frontend ci/build | exit 0, Vite 8.3.0 build | 원본 lock/build 그대로 |
| editable 설치 | exit 1, `Multiple top-level packages ... ['app', 'alembic']` | 제품 pyproject 수정 없이 명시 소스 import로 우회 |
| frozen engine regression | 72개/37.861초, 10개/0.08초 통과, exit 0 | namespace/source import 수집 보완 후 결과. 기존 policy 1/2/legacy 검사 포함 |
| frozen 외부 process health/static/재기동 | 2회 health/identity/static HTTP 200, stdin EOF exit 0 | marker-owned 시험 SQLite, head `20260912_0004`, CPU 6/대사 144/CG metadata 슬롯 18; media 이미지 없음 |
| Chromium 확보 | exit 1, ZIP central-directory 오류 재현 | Linux browser 4개 미재실행. Windows 결과와 별개 |

Windows: GitHub hosted Windows Server 2022 Datacenter x64, build 20348.
Python 3.12.10 / Node 24.19.0. W01 Linux 3.12.14와 patch가 다르다. setup-python이
Windows 3.12.14를 제공하지 않아 공식 Windows binary가 있는 3.12.10으로 격리 시험했다.
security-only patch를 어떤 Windows binary 공급 경로로 유지할지는 W03/W12 결정 조건이다.
명령 전문은 workflow와 [spike 실행법](spikes/w02/README.md)에 있다. build 전용 venv의
pip install report, resolved freeze, Windows wheel SHA256, browser/source/frozen 로그 및
ZIP/hash/native data inventory/renderer evidence를 Actions artifact에 수집한다(14일 보존).
Python 범위 의존성은 미래 build 해석/byte 일치까지 보장하지 않는다.

### Windows 정확한 SHA·artifact·결과

실행 code SHA `a9268d4b3b5eed3b55b8b40e2f06bbf28a549cb5`,
[push CI 38567208066](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38567208066) **전체 success**.
[artifact 11896177779](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38567208066/artifacts/11896177779)
`w02-windows-a9268d4b3b5eed3b55b8b40e2f06bbf28a549cb5`, 2026-10-28 만료.
다운로드한 evidence/source-sha·로그·내부 ZIP·metadata와 대조했다. 문서 후속 commit은 Git/PR로
찾으며, 이 code SHA의 spike/workflow/backend/frontend tree가 같을 때만 위 결과를 이어받는다.

| Windows 검사 | 실측 결과 | 범위/제한 |
|---|---|---|
| 선언 의존성·wheelhouse | pip report/freeze/hash 확보, `--no-index --force-reinstall` exit 0 | 격리 venv. 장기 완전 lock/byte 재현과 별개 |
| source unittest / 대사 pytest | 72개/50.665초, 10개/0.13초, exit 0 | UTF-8 모드. policy 1/2/legacy 및 기존 정산/복구 포함 |
| frontend npm ci/build | 각 exit 0 | 원본 product lock/build |
| 기존 browser 4개 | 모두 exit 0 | routed 대사/연결/CG 3개 + 실제 Vite/FastAPI/SQLite 108행동·12행동 후 API 재시작·완료 재접속. W01 Linux 차단이 해결됐다는 뜻은 아님 |
| Windows ZIP 압축 해제 | 한글/공백 `W02 압축 해제` 경로 통과 | 테스트 전용 unsigned ZIP, ASAR 밖의 native engine |
| frozen regression | 72개/51.046초, 10개/0.14초, exit 0 | 추출한 w02-engine.exe, PATH=System32 / PYTHONHOME·PYTHONPATH 비움. 설치된 Python/Node가 없는 clean PC 실기와 별개 |
| Electron same-origin 대국 | `passed=true`, 실제 renderer REST/WS 108행동 | Electron 44.7.2 / Chromium 152.0.7977.149 / 내부 Node 24.21.0. 외부 build Node 24.19.0과 구분 |
| 저장/복구 | 12행동 후 전체 authoritative turn 동일; 완료 재기동 응답·DB 불변 | seed 5/stage 2 시험 주입, policy 2, 점수 `[17000,27700,24700,30600]`, 순위 `[4,2,3,1]`, HP 3→2/stage 유지 |
| ready·포트·소유 종료 | 충돌 WinError 10048/exit 1 거절, unrelated listener 유지; 정상 3회 exit 0/forced=false | 초기 ready 1804ms, 재기동 1163/1156ms; stdin EOF 종료 419/374/303ms. 단일 hosted runner 표본, Windows 사용자 X 클릭 실기/host crash와 별개 |
| 인터넷 | OS 인터넷 차단하지 않음 | renderer non-loopback 차단만 시험. 물리적 오프라인은 사용자 결과 필요 |

`W02-Spike.zip` 205,983,766 bytes(약 196.44 MiB), 압축 해제 478,215,857 bytes,
시험 engine subtree 93,506,175 bytes. pytest/test helper와 넓은 dependency 수집을 포함하므로
제품 최소 용량·성능 추정치로 쓰지 않는다. CPU/RAM 사용량·사용자 PC 속도는 미측정이다.
ZIP SHA256 `313fbd046c006057ea0589b7b4bcb72be4cbd8487eb0426c561d7319f37d4990`;
Actions 바깥 artifact ZIP SHA256 `3dd93a9e455db12e57dcc57253fb0fbd40aa1d35fd4951fea268c50a35b66427`.
내부 ZIP의 Python312/VCRUNTIME140/VCRUNTIME140_1 DLL·RiichiEnv pyd·seed 두 JSON·migration
0001~0004를 확인했다. bootstrap 첫 실행 CPU 6/대사 144/슬롯 18, 재기동 추가 0.
사용자 DB/state 파일은 ZIP에 없고 CG 이미지 생성도 없다.

Git legacy fixture 원본 hash는 보존됐다. Windows checkout의 CRLF 변환으로 ZIP 내 fixture raw
SHA256은 `a6bac607e43bb379abc200a0091cb5ca7c0fc5819bf542647a2fe43b6ae3964c`이다.
313개 CRLF를 LF로 돌리면 원본 blob과 byte 전체가 동일하며 hash `b5144742...`가 일치한다.
기존 108-turn legacy replay 검사도 통과했다. fixture를 현재 정책으로 재생성한 것이 아니며,
Windows artifact의 raw byte hash를 Linux/Git LF hash와 직접 동일하다고 주장하지 않는다.

### 번들·native 조건

- PyInstaller onedir 후보는 `app` import path를 빌드 process의 PYTHONPATH로 지정하고
  testclient/namespace test helper를 명시 수집한다. frozen 런타임은 외부 Python/PYTHONPATH를
  사용하지 않는다. 첫 Linux frozen 시험에서 dynamic import 누락 3개가 있었으며 수집 보완 후
  위 72+10 통과를 확인했다. 오류를 제품 결함 또는 통과 결과로 숨기지 않는다.
- Windows 기본 cp1252에서는 legacy fixture의 encoding 없는 read_text가 실패했다:
  source 72개 중 71개 통과/1 UnicodeDecodeError. 원본 fixture·검사를 그대로 보존하고
  source `PYTHONUTF8=1`, frozen `--python-option 'X utf8'`를 spike에서 지정한다.
- RiichiEnv Windows wheel `riichienv-0.4.8-cp312-cp312-win_amd64.whl` SHA256은
  `50783478d424b0c6f9271bc153e01dc05eff64636be5e0ef4ea10f4e6fd60cd3`.
  Windows wheelhouse hash 및 Linux에서 cross-target 설치한 wheel tag/PE x64를 대조했다.
  `_riichienv.cp312-win_amd64.pyd`의 objdump import: `python312.dll`, `VCRUNTIME140.dll`,
  `bcryptprimitives.dll`, `KERNEL32.dll`, `ntdll.dll`, synch/UCRT math/runtime/heap API sets.
  wheel은 별도 DLL 없이 pyd를 포함하고 PyYAML/IPython을 선언한다. wheel 존재/PE 분석과
  clean Windows의 DLL 로딩 성공은 다르다. Python/C runtime bundle 및 OS 제공 DLL 경계를
  inventory와 실제 실행으로 확인하고 임의 시스템 DLL 복사는 하지 않는다.
- seed JSON·Alembic ini/env/version 0001~0004·원본 legacy fixture·React build를 같은 bundle에
  넣는다. REST/WS와 health는 기존 코드, static mount/port/identity/stdin 수명은 spike만 추가.
  pytest/test helper를 포함한 **시험 번들 크기는 제품 최소 번들 크기가 아니다**.

### 미검증과 재개 조건

실행·지원 OS·저장/인증·배포 방식은 미채택이다. Windows 10/11의 Python 미설치 PC,
OS 수준 인터넷 차단, 사용자 눈으로 UI 종료/재실행, 외부 VC runtime 부재, host 강제 종료/
전원 차단, 동시 writer/FK/durability, WebView2/Tauri/.NET 실행은 미검증이다.
renderer 외부 요청 차단과 PATH 제거는 각각 OS 인터넷 차단/깨끗한 PC와 구분한다.
기존 Windows 사용자 DB·미디어를 시험에 연결하지 않는다. W04 저장 보장·W05 host 통합·
W12 권리/고지/서명·설치형 준비는 본 spike의 통과로 완료하지 않는다.
사용자 결과는 PR #59 또는 Work에 `w02-user-evidence.json`과 OS/하드웨어/Python 미설치/
인터넷 차단 방식·화면 종료 여부를 첨부한다. DB/state 파일은 비밀값이 있어 첨부하지 않는다.

## W01 실행 검증 및 재현

모든 아래 검사는 baseline `5762267e2366fa5bdbdd69bc6f38672d141dcbc8`에서 실행했다.
환경은 Ubuntu 24.04.3 / Linux 6.18.44 x86_64, Python 3.12.14, uv 0.12.23,
Node 24.19.0 / npm 11.9.0이다. 프로젝트 자체 패키지를 설치하지 않고 선언 의존성만 임시 venv에
설치하고 backend 작업 디렉터리에서 app을 import했다. editable 설치는 W00에서 실패한
app/alembic flat-layout 자동 탐색 문제를 그대로 인계하며 W01에서 재시도/수정하지 않았다.

주요 실제 설치 버전: RiichiEnv 0.4.8, FastAPI 0.143.0, Starlette 1.8.0,
SQLAlchemy 2.1.4, Alembic 1.20.0, Uvicorn 0.54.0, psycopg/binary 3.3.6,
Pydantic 2.14.1 / settings 2.15.0, httpx 0.28.1, PyJWT 2.15.1,
argon2-cffi 25.1.0, python-multipart 0.0.32, websockets 17.2.
pytest 9.1.1은 기존 함수 검사 실행용으로 임시 venv에만 추가했다.
frontend lockfile 기준 React/ReactDOM 19.3.0, TypeScript 7.0.2, Vite 8.3.0,
plugin-react 6.1.1, React/ReactDOM types 19.3.0이다.
Python 범위 의존성은 lock되지 않았으므로 동일 명령의 미래 해석 결과까지 고정된 것은 아니다.

```sh
# 저장소 루트에서 시작; 전용 임시 환경이며 사용자 DB/미디어 사용 없음
uv venv /tmp/nrnf-w01-verify
cd backend
uv pip install --python /tmp/nrnf-w01-verify/bin/python -r pyproject.toml --extra test
/tmp/nrnf-w01-verify/bin/python -m unittest discover -s tests -v
uv pip install --python /tmp/nrnf-w01-verify/bin/python pytest
/tmp/nrnf-w01-verify/bin/python -m pytest tests/test_dialogue_service.py -v
cd ../frontend
npm ci
npm run build
```

| 검사 | 이번 결과 | 보장 범위/제한 |
|---|---|---|
| backend unittest | **72개 통과**, 32.760초, exit 0 | 실제 엔진·SQLite 메모리 DB·TestClient/ASGI 및 stub/mock. pytest 함수는 수집하지 않음 |
| 대사 pytest | **10개 통과**, 0.09초, exit 0 | 기존 선택/추출/확률/cooldown 검사. 실제 브라우저 표시와 별개 |
| npm ci / build | **각 exit 0** | TypeScript 및 Vite production build; 실행 배포/Windows 증거는 아님 |
| routed browser 3개 | **각 exit 1 / 환경 차단** | Chromium launch 실패, DOM assertion 미실행 |
| live-game browser | **exit 1 / 환경 차단** | 임시 SQLite Alembic head/bootstrap, API health·Vite 준비까지 진행. Chromium launch에서 중단; 회원가입·대국·12행동 후 재시작·정산 비교 미실행 |

브라우저 재현에 사용한 명령(Playwright는 저장소 밖 runtime의 1.62.1):

```sh
# frontend에서 별도 터미널; live-game은 자체 서버를 사용
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
export PLAYWRIGHT_MODULE_PATH=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright
node tests/dialogue.browser.mjs
node tests/connection.browser.mjs
node tests/result-asset.browser.mjs
TEST_PYTHON=/tmp/nrnf-w01-verify/bin/python node tests/live-game.browser.mjs
# Chromium 확보 시 위 명령에 TEST_CHROMIUM_EXECUTABLE=/실제/실행파일 사용 가능
```

네 검사 모두 `chromium_headless_shell-1234/.../chrome-headless-shell` 실행 파일 부재다.
`node "$PLAYWRIGHT_MODULE_PATH/cli.js" install chromium`도 시도했지만 Chrome for Testing
151.0.7922.34 ZIP의 `End of central directory record signature not found` 이후 다운로드 실패
(exit 1)했다. 원격 응답 오류의 원인은 확정하지 않는다. 정상 Chromium을 제공한 환경에서
[기존 실행법](frontend/tests/README.md)대로 4개를 다시 실행해야 한다. live-game은 포트 8000/5193을
독점 사용하고 자신의 임시 DB·프로세스를 정리했다. 별도 Vite도 종료했다.

Windows EXE/번들, 인터넷 차단 실행, ComfyUI/StabilityMatrix, Docker/nginx/PostgreSQL,
실제 CG 디코딩, 전원 차단/SIGKILL, 복수 worker·동시 요청은 이번에 미검증이다.
W01 당시 Actions workflow가 없었으므로 위 W01 결과에 CI 통과를 주장하지 않는다.

## 보존 불변조건과 코드 → 검사 대응

경로는 backend의 경우 `backend/app/`, 검사는 `backend/tests/` 기준이다.
아래 통과는 unittest/대사 pytest에 한정한다. browser는 코드 대조만 했고 이번 미검증이다.

| 보존 영역 | 실제 코드 | 기존 대응 검사와 보장 한계 |
|---|---|---|
| 규칙·합법행동 | [adapter](backend/app/mahjong/riichienv_adapter.py), [session](backend/app/mahjong/session.py) | [test_riichienv_session](backend/tests/test_riichienv_session.py): pending 좌석 전체 행동 요구, 불법 행동/index 거절·상태 불변, 4좌석 동풍전 완료. RiichiEnv 0.4.8 / `4p-red-east` / Tenhou 기본값 유지; 역·부·동점·유국 전체를 독립 대조한 검사는 아님 |
| stage→Tier·CPU 성향 | [game_setup](backend/app/services/game_setup.py), [Tier0](backend/app/mahjong/tier0.py) / [Tier1](backend/app/mahjong/tier1.py) / [Tier2](backend/app/mahjong/tier2.py) | [setup](backend/tests/test_game_setup.py), [Tier0](backend/tests/test_tier0_agent.py) / [Tier1](backend/tests/test_tier1_agent.py) / [Tier2](backend/tests/test_tier2_agent.py), [personality](backend/tests/test_personality_integration.py), [tournament](backend/tests/test_tournament_simulation.py): stage 0/1/2, seed 결정성·합법 선택·대국 완료·성향 일부 평가. 모든 성향이 선택을 변화시킴 또는 Tier 강도 단조 증가를 증명하지 않음 |
| HP/stage·진행 경계 | [game_result](backend/app/services/game_result.py), game_setup, [결과 UI](frontend/src/game/MahjongTable.tsx) | [test_game_result](backend/tests/test_game_result.py): 사람 4위만 HP -1, CPU 4위만 매핑된 progress +1, 미완료/HP 0/완료 CPU 거절. setup: stage 2→3 완료 제외, 서로 다른 활성 CPU 3명·HP 필요. [dialogue.browser](frontend/tests/dialogue.browser.mjs): 결과 loop/game over UI fixtures(이번 미실행). CPU 부족 이후/HP 회복 정책은 D04 미확정 |
| 정산 exactly-once | [registry](backend/app/services/game_registry.py), [game API](backend/app/api/game.py), game_result | [test_game_websocket](backend/tests/test_game_websocket.py)의 `test_restart_after_final_action_before_settlement_settles_once`, `test_fixed_seed_match_completes_and_persists_server_settlement` 및 result 중복 검사: 최종 행동 commit 후 미정산 복구, 완료 재접속·HP/stage 중복 방지. 행동 commit과 완료·진행 정산 commit은 **별도 transaction**이며 결과/HP 또는 stage는 정산 transaction에 함께 저장됨 |
| 저장·복구·접속 | registry, game API, [record](backend/app/db/models/game_session_record.py), [프런트 연결](frontend/src/main.tsx) | websocket의 `test_persisted_action_restores_same_turn_with_fresh_registry`, `test_stale_action_is_rejected_and_latest_turn_is_resent`, `test_failed_action_commit_recovers_only_persisted_turn`: DB 행동까지 동등 복구, 과거 이벤트 비전송, stale/commit 실패 rollback 후 cache 제거. 단일 active/소유자 검사도 통과. [connection.browser](frontend/tests/connection.browser.mjs), [live-game](frontend/tests/live-game.browser.mjs)은 각각 routed 복귀/실제 process 재시작용(이번 미검증) |
| 대사 독립성 | [dialogue_service](backend/app/services/dialogue_service.py), game API/session | [test_dialogue_service](backend/tests/test_dialogue_service.py) 10 pytest: 활성/누락·CPU 이벤트·깡/론/쯔모·확률/cooldown. 별도 대사 RNG를 CPU RNG에 합치지 않음. chi 단독 매핑 assertion/모든 실제 이벤트 end-to-end는 별도 보강 조건 |
| CG 실패와 정산 분리 | [result_assets](backend/app/services/result_assets.py), game API, main.tsx/MahjongTable.tsx | [test_result_assets](backend/tests/test_result_assets.py): 권한/해금·교체/삭제·형식/크기, 임시 metadata byte fixture 사용(실제 이미지 생성 없음). websocket: 결과 metadata/대사. [result-asset.browser](frontend/tests/result-asset.browser.mjs): HTTP 503에도 순위/다음 선택 유지, 늦은 실패 차단(이번 미실행). 성공 응답 후 이미지 디코딩 실패·ComfyUI 실패 검사는 아님 |

### policy 1/2 및 legacy replay 보존

- 새 선택/snapshot은 `policy_version=2`; `CpuChoice` 기본값 1이 버전 없는 기존 DB snapshot을
  복원한다. 새 기본값으로 오래된 snapshot을 다시 저장하거나 현재 CPU DB 값으로 치환하지 않는다.
- Tier2 policy 1은 기존 `round_wind == 0` 분기를 그대로 재현하고, policy 2는 동4 및 남장 연장
  (`round_wind > 0 or kyoku_index >= 3`)을 종반으로 판단한다.
  `test_endgame_round_boundary_and_legacy_policy` / `test_real_engine_east_and_sudden_death_rounds` 통과.
- 저장된 match seed, CPU 선택 순서/좌석 1·2·3, stage와 여섯 성향 snapshot, policy,
  CPU seed `match_seed * 10 + seat`, 사람 합법행동 index/순서를 유지한다.
  RiichiEnv 버전·합법행동 순서·agent RNG 소비 변경은 replay 호환 변경으로 취급한다.
- [legacy fixture](backend/tests/fixtures/tier2_legacy_replay.json)는 원본 `e357c01`, seed 5,
  stage 2 CPU 3명, policy 필드 누락, 108행동이다. 파일 SHA256:
  `b51447422f5522d4c16e0bab0aa27cfabe90c5923018cf583411d39e478ce64e`.
  `test_legacy_tier2_snapshot_replays_every_original_turn`이 매 턴 hash와 12행동 후 registry 교체,
  최종 재생을 확인했다. 점수 `[17000,27700,24700,30600]`, 순위 `[4,2,3,1]` 일치.
  [원본 계약](backend/tests/fixtures/README.md)대로 현재 policy로 fixture를 재생성하지 않는다.
- policy 2는 `test_new_tier2_policy_survives_registry_restart`에서 1행동 복구를 검사했다.
  전체 대국·12행동 후 실제 API 재시작·완료 재접속은 live-game 검사 영역이며 이번 미검증이다.
- UI/이미지·대사 RNG와 생성 요청은 엔진 행동 log/CPU RNG/정산에 끼워 넣지 않는다.
  완료 record의 결과/정산과 replay에서 소비한 과거 이벤트 비전송도 보존한다.

## 새로 확인한 검증 누락과 후속 조건

제품 결함을 새로 확정하거나 수정하지 않았다. 다음은 현재 검사의 한계이며 해당 후속 Task에서 다룬다.

- **검사 수집:** 기존 unittest 72개는 pytest 대사 함수 10개를 포함하지 않는다.
  `pyproject.toml` test extra에도 pytest가 없다. 후속 검증 환경은 두 명령과 pytest 설치를 명시해야 한다.
  의존성/CI 변경은 이번 범위 밖이며 별도 허용 범위에서 처리한다.
- **복구/정산:** 행동 commit 실패 회귀는 있으나 정산 commit 자체의 실패 주입/재시도,
  실제 동시 socket/writer·중복 프로세스, SQLite FK 적용·잠금/전원 차단 durability는 보장되지 않는다.
  W04는 저장 계약 결정 후 이를 검증해야 한다. 메모리 DB `create_all` 통과와 migration/Windows 저장을 혼동하지 않는다.
- **CPU/규칙:** 일부 성향 검사는 파라미터 저장/선택 non-null만 확인한다. 소규모 tournament는
  Tier 강도 순서 보장이 아니다. 엔진 교체·CPU 튜닝 시 독립 규칙/행동·통계 증거가 추가로 필요하다.
- **CG:** HTTP 503/늦은 실패 fixture와 실제 이미지 디코딩 실패는 다르다. 현재 `<img>`에는
  onError 대응이 없으므로 성공 HTTP 뒤 디코딩 실패 표시는 별도 확인/수정 Task가 필요하다.
  W10/W11의 생성 실패 독립성은 아직 구현·검증하지 않았다.
- **실기:** Chromium 확보 후 기존 browser 4개 재실행; Windows 런타임/번들 증거는 W02에서
  별도 확보한다. W01 환경 차단을 제품 오류나 Windows 성공으로 해석하지 않는다.

## 기존 검증 증거 (재실행 아님)

- `docs/DECISIONS.md`, `docs/WORK_HANDOFF.md`: 2026-10-14 실제 React/FastAPI/Vite/SQLite
  대국 108행동 및 12행동 후 API SIGTERM 재시작, 전체 턴 동일 복구, 완료 재접속/정산 보존 기록.
- `docs/WORK_HANDOFF.md`의 2026-09-12 Docker 최종 통합: nginx·PostgreSQL·media volume
  및 migration/재시작 보존 기록. 최근 제품 전체의 Windows/전원 차단 보장을 의미하지 않는다.
- `frontend/tests/README.md`: 3개 routed browser 회귀와 `live-game.browser.mjs` 재현 절차.
  `backend/tests/fixtures/README.md`: legacy replay 원본·계산 기준.

## 초기 분석 당시 차단/불일치 — 역사적 기록

아래 1~3은 Windows 전환 전 baseline이며 현재 구현 판정은 이 문서 앞의 W04~W06-B 결과를 따른다.

1. **진행:** 선택 가능 CPU 3명이 필요하고 stage 3은 제외된다. 6명 중 4명을 완료하면
   2명만 남아 이후 시작 불가능. 모든 CPU 완료라는 기존 목표와 실제 진행 경로가 충돌한다.
   새 목표는 REQUIREMENTS D04로 갱신됐으나 현재 코드에는 아직 미반영이다.
2. **실행:** 제품 Windows shell·기동/종료 관리는 없다. W02 격리 후보와 Windows 실행 증거는
   위 별도 기록이며 W03 채택·W05 통합·W12 정식 배포를 완료한 것이 아니다.
3. **저장:** SQLite 시험 성공과 제품 전환은 다르다. PostgreSQL 행 잠금/환경·웹 인증·
   `/data/media` 경로와 bootstrap을 Windows 실행 조건에 맞춰 검증해야 한다.
4. **콘텐츠:** 공유 Level별 프롬프트·후보·상황/대사 관계·변수·ComfyUI 연결·생성 캐시 미구현.
5. **문서:** 기존 docs에는 초기 목표 트리, Tier 1/2 미구현 등 시점별 서술과 Docker 완료/보류
   서술이 함께 있다. 루트 기준 문서가 현재 인계점이다. 과거 증거 본문은 보존한다.
   CPU 난이도 순서가 확실히 검증됐다는 결론도 금지: 최신 정책의 고정 표본은 작다.

## 다음

W06-B PR #68과 W06-C PR #70은 main에 병합됐다. W07 정책 독립 기술 계약을 구체화했으며,
다음은 REQUIREMENTS의 미응답 정책 조율과 조건부 계약 최종화다.
후속 사용자 지시로 W08-A 등록 기반만 독립 구현했다. 나머지 W08~W11은 각 정책 게이트를 유지한다.
개인 Windows 실기, 전원 차단 durability 및
실제 ending CG/음악 재생은 해당 범위에서 증거를 별도로 확보한다.
