# W09-A — 국 결과·화료 등급·표시 순서 진단

## 범위

기준 main `b64b26e`(PR #97) 이후 최신 정책 보완을 포함한 main에서 시작한다.
권장 환경은 고성능 Work다. 새 규칙/CPU/이미지 생성 구현이 아니라 기존 엔진의 결과 데이터와
보존 경로를 확인하고, 명확한 후속 구현 계약을 만드는 한정 진단이다.

확정 요구:
- 각 국 화료 NPC의 현재 복장 상태와 점수3구간(만관 미만/만관·하네만/배만 이상)의
  포즈·배경 프롬프트를 조합해 그 국 결과창 배경 CG로 사용한다. 단계는 바뀌지 않는다.
- 플레이어 화료는 캐릭터 CG 없이 기본 결과창 배경을 사용한다. 화료자 없는 국도 화료 CG 없음.
- 마지막 국 결과를 먼저 표시하고 그 뒤 동풍전 결산→최종4위 단계 증가→변경 후 단계 CG·고정 패배 문구다.
- 엔딩 후 자유 대국(기존 문서의 오마케)도 매 국 화료 CG를 동일 적용한다. 모든 stage3·난이도10은 유지.
  단계 변경/새 패배 단계 CG/엔딩 재발행은 없다. 기존 승패 대사/음성은 유지한다.
- 대사 텍스트는 캐릭터 고정 데이터다. 공유 문장 풀로 이전하지 않는다. 상황 P/N과 대사 소유는 별개다.

## 시작점에서 확인한 사실과 한계

제품 source `53d70f7`(PR #96 head, 이후 main은 문서 변경)에서 Python3.12.14/RiichiEnv0.4.8,
4p-red-east/default_tenhou, seed701, 네 좌석 Tier0(seed7010+seat) 표본을 조사했다.
440번째 step까지 완료했고6개 hora가 기록됐다. hora 필드는 actor/target/deltas/type/ura_markers와
쯔모일 때 tsumo였으며 han/fu/점수 등급은 없었다. 그중5개 중간 국 화료 직후 반환 state의
win_results는 비어 있고 최종 국만 화료자별 WinResult가 남았다. 이는 이 한 표본의 관측이다.

`AuthoritativeGameSession._step()`은 반환 observation들의 events를 수집하고,
`_advance_until_human_turn()`은 CPU 행동을 이어 간다. pending batch의 단순 배열 index는
엔진 전역 event ID나 국 ID가 아니다. 중복/누락 가능성과 마지막 국 event는 별도로 진단해야 한다.
`api/game.py`는 현재 human_turn/match_complete 및 대사/음향을 보내며 매 국 결과창 큐는 없다.

RiichiEnv0.4.8의 GameViewer.get_results(round_idx)는 MetadataInjector로 MJAI log를 재처리한다.
공개 score API와 이 경로는 **조사 후보**이며 제품 채택 결정이 아니다. viewer는 log를 참조하고
실패 시 빈 결과로 fallback하는 코드가 있으므로 deep copy와 실패 감지가 필요하다.
HTML/Web viewer를 게임에 끼워 넣거나 실패를0점/일반 구간으로 처리하지 않는다.

## 검증할 질문

1. 국 시작/끝·화료/유국·같은 국 복수 화료를 구분하는 신뢰할 수 있는 원본은 무엇인가?
   observation events, mjai_log, win_results 등 버전0.4.8의 실제 반환값과 문서/코드를 대조한다.
2. 중간 국과 마지막 국의 han/fu/역만·보너스 제외 화료 가치/등급을 어디서 고정할 수 있는가?
   riichi봉·본장·친/자·쯔모/론·책임지불이 섞인 단순 deltas 크기로 등급을 추측하지 않는다.
   기존 엔진 판정/공식 평가 API를 쓰는 가장 작은 경로를 비교한다. 새 점수 계산기를 만들지 않는다.
3. 다음 국으로 이미 진행된 뒤에도 결과를 재현하려면 어떤 필드/시점의 snapshot이 필요한가?
   winning CPU mapping·그 국 당시 stage/복장·score band·고정 문구/콘텐츠 revision의 소유를 명시한다.
4. 현재 session 단위 seed/action replay와 기존 result settlement를 보존하면서 국 결과 event를
   중복 없이 수집·저장할 최소 경계는 어디인가? 기존 event ordinal/음향 계약을 바꾸지 않는다.
5. 결과창 표시 순서는 어떻게 보존하는가? 복수 미표시 국 결과, 마지막 국 결과와 match_complete,
   다음 대국·전체 완료 엔딩·종료/재시작·ack 응답 유실·reset을 구분한다.
   UI가 국 결과를 확인하는 것과 게임 엔진 정산을 같은 작업으로 취급하지 않는다.
6. 복수 화료가 실제 규칙에서 가능한지 먼저 확인한다. 가능하면 화료자 전원을 결과에 보존하고
   한 배경 CG의 대표/순차 표시 정책은 선택지와 권고로 남긴다. 승자를 임의로 버리거나 규칙을 바꾸지 않는다.

## 한정 실행·재현

- `spikes/w09-a-hand-results/` 안에 재현 스크립트·작은 JSON 근거·README만 추가한다.
  소유 임시 DB/합성 테스트 상태를 사용한다. 사용자 DB/실제 미디어·문구를 사용하지 않는다.
- 전체10분, 대국당 최대5,000step·30초. 자연 표본은 seeds701..704 × 네 좌석Tier0 또는 네 좌석Tier2,
  각각 수집 없음/수집 있음 두 실행으로 최대16대국이다. 초기 agent seed와 구성은 실행 전 고정한다.
  강도 비교/튜닝 목적이 아니며 신규 표본을 추가해 실패를 희석하지 않는다.
- 수집 유무에서 행동 trace·최종 scores/ranks가 같아야 한다. 계측의 엔진/log/RNG 변형을 차단한다.
  viewer/재평가 조사에는 복제한 log를 쓰고 원본 before/after digest를 비교한다.
- 자연 표본에서 나오지 않은 경우는 최소한의 격리 fixture로만 확인한다: 론/쯔모·친/자,
  보너스 있는 화료·만관/배만 경계, 유국·마지막 국·복수 화료/책임지불(실제 지원되는 것만).
  공개 API로 만들 수 없으면 미검증과 재개 조건을 남기며 엔진 바이너리를 수정하지 않는다.
- 필드 누락/순서 모순/점수 불일치/trace 변형/예산 초과는 해당 후보 채택을 중단한다.
  기존 실패 자료를 보존하고 새 계산법/패키지 교체/규칙 변경으로 우회하지 않는다.
- 실행 source SHA/환경·명령·소요시간·관측/미검증·실패를 구분한다. Windows 실기는 실행한 경우만 주장한다.
  진단 전용으로 Windows package를 새로 배포하거나 관계없는 전체 회귀를 반복할 필요는 없다.

## 제출물과 다음 구현 분해

`README.md`에 원본 event/WinResult 필드, 수집 지점과 수명, 점수 등급의 정확한 근거,
순서/복구 state 초안, 후보별 비용·실패/한계와 단일 권고안을 남긴다.
채택을 제안할 DTO는 version/국 identity/화료자 목록/actor→CPU/현재 stage/score band/
콘텐츠 snapshot·표시 순서·게임 generation과 관계를 구체화한다. DB schema/API를 곧바로 만들지 않는다.

권고에 따라 다음을 독립 지시문으로 작성한다.
- 관리: 3점수구간의 포즈·배경 상황 P/N 및 캐릭터 고정 대사 편집. 기존 P/N·voice 독립/빈 값 보존.
- W09-B: 국 결과 수집/영속·표시 순서/복구와 텍스트. CG 생성은 아직 mock/미등록으로 분리.
- W10/W11: 미확정 생성 정책·ComfyUI 실제 기술 확인 후 구현.
- W11-U: 국 결과 배경과 최종 결산의 단계 변경 CG 연출 연결. 화료와 패배 CG를 혼동하지 않는다.

이 분해의 코드 변경 범위·선행·회귀·관련 Windows 검증 기준을 TASKS/ARCHITECTURE에 반영한다.
미응답 생성/복수 화료 표시 정책을 임의 확정하거나 이미지가 없어 기본 대국을 막지 않는다.
제품코드/migration/UI·seed/action replay/CPU·규칙/정산·기존 미디어·음향을 변경하지 않는다.
외부 모델/새 의존성/ComfyUI 실행·콘텐츠 생성·Release/tag·직접 병합·후속 Task 구현은 금지다.
