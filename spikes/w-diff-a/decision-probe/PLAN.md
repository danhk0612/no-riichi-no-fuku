# W-DIFF-A 판단 축 진단 — 실행 전 고정

기준 main e8a70b57db22727a861956ae6ee42c087057f6b8, tree
ac4dc24e89271b9dffcee8b1f7d1a132f1ff989e. PR #87 병합 확인, 열린 PR #35는 범위 밖.
사용자 2026-10-18 승인 범위. 기존 v1/v2·제품·fixture 불변. 본 PLAN과 실행 코드를
첫 측정 전에 commit한다. 결과 뒤 후보/순서/seed/중단 조건 변경·재시도·표본 추가 없음.

- 순서 000,001,010,011,100,101,110,111,tier2. 비트 순서 U/D/M.
  U0 기존 수용패수, U1 4*floor(ukeire/4). 최소 샹텐 유지, best-ukeire와
  cutoff(-4) 및 EV에 동일 양자화값 사용. D0 원 위험, D1 상대별 현물0/그 외
  원 기본위험 합(스지/벽 차감 제거). M0 원 가중추첨, M1 EV 최대.
  EV는 휴리스틱이며 화료확률/기대득점이 아니다. 강도 순서는 미정.
- 원 legal physical copy 모두 유지(종류별 통합 없음), 원 최소샹텐 후보 안에서
  정밀도별 cutoff, (-EV, physical tile) 정렬, 동점 tile 오름차순/동일tile 원 안정순서.
  000은 원 Tier2 policy2 행동/RNG 그대로 반환. 모든 조합은 원 policy2를 먼저 실행해
  비discard/fold(true일 때 안전패 선택이 성립하지 않아도) 결과 보존.
  다른 조합 weighted는 원 discard 직전 RNG 상태의 별도 복제본으로 choices 1회,
  max는 추가 draw0. shadow expert의 원 RNG 소비는 원본대로 유지한다.
  비트마다 다른 임의 seed를 주지 않으며 공통 quantile로 축효과를 분리한다.
  공개 Observation만 입력. 기존 성향6값/계수/타점/역/리치/울기/fold 정책 불변.
- 사전 gate: seed1701 원 Tier2 대국의 공개 관측을 균등 간격으로160개 추출,
  agent seed19001, 기존6성향+전부0.1/2.0=8성향. 각조합과 원본의 같은 입력 비교.
  합법성/000행동·RNG/비discard·fold/성향6값 보존, 결정적 반복,
  각축 특징 또는 후보/행동 변화와 조합별 성향간 다른 행동 존재를 확인.
  실패 시 대국 비교 중단. 축별 후보 변화/행동 차이와 단일프로세스 CPU/wall 비용 기록.
- 통과 후 기존 neutral/mixed/characters 상대 구성 그대로, index=(seed-2000)%6.
  9 label ×3 context ×seed2000..2015 ×4대상좌석=1,728대국.
  대상 seed=seed*10+seat, 원 opponent seed/성향 offset 규칙 유지.
  최대8worker, 각대국5,000step(다음 step 전 차단). 단일 상위 실행기 전체wall1,200초:
  두 독립 gate 프로세스/전체 대국/추출 trace 재현/전체 JSON 복구까지 포함.
  구현/문서/별도 fault-test 시간은 실험 wall 밖. 상위 종료 시 process group 전체 종료.
  gate/worker 오류·비교 실패·deadline이면 즉시 중단, 완료행/실패/미실행 격자 보존.
  지연 첫작업에도 남은 시간 timeout, 실행/대기 pool terminate/join. 재실행 금지.
- 4좌석 평균을 seed블록으로 원 Tier2 대비 점수/순위 paired delta.
  context별16블록 t근사95%(2.131), 8조합×3context×2지표48비교
  Bonferroni 정규근사 구간도 설명용 병기. 정규성/모집단추론 보장 없음.
  성향별 블록수2~3으로 매우 작음. 비트 효과/2축·3축 상호작용은 블록 내
  factorial contrast로 보고, 최댓값 조합 채택/레벨 정렬/10profile 튜닝 없음.
- 독립 두 gate 프로세스의 모든 행동·진단값 동일(시간 제외), 각 context×9label
  seed2000 좌석2의 전체 trace/결과 재현27건(비교표본 추가 아님).
  각8조합 seed1811, 사람12행동 JSON roundtrip 후 전체 잔여 human-turn/결과 비교.
  변경 현재설정을 실제 전달, 복구는 저장profile/새 대국은 변경profile 우선.
  unknown/변조profile 거절. factory 주입 격리이며 production policy3/파일DB 아님.
- 화료/방총률은 안정적인 기존 집계가 없으므로 미측정. Windows/인간 상대/holdout 없음.
  실패 시 수정을 통해 이번 실험을 재개하지 않고 원인/다음 승인 범위를 기록한다.
