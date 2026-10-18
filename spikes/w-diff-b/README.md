# W-DIFF-B 독립 재검증과 제품 연결

측정 전 PLAN/source freeze 후 후보 변경 없이 실행했다. 이전 연구 원자료는 보존했다.

| 상대군 | 저 평균점수/순위 | 중 평균점수/순위 | 고 평균점수/순위 |
|---|---|---|---|
| neutral | 18632.03 / 3.3385 | 21783.20 / 2.8867 | 23650.26 / 2.6927 |
| mixed | 18343.23 / 3.2786 | 22368.16 / 2.8203 | 24274.22 / 2.5469 |
| characters | 18450.78 / 3.3073 | 21784.38 / 2.8926 | 25310.16 / 2.4948 |

모든 상대군에서 저→중→고 점수 증가·평균 순위 감소. 인접9구간 유의성은 수용 조건이 아니며 주장하지 않는다.
L10/Tier2 384대국 완전 동일. 공통160관측×8성향×10profile의 합법성·성향값·보호 판단·실제 행동 차이 및
두 독립process digest 일치. 10profile 저장12행동 후 완주 replay, 12표본 대국을 별도process에서 재현했다.
성향6값을 보존해도 낮은 레벨의 실수가 행동상 성향 표현을 약하게 할 수 있다. corpus의 수비 표본 규모는
이번 corpus의 fold는0이므로 합성 보호 경계 검사와 구분한다. 전체대국의 profile fold 보호 횟수는12,893회다.

원본 full measurement는 4,224대국 후 tuple/list 비교의 표현 차이에서 중단했다. 양쪽 JSON 정규화 및
분석만 재개하는 seed 초기화를 고쳤고 seed/profile/상대/표본/판정은 바꾸지 않았다. 원본실패 log, 모든 rows,
analysis log와 고정 source 해시·전체 wall span 상한 541.223초(20분 예산 이내)는 execution.json에 보존했다.
`result.elapsed_s`는 복구 분석8초이며 전체 실험 소요로 읽지 않는다. 별도 band interval은 seed32block의
paired 차이를 사용한 설명용 t근사95% 구간이며 인접/다중비교 유의성을 뜻하지 않는다.

```sh
PYTHONPATH=backend python spikes/w-diff-b/validate.py
python spikes/w-diff-b/report.py
```

신규 로컬 policy3만 제품에 연결한다. settings/revision/start snapshot/UI/DB회귀 및 Windows CI 검증은
CURRENT_STATE와 제품 PR의 정확한 최종head 근거를 따른다. 기존 Tier1/2/과거 연구/legacy fixture는 수정하지 않았다.
