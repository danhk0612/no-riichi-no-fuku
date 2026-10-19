# W09-A2 — 동일 엔진 복제본의 화료 결과 보존 진단

기준 main2291583(PR #100). 제품코드·엔진/규칙·의존성 교체 없이 기존0.4.8 공개API만 조사한다.
W09-A 원본/실패 근거는 불변이다. 다음 한 후보와 예산을 **첫 실행 전** 고정한다.

- 후보: 실제 RON/TSUMO 제출 직전 env.clone(). 복제본의 네 score만 -1,000,000으로 설정하고
  같은 action map을 한 번 step한다. 음수 점수의 기존 종료 분기가 다음 국 초기화를 막으면
  복제본 win_results를 읽는다. 원본 점수/상태/agent/RNG/action map은 수정하지 않는다.
- 목적은 재평가용 조건을 재구성하지 않고 **같은 엔진 화료 계산 경로**에서 결과를 보존하는 것이다.
  복제본의 종료/순위는 제품 결과로 사용하지 않는다. 최종 정산은 원본만 담당한다.
- pinned upstream v0.4.8 =0c1e575a3bf678e30e068149cd0fffa635d001a9. PyPI0.4.8 provenance와 대조.
  소스상 화료조건/평가→지급→음수점수 종료 확인→다음 국 초기화 순서를 근거로 남긴다.
  점수 변경이 화료 합법성/계산에 영향을 주는 분기가 있으면 채택 중단한다.
- 자연 표본: 고정seed701..704 × 전 좌석Tier0/Tier2(policy2) × 수집없음/있음 =최대16대국.
  agent seed=seed*10+seat·기본성향, 최대5,000step/30초, 전체 실행/분석/합성fixture window600초.
  실험 실패 후 새 seed/재시도·대체 후보 탐색 없음. 첫 불일치/timeout은 중단·근거 보존.
- 수집 전후 trace/steps/scores/ranks/log digest 동일, 원본 즉시 fingerprint 불변,
  복제본/원본 hora actor/target/deltas/ura 등 동일을 모두 검사한다. final live WinResult와도 비교한다.
  원본 중간 WinResult는 사라지는 기존 한계를 감추지 않는다.
- 합성: 공개apply_event로 만든 합법 동시론·친/자·본장/리치봉, 역만과 특별조건은 가능한 최소 fixture로
  독립 확인한다. 실제 지원하지 않는 조건/fixture는 미검증 기록. 엔진 바이너리/규칙 수정 금지.
  점수 구간은 공식 calculate_score의 자론/본장0 및 yakuman flag로 분류한다. delta로 추정하지 않는다.
- 독립 재현은16대국의 baseline/collector 쌍 안에서 확인한다. 추가 자연 대국을 반복하지 않는다.
  시간/실패/원자료와 소스/설치binary hash를 보존하고 Windows 미실행은 명시한다.
- 통과 시에도 제품 적용은 후속 PR이다. 복수 화료 무작위 전원 표시와 표시 snapshot/복구를 보존한다.
  source API/규칙 변경·새계산기·ComfyUI/이미지/문구 생성·직접병합/Release/tag 없음.
