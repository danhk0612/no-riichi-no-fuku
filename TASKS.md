# 개발 Task

모든 미착수 Task는 계획이며 실행 승인이 아니다. 상태는 구현/검증 사실로만 변경한다.
W00은 초기 분석·기준 문서 준비(완료); 본 파일은 후속 개발 명세다.
Task 목적·금지 범위·완료 기준 변경이 필요하면 사용자 결정 후 갱신한다.

## 순서와 우선순위

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
| W08-S | 폴더 음향팩·단일 선택·fallback·캐릭터 음성 연결 | P1 / 완료(PR #83 병합, 최종 검증은 PR 참조) | W07 팩/event 계약, W08-A/B/C 병합, Q-PACK/Q-AUDIO/D-WIN/Q-OMAKE-VOICE | 저성능 Work |
| W-DIFF-A | 난이도 1~10 설계·격리 기술 검증·구현 인계 | P1 / 판단 축 진단 완료·10강도/성향 동시충족 미입증 | PR #83/#84 병합, 2026-10-18 사용자 승인 | 고성능 Work |
| W-DIFF-B | 단계+게임 설정의 최종 난이도·저장·설정 UI 적용 | P1 / DIFF-* 정책·profile 보정 승인 대기, 미착수 | W-DIFF-A 검토 | 저성능 Work(판단 구현 복잡 시 고성능 Work) |
| W09 | 공유 상황·대사·변수 연결 | P1 / 대기 | W08 | 저성능 Work |
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

## 후속 Work 지시문 — W-DIFF-B (게이트 해제 후에만)

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
| W08-S | W08-A/B/C 병합, Q-PACK/Q-AUDIO/D-WIN/Q-OMAKE-VOICE 확정, D-WIN의 화료음성 연결과 최종 1위 미추가 | W08-A registry·immutable media 참조 재사용. audio/voice selection API·최소 UI·재생 resolver와 승인 hook을 구현. 기본 선언 다음 `win`, final 4th는 변경 후 `defeat_stage_N`(오마케/stage3도 stage3), 기존 보충 CPU `match_first` 대사는 기존 계약만 유지하고 최종4위 `match_last` 대신 단계별 대사를 사용. 새 동풍전 최종 1위 대사는 추가하지 않음. 새 `win` voice slot 등록 검증을 허용하며 legacy W06 플레이어·자료는 보존. shared dialogue text/context list는 W09. CPU 판단/규칙/seed/replay 계약 변경 금지 | W06 selection/file/pending/reset/restart 호환·Q-AUDIO 원자 전환, per-domain single pack/default/mute, voice missing/off, simultaneous writes, event identity/order, stale callback, duplicate/reconnect suppression, omake. Backend/build/browser and exact-SHA Windows CI/artifact source/hash |
| W09 | W08/W08-S 병합, D05-b/c·D06-b/d·D08-b·D10-a·Q-LEGACY | `dialogue_service.py`와 새 content resolver, `api/game.py`/`game_registry.py` 표시/정산 저장 경계·필요 additive migration·types/main/MahjongTable. 원 pending ordinal 유지·공통 선언과 actor 음성, event/상황/캐릭터/Level 교집합·`win` text/context relation 및 변수 snapshot. W06 version2/오마케의 확정 voice 유지/추가 진행·CG 억제·노출 policy 유지. ComfyUI submit 금지 | source index/ron-tsumo/win ordering·reach_accepted/actor·최종4위·보충/omake·대사 고갈·변수·중복/재접속·commit 실패·policy1/2/legacy replay |
| W10 | W07 D07-a/b·D08-a·D09-a, Q-FRAME, W08 입력 schema | 새 ComfyUI adapter/client/workflow/settings service/schema/API, `local_runtime.py` 수명·최소 설정 UI/api. 승인 endpoint 정책과 job 입력/snapshot/unknown 상태 구현. 실제 지원 workflow의 object_info/input/output·Anima/encoder/VAE/LoRA·한도/파일 decode를 기술 확인. 실환경 없으면 mock 범위만 제출하고 실출력 완료 금지. 게임 RNG/정산·모델 다운로드·전역 interrupt 금지 | mock submit/status/result·응답유실·재기동/자기 job·endpoint 미연결 기본 게임·종료 소유권. 실제 생성은 별도 사용자 승인/환경/D11 제공 때만 실측 |
| W11 | W06·W09/W10 병합, D05-b·D06·D08 전체, Q-IMAGE/Q-FRAME | 새 selection/job/artifact 연동 services/API·필요 additive migration, W09 표시 hook·W10 adapter 호출, types/api/main 최소 표시/명시 retry. seed/cache/4단계3종 분리·재렌더 무추첨·writer 밖 submit·late result 격리·원본/이전 파일 보존 구현 | 입력/label/모델 revision별 cache·동시 동일 요청·submit unknown·DB 실패·A→B/새 대국/reset 후 완료·missing 파일·명시 retry·재시작 snapshot. 실제 ComfyUI와 mock 구분 |
| W11-U | W08 표시 DTO·W09 result/voice·W11 이미지 API, Q-META/Q-IMAGE | `CpuSelection.tsx`·`MahjongTable.tsx`·main/types/api/style와 새 최소 상세/결과/뷰어 컴포넌트. 정사각 프로필 목록·상단 CG/전신·좌석 상세·stage_after 연출·CG 전용·줌/팬 구현. DTO 확정 후 mock UI 개발 가능하나 수용은 실제 W11 연결 후. 갤러리/새 스탯/자동 생성 hook 추가 금지 | hover/선택/좌석 identity·로딩/깨진 이미지·stale blob·CG 전용 복귀/줌팬·최종 결과→기존 엔딩 ack·재조회에 재정산/추첨/submit 없음. 보충/오마케 표시 |

위 새 파일명은 책임 분리용 구현 경로이며 기존 서비스에 동일 책임이 있으면 최소 재사용한다.
W08→W08-S→W09는 공통 schema/API/UI 충돌 때문에 순차다. W10 독립 작업은 정책 확정과
models/main/local_runtime/API/문서 소유 분리 후만 가능하며 이번에 병렬 agent를 실행하지 않는다.
W11은 W09/W10 이후, W11-U 수용은 W11 이후다. W12는 이 여섯 Task와 D11 실제 콘텐츠/권리·
Windows 실기 게이트를 기다린다. W08-A/B/C는 각각 사용자 지시로 독립 승인됐다. 나머지는 문서 PR만으로 자동 착수하지 않는다.

모든 구현 Task는 관련 unittest와 별도 dialogue pytest·frontend build/browser·writer/정산 실패·
W05 종료/재시작·W06 pending/reset/사운드 회귀를 변경 영향대로 실행한다.
정확한 head SHA의 Windows hosted CI/artifact source/ZIP hash를 대조한다. 개인 PC·OS 인터넷 차단·
전원 차단/실제 CG·오디오·ComfyUI는 실제 수행한 범위만 기록한다. 사용자 폴더 대신 소유 임시 자료로 검사한다.

### W08-A — 팩 등록 기반 시스템 (독립 승인 범위)

- 최종 검토 보완: 제품 source `ad12e6f`에서 Windows 예약 장치명을 팩/캐릭터/voice namespace ID에서도
  거절한다. 수정 전 실패 재현과 registry 15개 통과를 확인했다. 원본 `0742a9d`의 Windows 성공과
  수정본 검증은 구분하며 최종 head/CI/artifact/병합 상태는 PR #79를 따른다.

- 결과: 제품 source `ca2c2ef`의 Linux/Windows unittest 114개·대사 10개, build/종료 및
  W05 packaged renderer 22개·일반 종료/restart 검증을 통과했다. artifact/source/ZIP hash는
  CURRENT_STATE에 기록했다. [PR #79](https://github.com/danhk0612/no-riichi-no-fuku/pull/79) 제출, 직접 병합 없음.
  A→B→A 인식 포인터 회귀는 수정 전 실패를 재현한 뒤 보완했다. 실제 리소스 출력은 미검증이다.

- 기준: main `01da784`, PR #75~#78 병합 확인. W07 전체 완료나 W08 전체 착수가 아니다.
- 범위: character/sfx/bgm/voice 영문 identity·manifest v1 검증, 지정 폴더 startup scan/명시 rescan,
  DB 목록·진단, pack/revision/content digest, immutable media 복사·과거 revision 보존, additive migration과 local API.
- 구현 계약은 ARCHITECTURE의 W08-A 절을 따른다. 외모/상의 속옷/하의 속옷 P/N,
  4 Level × 3종 이미지·구도 P/N을 원본 manifest snapshot으로 검증·보존한다. 실제 문구/자료 seed 없음.
- 제외: 캐릭터/공유 후보 편집·삭제/재연결 UI, CPU 생성/기존 CPU 연결·팩 실제 적용,
  음향 선택/재생 전환·event·생성·화면 개편. 기존 W06 설정/자료/pending/진행/엔딩은 그대로 유지.
- Q-PACK은 A로 결정됐다. W08-A는 등록/보관만 구현한 이력이며 적용/병합은 후속 작업이다. Q-META는 편집/표시,
  Q-LEGACY는 기존 대사 이전, D06-c/D05-c/D10-a는 후보 이동/event/변수, Q-AUDIO는 W08-S 전환,
  Q-OMAKE-VOICE/D-WIN은 신규 음성 hook, Q-IMAGE/Q-FRAME/D07~D09는 생성/표시 수명을 막는다.
- 검증: ID·namespace/폴더 일치·중복/버전/불완전 복사·경로 이탈, 참조 bytes 변경 revision,
  반복 migration/scan·실패 rollback·restart/reset·과거 파일/hash 보존·capability·기존 회귀.
  Windows hosted CI/artifact는 정확한 source SHA로 확인하고 임시 signature fixture 검증과 실제 리소스 출력을 구분한다.
- 제출: `task/w08-a-pack-registry` commit/push/PR. 직접 병합·Release/tag·사용자 자료 변경/삭제 금지.

### W08-B — 기존 캐릭터 프롬프트 편집·팩 목록 UI

- 최종 검토: 저장 대기 중 P/N 입력 소실·팩 탭 재진입 중복 검색을 각각 재현하고 입력 잠금/
  in-flight guard로 보완했다. 전용 content browser 회귀를 W05에 연결했다. 원본과 수정본의
  exact-head CI/artifact 및 병합 상태는 PR #81/CURRENT_STATE를 따른다.

- W08-A 병합 후 독립 구현한다. ARCHITECTURE의 W08-B 계약을 따른다. 기존 CPU PK·명단·진행은 유지한다.
- 외모/상의 속옷/하의 속옷 P/N과 4 Level×3종 구도 P/N 편집·저장, 필드별 명시 override,
  팩 목록/진단/재검색 UI만 구현한다. 새 CPU/팩 실제 적용·이미지 업로드·공유 후보는 제외한다.
- Q-PACK A를 위해 빈 문자열 포함 편집 기록을 남긴다. 현재 값 비교로 기록을 지우거나 전체 폼
  저장으로 미편집 필드를 override로 만들지 않는다. 실제 팩 병합/적용은 후속 작업이다.
- 최소 파일: models/exports·0007 다음 additive migration, services/character_content.py,
  schemas/local_content.py·api/local_content.py·local_runtime 등록, frontend api/types/main 및 최소 편집 패널/스타일.
- 검증: GET 무쓰기·빈 값/문자열별 격리·revision 충돌·commit 실패·권한·A→B 늦은 응답·저장/재시작/reset 보존,
  scan 후 로컬 편집 불변, W06 설정/명단/pending/파일·legacy replay 보존. 변경 영향에 맞춘 Windows exact-SHA CI/artifact.
- 환경: 저성능 Work. 시스템 우선이며 구체 프롬프트 작성·콘텐츠 seed·생성/재생 기능은 추가하지 않는다.

### W08-C — 기존 CPU와 캐릭터팩의 명시 연결·동일 팩 갱신

- 결과: 제품 source `c41cd44`의 Linux/Windows unittest 123·대사 10, build/browser·종료 회귀,
  Windows packaged renderer 22 checks·일반 종료/restart와 다운로드 artifact source/ZIP hash를 확인했다.
  실제 서버/Vite의 108행동·재시작 browser도 통과했다. 자세한 검증은 CURRENT_STATE 및
  [PR #82](https://github.com/danhk0612/no-riichi-no-fuku/pull/82)에 있다. 개인 PC/실제 리소스 출력은 미검증.
- 준비 main `e2e38d1`, PR #79~#81 병합을 확인했다. W08-B 다음 독립 범위이며 W08 전체 완료가 아니다.
- `task/w08-c-character-pack-application`에서 기존 content 서비스/API·편집 화면을 확장한다.
- 최초 연결은 사용자 CPU/등록 캐릭터팩 선택 후 명시 적용. 기존 PK/slug/이름/성향/명단/진행은 불변.
- CPU별 적용 revision FK와 기본/구도 문자열별 overrides를 재사용한다. 재검색은 등록 포인터만 갱신,
  사용자가 같은 팩의 새 등록 revision을 적용하면 미편집 P/N만 반영한다. 빈 값/동일 값 편집도 보호한다.
- immutable 이미지 참조는 적용 revision의 Level/kind별 media UUID로 조회한다. 과거 revision 조회는
  고정 원본/파일만 반환하며 기존 게임 presentation snapshot은 수정하지 않는다.
- content expected_revision 및 대상 registered revision을 writer 안에서 검사, commit 후 응답한다.
  불완전 소스/충돌/잘못된 종류·교체/commit 실패는 기존 적용값·기록·파일을 보존한다.
- 검증: 최초 연결·미연결 무자동연결·전 필드 P/N 병합·편집/갱신 경쟁·revision 충돌·commit rollback,
  과거 media/source hash·재시작/reset 보존·늦은 UI 응답, backend/build/browser·Windows exact-head artifact.
- 제외: 다른 팩 교체/해제·새 CPU·metadata/shared/event·생성·선택/결과 UI·음향 적용(W08-S).

### W08 — 캐릭터·공유 목록·후보 관리

- 목적: 외모/복장 P/N, Level별 공유 항목 및 네 종류 후보 선택·제외 편집.
- 범위: W07 확정 schema/API·migration·관리 UI, stable ID/label·CRUD·후보 참조·재시작 저장.
- 선행: W05, W07. shared dialogue 데이터 관리 포함, event 선택은 W09.
- 완료: R07~R09/R14 편집·저장, 캐릭터 간 격리·단계별 차이·삭제/빈 후보/추가 정책 검사.
- 금지: 공유 원문 캐릭터별 복제, 미승인 seed/갤러리/배치 기능, 생성 API·규칙 변경.
- 환경: 저성능 Work.

### W09 — 공유 상황·대사·변수 연결

- 목적: 실제 event에 맞는 허용 상황/대사를 기존 말풍선·결과로 전달.
- 범위: W07 event/상황/Level 정책, 상황 대사와 캐릭터 후보 교집합·변수 치환,
  기존 CPU별 event 대사의 승인된 호환, 기존 노출 확률/cooldown 경계 보존.
- 선행: W08 및 W07 D05/D10 결정.
- 완료: 상황별 다문장·캐릭터/Level 제외·변수·빈 후보·재접속/event 불일치 회귀 통과.
- 금지: 임의 조사/추가 변수·생성형 대사, CPU 판단·기존 노출 정책의 무관 변경.
- 환경: 저성능 Work.

### W10 — 독립 ComfyUI·Anima adapter

- 목적: 게임 정산과 독립인 로컬 생성 연결.
- 범위: W07 생성 계약, endpoint/object_info/workflow/model/LoRA/P/N, submit/status/result,
  실패/소유 job/종료 경계; Wayward 참고 파일 복사 시 개별 유래·고지·의존성 확인.
- 선행: W03 endpoint 수명/관리 UI 경계, W07 D07/D09 결정.
- 완료: mock 계약 검사 및 실제 StabilityMatrix ComfyUI/Anima 최소 생성 증거(별도),
  오프라인·미연결 게임 독립성. 사용자 모델/LoRA 배포 없이 설정 참조로 작동.
- 금지: Wayward/WML 의존, 게임 RNG/정산 결합, 승인 없는 ComfyUI 자동 기동/전역 interrupt,
  클라우드 AI·모델 번들·사용자 이미지 삭제.
- 환경: 저성능 Work. 미확정 node/model 기술 문제만 고성능 Chat 검토.

### W11 — 이벤트 랜덤 조합·생성/파일 연동

- 목적: 현재 캐릭터/Level 후보로 표시 이벤트의 이미지와 대사 연결.
- 범위: 허용 복장 상태/상황/포즈 선택→P/N 결합→파일 재사용/생성→표시,
  승인된 request/cache identity, 늦은 결과·재렌더·재시작·실패/대기 정책.
- 선행: W06, W09, W10, W07 D08 결정.
- 완료: 이벤트당 선택 안정성·허용 후보·설정 수정 후 재사용 기준·다른 캐릭터/시점의 지연 결과
  차단·파일 보존·ComfyUI 중단 후 대국 계속을 통합 검사. 실제 Windows/ComfyUI와 mock 구분.
- 금지: 렌더마다 재선택, CPU RNG 변경, 임의 cache 삭제/추가 백업·갤러리/배치 기능.
- 환경: 저성능 Work. 계약으로 해결되지 않는 복합 상태 문제는 고성능 Work로 분리.

### W12 — Windows 통합·배포 준비

- 목적: 오프라인 사용/데이터 보존/선택적 생성의 배포 후보 검증.
- 범위: 확정 설치/포터블 방식, 깨끗한 Windows 압축 해제·첫 실행·업데이트 데이터 보존,
  기본 대국/복구·ComfyUI 없음/정상/실패, 라이선스/고지·사용자 README·재현 build/CI.
- 선행: W11, D11 콘텐츠/권리와 사용자 테스트 환경.
- 완료: 정확한 SHA와 artifact·Windows 실측/미검증·의존 런타임/용량·업그레이드 보존 기록,
  공개 배포 가능한 범위 및 잔여 제한을 검토 가능하게 준비.
- 금지: 미승인 Release/tag/직접 병합, 모델/CG 권리 추측, 새로운 기능/대규모 정리.
- 환경: 저성능 Work. 공개 배포는 별도 명시 승인 후 별도 실행.

## W04 PR #61 보완 결과

이름 PATCH→GET→파일 DB→runtime 재시작 보존, REST/WS malformed capability 거절,
local 전용 write intent·동시 읽기·기본 engine의 원본 transaction 보존, 파일 DB 정산 commit
실패/rollback/cache eviction·재시작 후 exactly-once를 보완했다. 최종 code `455d400`의 실행
결과는 CURRENT_STATE를 따른다. 기존 보완 지시/성공 이력은 PR #61/#62와 Git에 보존한다.

## W06-B PR #68 보완 결과

기존 `task/w06-b-progression`과 PR #68을 유지했다. 최신 main `1646bd9580d7aaa34d1d793b7272d74163fc57f2`
및 기준 문서 충돌 정리 `ece3a08b639d1da4b67db8ca543ede728ebbb59d`를 확인하고 W06-A 계약 범위에서
legacy 취소 후 늦은 정산, 웹 HP 0 member의 대국 생성, `ending_pending` 화면, reset/ack 복구,
generation/request-token stale 응답을 보완했다. 수정 전 실패와 수정 후 통과를 포함한 재현·검증 내역은
[CURRENT_STATE.md](CURRENT_STATE.md)의 “W06-B PR #68”에 기록한다.

최종 검토 source `300892a93d923e0565c9c668ffb8a1a7b635cfd6`에서 reset 실패 후 renderer를
reload하지 않고 다음 행동·전체 대국까지 완료하도록 smoke를 보강했다. W05 push run
[38808520631](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38808520631), PR run `38808528623`,
W04 run `38808528770` 모두 성공했다. 다운로드 artifact `12007637653`의 source SHA, 외부 archive와
내부 Windows ZIP hash 및 renderer/lifecycle JSON을 대조했다. unittest 94개·dialogue pytest 10개,
frontend build·Node 종료 회귀도 통과했다. 상세 SHA/hash·검사 범위·이전 증거는 CURRENT_STATE를 따른다.
최종 검토는 통과했으며 병합 상태/SHA는 PR #68과 Git을 확인한다. 개인 Windows PC·전원 차단 및
실제 ending CG/음악은 미검증이다. 이 B 검토 당시에는 W06-C 미착수였다. C 최종 검토와 병합 상태는 아래 결과 및 PR #70을 따른다.

## W06-C PR #70 — 최종 검토 통과

기존 `task/w06-c-sound-ending`과 PR #70을 유지했다. 수정 전 실패 5건은 CURRENT_STATE 표에
보존했다. BGM 반복·순서변경 시 곡 유지·media 교체·늦은 callback/재시도, 완료 결과 화면을 가로지르는
최종 committed SFX와 replay/reset 차단, 비활성 선택 해제, 새 ending의 active 음악 제한을 보완했다.
W06-A/B 계약, CPU/대사/정산 RNG 및 사용자 자료는 변경하지 않았다.

제품 source `e9918fec249e909faa135227399e96136d2b984e`의 Windows Server 2022 W04 PR run
38823272350와 W05 push run 38823267255가 통과했다. W05 exact-source artifact `12012999384`는
source SHA와 외부 archive SHA256 `839804e93f47eadc5ffbbb8c488fc3b3667a312819b2da3b48bdc2732a2961f3`,
내부 Windows ZIP SHA256 `deca88e1ab2ee99b44e7f3773ccedebbafc12aa30e315ace9740af0dbde716e4`를 대조했다.
Linux unittest 100, focused sound 6, dialogue pytest 10, frontend build, 종료 회귀 3도 통과했다.
최종 문서 SHA와 CI/artifact 증거, 실제 미검증 범위는 CURRENT_STATE에 기록한다.
실제 CG/음악 출력과 개인 PC/전원 차단(D11)은 미검증이다. 보완 제출 당시에는 PR을 직접 병합하지 않았고
Release/tag/W07을 수행하지 않았다.

최종 검토 source `efd5a0316ff4f3f6f51c05d24566c0b1b5829157`에서 BGM/SFX의 늦은 play 응답
격리 회귀와 명단 초기화 뒤 실제 선택 가능 상태를 기다리는 smoke 조건을 보강했다.
W04 `38826559169`, W05 PR `38826559160`/push `38826553799` 모두 통과했다. artifact/source/ZIP
검증 및 중간 실패 이력은 CURRENT_STATE를 따른다. 최종 검토를 통과했으며 병합 상태는 PR #70/Git으로 확인한다.

## W08-C 인계·검토 범위

현재 독립 범위는 위 W08-C와 ARCHITECTURE의 W08-C 계약이다. 구현 source와 정확한 head의
W04/W05 Windows 결과·다운로드 artifact source/ZIP hash는 이 브랜치의 제출 PR에서 확인한다.
새 Work는 최신 main·현재 branch·열린 PR·AGENTS 및 루트 기준 문서를 다시 확인한다.
W08-C 검토 후에도 W08-S나 나머지 W08/생성/화면 Task는 별도 지시 없이 시작하지 않는다.
다른 팩 교체/해제·새 CPU/metadata·음향 적용·공유 후보·event·생성·사용자 자료 변경은 제외한다.
직접 병합·Release/tag는 이번 승인 범위가 아니다.

## W07 정책 조율·계약 확정 지시문 — 이전 작업 이력

권장 환경: 질문 답변 조율은 **고성능 Chat**, 복합 schema/API 계약 정리는 **고성능 Work**.
W07 설계 준비와 2026-10-16 중간 요구 배분을 반영했다. 확정 내용은 다시 묻지 않으며, 남은 사용자 응답과 기술 계약을 정리한다. 아래 지시문은 답변 후 문서 계약을
확정하는 범위이며 제품 구현 승인이 아니다. 응답이 없으면 질문을 유지하고 구현으로 넘어가지 않는다.

```text
danhk0612/no-riichi-no-fuku의 W07 정책 조율·계약 확정만 수행해.
최신 main·현재 브랜치·열린 PR·AGENTS.md와 루트 기준 문서를 확인하고,
W07 설계 준비 문서 PR의 최신 상태/변경을 먼저 읽어. 미병합이면 최신 head를 기준으로
현재 사용자 승인 범위와 충돌 여부를 확인한 뒤 기존 문서 브랜치에서 이어가. 다른 작업을 덮어쓰지 마.
REQUIREMENTS의 R20~R29·중간 검토를 먼저 읽고 D05-a 확정을 유지해.
D04-count/D10-text-voice는 재확인으로 확정됐다. 다시 묻지 말고 나머지 미응답 질문만 구분해.
미완료 `<3`는 유지하며, 기본 선언의 간단한 공통 텍스트와 actor 캐릭터 음성팩을 분리해. 확정 요구를 최초 권고로 되돌리지 마.
TASKS의 중간 요구 배분에 따라 W08-S/W11-U를 포함해 계약을 갱신해. 조건부 W06-D는 불필요로 종료했으므로 제품 변경을 만들지 마.
확정 정책은 다시 묻지 말고, 응답하지 않은 항목·상충하는 조합은 선택지로 남겨.
권고를 승인으로 간주하거나 D11 실제 콘텐츠/권리를 추측하지 마.

답변받은 범위에서 ARCHITECTURE의 관계/API/UI 초안을 구체 필드·제약·version·
migration/기존 seed·legacy 호환·method/DTO/오류·event source ordinal·표시 snapshot/
생성 입력·seed/cache 식별·재접속/job 수명·파일 보존·검증 예제로 확정해.
정책 결정과 ComfyUI node/workflow 지원의 실제 기술 확인을 구분해.
영문 ID 루트/팩 manifest·인식·종류별 slot과 fallback·기본값·기존 자료 이전, 단계별 3종 prompt/asset,
선택/좌석/결과·CG 전용/줌팬의 API 책임을 먼저 명세해. 원본 이미지팩과 선택 voice pack은 독립이야.
W08/W08-S/W09/W10/W11/W11-U가 임의 정책 선택 없이 구현할 수 있는지 확인하고 지시문을 작성해.
미해결 의존 Task는 차단 상태로 유지하고 W07 전체 완료라고 표시하지 마.
REQUIREMENTS/ARCHITECTURE/TASKS/CURRENT_STATE만 책임에 맞게 갱신해.
문서 commit/push·PR 제출/갱신까지 진행해.
제품 코드/migration/UI 구현·CPU/규칙 변경·콘텐츠/CG/오디오 생성·사용자 자료 수정/삭제·
ComfyUI 실행·직접 병합·Release/tag는 하지 마.
```

## 최초 구현 지시문 — W06-C (과거 지시, 이력)

A 및 B 검토/병합 후 사용한다. 권장 환경: **저성능 Work**. B와 병렬 작업하지 않는다.

```text
danhk0612/no-riichi-no-fuku의 W06-C만 수행해.
최신 main·현재 브랜치·열린 PR과 AGENTS.md 및 루트 기준 문서를 먼저 읽고,
TASKS W06-C와 ARCHITECTURE의 “W06-A 구현 계약 — W06-B/C 인계” 전체를 따라.
A/B 검토·병합과 B의 실제 schema/API/검증 결과를 먼저 확인해.
task/w06-c-sound-ending에서 최소 사운드 등록·선택과 엔딩 리소스 표시/재생을 구현해.

local_media_assets/sound_effect_sets/background_tracks와 공통 설정을 B 다음 migration으로 추가해.
등록/수정/비활성화·media 업로드/file·sound-selection·ending-resources API와
게임 내부 최소 관리/설정·엔딩 화면만 구현해. 캐릭터 P/N/공유 후보 관리 UI는 W08로 남겨.
초기값은 효과음 null/BGM 빈 목록/엔딩 미등록. 실제/더미 CG·음악·대사를 생성·seed하지 마.
asset UUID/상대 key·한글 경로·형식/크기·root 이탈 보호·인증·immutable 파일 계약을 지켜.
파일 교체/참조 해제 시 기존 파일을 삭제하지 마. hard DELETE/자동 청소/변환 기능은 추가하지 마.
명단과 사운드 선택은 독립이고 진행 중 설정 변경·재시작 보존을 지원해.
B 엔딩 event/ack/generation 계약을 재설계하지 말고 리소스 resolve만 연결해.
pending payload는 완료 시 한 번 고정하며 이후 설정 변경으로 바꾸지 마.

선택 BGM은 목록 순서 순환, 기본 마작 6개 SFX는 대사 존재와 독립시켜.
commit 뒤 event identity로 중복/복구 과거 재생을 막고 오마케에서도 기본 SFX는 유지해.
당시 설계는 오마케 캐릭터 대사/CG/승패 이벤트를 억제했으며 캐릭터 voice/새 SFX hook은 범위 밖이었다.
2026-10-16 결정으로 기본 선언·화료·최종4위 대사는 재생하고, stage/Tier/추가 진행/CG 억제는 유지한다.
엔딩은 일반 BGM 중지→등록 CG/음악 1회/평문 대사→명시 계속하기 ack→오마케 순서야.
미등록/누락/비활성/재생 실패/autoplay 거절은 안내·무음으로 처리하고 대국/계속하기를 막지 마.
음악 ended나 GET/파일 실패로 자동 ack하지 마. pending 재기동은 같은 엔딩,
ack 응답 유실 뒤는 omake로 복구해. 초기화/화면 이탈/늦은 load/ended callback도 세대로 격리해.

TASKS의 C 파일 범위·검증표를 따라 backend/frontend/browser 및 기존 B/legacy/writer/정산 회귀를
실행해. 실제 사용자 폴더 대신 소유 임시 자료로 파일/설정/초기화 보존을 검사해.
정확한 수정 SHA의 Windows CI·artifact source SHA/ZIP hash·packaged 흐름을 확인해.
mock 재생/미등록 경로와 실제 제공 리소스의 CG 표시·오디오 출력 검증을 구분해.
실제 자료가 없으면 완료로 과장하지 말고 PR에 D11 실측 대기와 정확한 재개 조건을 남겨.
사운드 설정·pending/ack 후·reset 후 재실행과 한글/공백 경로를 검사해.

CURRENT_STATE/TASKS/ARCHITECTURE와 사용자 README를 실제 구현 범위에서 갱신해.
브랜치 commit/push·PR 제출·검증 CI는 허용한다.
직접 병합·Release/tag·W07 착수·공유 콘텐츠 정책 확정·ComfyUI·외부 사운드 생성 서비스·
파일/콘텐츠 생성·사용자 자료 수정/삭제는 하지 마.
```
