# W09-C2 — 신규 대국의 결과 콘텐츠 저장 설계

이 문서는 W09-M/S를 국 결과와 연결하기 위한 설계다. 실제 이미지 생성은 W10/W11 범위다.
운영 기준은 REQUIREMENTS의 최신 결정이며, W09-C 표시 계약 §2~6의 C1 저장 대국은 그대로 둔다.

## 저장 시점과 소유권

| 시점 | 기록할 값 | 금지할 동작 |
|---|---|---|
| 로컬 대국 생성 writer | 참가자별 이름·CPU ID·현재 stage, 고정 문구 원문/출처/revision, 적용한 캐릭터·팩 revision, 현재와 결산 후 가능한 Level별 P/N·미디어 참조, 명시 후보·기본값과 허용 이벤트를 한 transaction에서 복사 | revision만 보존하고 나중에 변경 가능한 설정을 조회 |
| 국 종료 writer | B2의 승자별 hora offset, actor/target, 화료 당시 stage, 엔진 band와 C1 표시 순서에 대응하는 이벤트별 콘텐츠 사본 | 점수 재계산, 복수 승자 중 일부 생략, 화면이 다시 열릴 때 후보 재추첨 |
| 동풍전 정산 writer | 기존 정산의 stage_after, 기존 보충 1위/최종 4위 조건, 해당 슬롯의 원문·표시문과 참조. 단계가 바뀐 경우만 변경 단계 CG | 정산이나 단계 증가 재호출, 마지막 화료를 정산으로 대체 |
| GET/WS/ack/재시작 | 저장된 콘텐츠와 기존 cursor를 읽는다. ack는 기존 한 칸 확인만 수행 | 현재 설정으로 소급 보충, UI callback에서 음성/정산/생성 재실행 |

`game_registry.py`의 신규 생성→facts/entries, action→facts/entries, 별도 settle→settlement entry 경계를 유지한다.
`result_delivery.py`의 create·append·validation과 renderer의 버전 분기는 함께 변경해야 한다.
현재 DB CHECK는 delivery.version=1/content_mode=unbound만 허용한다. 새 대국에만 명시적으로 새 버전/모드를
지정한다. ALTER 전후 기존 FK·행·entry UUID·payload·acked ordinal·revision을 비교한다. 무차별 UPDATE나 GET backfill 금지.

## 콘텐츠 관계와 판정

- 대국당 불변 anchor 한 건, 표시 entry의 기존 event UUID당 불변 결과 한 건으로 분리한다.
  anchor와 생성 시 발생한 첫 국 entry, 이후 각 entry와 그 결과는 각각 같은 transaction으로 쓴다.
  anchor에는 필요한 참여 캐릭터·Level·관련 관리 자료만 넣고 미디어 파일 자체를 복사하지 않는다.
- 새 버전 validator는 사실/entry/콘텐츠가 일대일인지(유국·사람 승자의 명시적 기본 배경 포함), 참가자·stage·band·
  UUID가 일치하는지 검사한다. 누락/불일치는 기존 전달 오류로 처리한다. 허용 후보가 없는 정상 상태와 구분한다.
- CPU 화료는 actor==target이면 tsumo, 아니면 ron. B2가 기록한 band 1~3으로 W09-S의
  `ron_band_N`/`tsumo_band_N` 키를 만든다. anchor의 **당시** 명시 후보에서 같은 Level·종류·이벤트인
  항목을 거르고, 남지 않으면 당시 지정 기본값에도 같은 조건을 적용한다. 셋 중 하나라도 누락됐다고 다른
  캐릭터나 점수 구간에서 빌리지 않는다. 복장/포즈는 같은 Level 계약을 따른다.
- 문구는 CPU 화료마다 win, 최종 4위는 defeat_stage_after, 기존 완료 보충 1위만 match_first를 사용한다.
  W09-M 슬롯의 현재값과 당시 이름을 한 번 평문 치환한다. 빈 편집과 미설정의 진단 상태를 보존하고,
  공통 선언·음성·W06 엔딩에 새 치환을 적용하지 않는다. 원본 B2 facts 및 C1 과거 문구는 불변이다.
- 선택된 항목 ID·revision·원문 P/N, 최종 P/N, 안정된 미디어 식별자와 digest를 기록한다. 파일 경로를
  조회 때 재해석하지 않는다. 생성 job의 가변 상태는 별도다. RNG는 기존 CPU·규칙·음성 및 승자 순서와 분리한다.
- 프롬프트 조합의 기술 기본안: 외모→해당 Level에서 적용할 상의/하의 속옷→복장 상태→상황→포즈→이미지
  종류별 구도. Positive와 Negative를 따로 줄바꿈으로 결합하고 원문·태그를 자동 수정하지 않는다.
  단계별 프로필·전신·기본 CG는 편집 화면에서 명시적으로 생성한다. 미등록이면 안내만 표시한다(Q-IMAGE A). 같은 최종 긍정/부정 프롬프트·모델/LoRA·workflow·생성 설정은 최초 seed와 이미지를 재사용한다(D08-a A). 재시작하면 현재 표시 중이던 결과만 당시 내용으로 복구한다(D08-b A). 누락·실패 때는 대사와 상태를 표시하고 진행을 허용한다. 다른 이미지로 대체하거나 자동 재시도하지 않는다(D08-c A). 실제 생성·캐시·명시 재시도는 W10/W11 범위다.

## 구현 순서와 검증

1. 새 버전의 anchor·entry 콘텐츠 스키마와 무손실 migration, 별도 writer의 실패 rollback부터 검증한다.
2. 실시간 설정을 조회하지 않는 선택·치환을 구현한다. 시작 직후 설정 편집/팩 갱신·이동/삭제 뒤에도
   원래 대국은 이전 값, 다음 새 대국만 새 값을 갖는지 파일 DB로 확인한다.
3. renderer에서 저장된 결과를 표시한다. 복수 론/유국/사람 화료, 최종 국→결산→엔딩 순서, stage3 보충/오마케,
   중간 승자 확인 후 cold restart 및 reset 경쟁, 누락 미디어에서도 다음 확인이 가능한지를 검증한다.
4. 기존 NULL/B2/C1과 웹은 종전대로. C2에서 실제 ComfyUI submit·새 모델/오디오·문구/이미지 seed·갤러리는 제외한다.
   전달 테이블의 기존 CHECK와 payload는 유지하고, 별도 콘텐츠 버전과 JSON 열로 새 대국을 구분한다.
