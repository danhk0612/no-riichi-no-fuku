# W-DIFF-B 교정 후 독립 검증 — 측정 전 고정

- 기준 main d6cc88258739363e2408a80c99103b45c64b99bc (무늬 교정 포함).
- 사용자 2026-10-18 승인: 설정1~10/기본5, stage0/1/2→3/6/9,
  clamp(base+setting-5,1,10), 완료 보충1/오마케10 우선, 다음 대국 적용/초기화 보존.
- 수용: 서로 다른 실제 판단 설정10개와 저·중·고 강도 추세. 인접 통계 분리 요구 없음.
- 후보는 `backend/app/mahjong/difficulty.py`, version `tier2-bounded-lapse-suitfix-v1`.
  분자 [650,480,380,290,210,145,90,50,20,0]/1000, best shanten+1 이내,
  shanten/기존 성향 EV/물리tile 정렬, 종류 중복 제거 후6개. 추가 shanten 후보 가중치1/4.
  기존 Tier2 policy2가 먼저 판단하며 fold/비버림패 보존. 독립 RNG seed XOR0x574449464641.
- 후보/seed/표본/판정은 결과 확인 후 바꾸지 않는다. 실패 시 제품 연결 중단하고 근거 보존.
- 새 seed5000..5031, neutral/mixed/characters, L1..10+Tier2, 4좌석 순환: 총4,224대국.
  종전 calibration/run.py의 동일 공개 정보·상대·성향 정의와 유한 Pool 실행기를 재사용.
- 공통 관측 seed5701, 최대160개 ×8성향×10profile. 합법성/동일seed/6성향 불변,
  모든 인접쌍이 전체8성향 corpus에서 행동 차이>0, 각 레벨에서 캐릭터 간 행동 차이>0.
  모든 보호된 수비/비버림패 판단과 L10은 기준 동일. 합성 경계 검사는 별도 회귀로 수행.
- 각 context에서 low=L1..3, mid=L4..7, high=L8..10: 평균 점수 엄격 증가와 평균 순위 엄격 감소.
  각 band는 레벨별 동일 표본 평균. seed block 차이 95% 구간은 설명용이며 인접 유의성은 주장하지 않음.
  L10/Tier2의384대국 scores/ranks/steps/trace 완전 동일. 오류/illegal/5,000step초과는 실패.
- 새 check.py는 이전 v2 check를 복사해 production 후보 import/새seed/승인된 행동 기준만 변경.
  모든10profile에서12행동 저장 후 다른 현재설정을 전달해 끝까지 replay를 비교한다.
  이 검사는 연구 factory이며 제품 DB/Windows 복구 검증은 통과 후 별도 수행한다.
- gate 2독립process의 결정 digest 일치; sample12대국 별도 process 재현.
- 전체 검증 wall budget20분(8worker), 초과/실패 시 worker 종료, 부분 결과 보존.
  재검증만 통과하면 기존 W-DIFF-B 계약의 설정·snapshot·UI 구현을 진행한다.
