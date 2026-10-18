# 공개 정보 1수 선읽기 — 측정 전 고정

기준 main 4c883a085e24aff1d9e0da7457315588be7f21f9, PR #88 병합.
2026-10-18 사용자가 제한적 1수 선읽기 설계·격리 검증을 승인했다.
제품/policy1/2/기존 연구/fixture는 보존한다. 10profile/B 채택이 아니다.

- 단일 후보 `public-one-draw-v1`, blend 분자1/분모4. baseline wrapper는 분자0.
  원 Tier2 policy2를 먼저 실행하고 원 비discard/fold/최소샹텐 및 rational 후보를 보존한다.
  후보별 현재 손패에서 discard → 공개 미확인 수 가중의 가상 draw1회 →
  최소샹텐의 다음 discard 중 최대 수용패수로 평가한다. 재귀적 선읽기/타가 turn/실제 벽 조회 없음.
- 각 물리tile은 공개 관측의 own hand/discards/melds/indicators를 set으로 중복 제거해 센다.
  미확인수=4−공개된 해당 종류 수. 이는 실제 산패/타가 손패 분포 확률이 아닌 휴리스틱 가중치다.
  첫 discard도 이미 본 패이므로 미확인수에 되돌리지 않는다. 가상draw 종류는 미확인수1 감소.
  shape 완성 시 미래 수용패수는 가상draw 후 남은 미확인총수, actual 화료/yaku 보장 아님.
  그 외는 다음 discard 후보별 34종의 샹텐 개선 수를 세어 최대값을 사용한다.
  `Q=Σ(미확인수*미래 수용패수)/미확인총수`, 분모0이면 현재 수용패수를 유지한다.
- 같은 원 rational pool에서만 `ukeire'=0.75*현재+0.25*Q`로 기존 휴리스틱 EV를 계산한다.
  타점/위험/종반과 성향6값/계수는 변경하지 않는다. 원 사전 discard RNG 복제본의
  choices1회, (-새EV, tile) 정렬. 원 shadow RNG 소비와 엔진/콘텐츠 RNG는 불변.
  물리copy 추첨은 기존대로, 선읽기 계산만 같은 패 종류에서 재사용한다.
- 결정별 샹텐 cache는 그 결정에만 존재하며 최대50,000 cache miss. 초과는 명시 실패,
  원 판단 fallback/시간 기반 탐색 축소/표본 제외 없이 중단한다. 캐시는 sorted34종개수→샹텐.
  엔진의 순수 calculate_shanten만 사용하며 canonical136ID 손패로 전달한다.
- 먼저 작은 합성 손패로 공개 미확인수/샹텐/copy/가상draw/예산 경계를 검사한다.
  그 뒤 소스 hash/PLAN을 고정하고 실제 관측 측정을 시작한다. 측정 후 후보 수정/재시도 금지.
- 비용/합법 gate: seed2701 원 Tier2 대국의 공개 관측에서 균등32개, agent seed29001,
  기존6성향+all0.1/all2.0의8성향 × baseline/candidate. 독립2프로세스 결정적 결과 비교.
  기존 RNG/성향/원 비discard·fold 보존, baseline 행동 동일, 합법성 검사.
  단일프로세스 후보의 중립 CPU p95≤250ms/max≤1,000ms를 연구 진행용 한도로 둔다.
  이는 사용자 승인 제품 지연 기준이 아니다. 실패해도 gate 원자료/실패를 보존하고 대국은 미실행.
  성향 간 행동/패종류 차이는 수용 판정 없이 기록하며 값 보존만으로 표현 보존을 주장하지 않는다.
- 통과 시 tier2/baseline/candidate 3label×neutral/mixed/characters3context×
  seed4000..4007×4좌석=288대국, 최대8worker·각5,000step. 독립8seed 블록(4좌석 평균) 분석.
  후보 대 원 Tier2의 점수/순위·설명용 t근사95%(df7:2.365), 6지표 Bonferroni 정규근사 병기.
  강도 단조/10구간/인간상대·정밀한 모집단 추론은 주장하지 않는다.
- 단일 상위 전체wall20분: 두 gate·288대국·고정seed4000좌석2의9대국 추출재현·
  두 wrapper profile seed2811의12행동 JSON 저장 후 전체 잔여 재현까지 포함.
  현재 설정을 실제 전달하고 복구는 저장profile/새 대국만 변경profile 적용. unknown profile 거절.
  사전 테스트·분석/문서 시간은 실험 wall 밖. gate/worker/재현 실패·deadline 시 process group 종료,
  완료/미실행 수 보존. 비교 실패를 고쳐 이번 실험을 재개하지 않는다.
- 기존 공통입력/대국/PLAN/원본 source를 덮지 않는다. Windows·production decoder/파일DB·
  별도 강도 holdout·10profile 보정·제품/CG/정산/음향/리치·울기·fold 변경은 미실행.

결과는 개선/악화/비용 실패를 그대로 기록한다. 한 후보 비교로10단계 실현 가능/불가능을 확정하지 않는다.
