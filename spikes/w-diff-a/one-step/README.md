# 제한적 공개 1수 선읽기 — 격리 연구 결과

**구현·재현·계산 예산은 확인했지만 강도 개선은 입증하지 못했다. 제품에 채택하지 않는다.**
기준 main `4c883a0`(PR #88 병합), 사용자의2026-10-18 후속 승인으로 수행했다.
10개 난이도 profile·설정 공식·제품 agent/API/DB/UI는 구현하지 않았다.

## 고정 정의와 정보 경계

측정 전에 [PLAN.md](PLAN.md)와 실행 코드6개 파일(PLAN 포함)을 로컬 commit `8e73bb0`에
고정했다. source tree `14120d10a630c38067544c7fdc9f1d28550df253`를 동일 내용의 원격 commit
`55ff6e1a565ad9e2ed1d2a4e282c7e033ad44fdd`로 전송했다. 원격 전송은 실행 중이며 측정 전
고정 근거는 로컬 commit/hash다. 측정 후 실행 코드/후보/seed는 바꾸지 않았다.
사후 report/합성 검증/문서는 측정 도구와 구분해 sources에 식별한다.

`public-one-draw-v1`은 원 Tier2 policy2의 판단/RNG를 먼저 실행한다. 원 비discard/fold,
최소샹텐·best-ukeire−4 후보를 유지하고 그 안에서만 현재 discard→가상의 own draw1회→
다음 discard를 평가한다. 다음 최소샹텐 손패의 최대 수용패수 가중 평균 Q로
`ukeire'=0.75*현재+0.25*Q`를 만들고, 기존 타점/위험/종반·성향6값/계수로 **가중 추첨**한다.
원 discard 직전 RNG 복제본을 써 원 expert/엔진/콘텐츠 RNG 소비를 바꾸지 않는다.

이미 본 own hand/discards/melds/dora indicators를 물리ID set으로 중복 제거한다.
`4−공개수`는 미확인 수 가중치이며 실제 산패/타가 패의 확률 분포가 아니다. 가상 draw만
미확인 수에서1 빼고 discard는 되돌리지 않는다. 다음 실제 패·벽·타가 손패를 조회하지 않는다.
shape 완성에는 잎 proxy를 사용하며 역/실제 화료/방총 확률이나 실제 기대 득점을 예측하지 않는다.
타가 turn·울기/리치/새 fold 정책·추가 탐색 깊이·외부 AI는 포함하지 않는다.

한 판단에 최대50,000 샹텐 cache miss, 결정별 캐시이며 초과는 실패다. 시간에 따라 후보를
줄이거나 원판단으로 조용히 대체하지 않는다. baseline wrapper는 원 Tier2와 동일해야 한다.
수학적 cache/공개수/가상draw/예산 경계를 합성 손패로 별도 확인했다.

## 실제 실행과 강도 한계

Python3.12.14/RiichiEnv0.4.8/Linux, 최대8worker. 두 독립 비용 gate·288대국·추출9대국·
두profile JSON 전체 복구를 상위 deadline 하나로 실행해 **112.509초/1,200초**에 완료했다.
실패/timeout/제외/재시도0, 총141,135step·최대963step(대국 한도5,000).
모든96 baseline/원Tier2 쌍의 전체 trace/점수/순위/step/판단수가 같다.

3label(tier2/baseline/candidate)×3상대(neutral/mixed/characters)×seed4000..4007×4좌석.
기존 상대/성향 offset을 사용하며 이 표본은 사전 진단이다. 독립 강도 holdout이 아니다.
8seed 각각4좌석 평균을 한 블록으로 분석했다. 각 표의 구간은 **다중 비교 전** 설명용 t근사95%
(df7 계수2.365)다. 6지표 Bonferroni 정규근사도 analysis.json에 보존했으며 모두0을 포함했다.
정규성/독립성/무작위 모집단 추출이나 모든 성향·인간 상대 강도를 보장하지 않는다.

| 상대 | 원 Tier2 점수/순위 | 선읽기 점수/순위 | 점수차 [설명용95%] | 순위차 [설명용95%] |
|---|---|---|---|---|
| 중립 | 25,000 / 2.5000 | 23,768.8 / 2.6875 | -1,231.2 [-3,754.1, +1,291.6] | +0.1875 [-0.2559, +0.6309] |
| 혼합 Tier0/1/2 | 24,893.8 / 2.5625 | 24,393.8 / 2.4688 | -500.0 [-4,918.7, +3,918.7] | -0.0938 [-0.7350, +0.5475] |
| 기존 성향 Tier2 | 25,525 / 2.4688 | 24,746.9 / 2.4688 | -778.1 [-5,181.7, +3,625.5] | 0.0000 [-0.4741, +0.4741] |

평균점수는 세 상대 모두 낮았으나 작은 표본/넓은 구간으로 약화가 확정됐다는 뜻도 아니다.
이 후보가 더 강하다는 근거는 없으며 “선읽기니까 최고10으로 채택”하지 않는다.
단일 혼합계수/기존 rational pool/속도 위주 잎 proxy의 제한된 연구다. 모든 선읽기 방식의
실현 가능성·불가능성을 결론내리지 않으며 이번 결과 뒤 계수/seed/표본을 바꾸지 않았다.

## 비용·성향·재현

공통 seed2701 공개32관측×8성향×두wrapper=512입력을 두 독립 프로세스에서 검사했다.
시간 제외 전체 행동/진단값이 동일하며 hash는 execution.json에 있다. 같은 입력에서
baseline/원본 행동과 RNG, 모든 wrapper의 성향6값/원 비discard 보존·합법성을 확인했다.
**공통32입력에는 fold가0건**이었다. fold 검색 차단은 코드 경계와 별도 합성 시험으로 확인했으며
이 작은 corpus만으로 수비 상황의 폭넓은 실측 완료를 주장하지 않는다.

중립과 실제5성향 사이 버림패 종류 차이는 baseline/후보 모두 [12,0,12,0,12]/25였다.
전체 행동 차이도 [13,0,13,0,13]/32로 같다. 후보와 baseline 자체는 성향별6~8행동이 달랐다.
표현이 거의 사라졌던 직전 max 선택과 다른 결과지만 corpus가 다르므로 이전 수치와 직접
개선율을 계산하지 않는다. 값/몇몇 행동 차이를 모든 캐릭터 특성·비율 보존의 증거로 쓰지 않는다.

| 중립32입력 | 평균 CPU ms | CPU p95 ms | CPU 최대 ms |
|---|---:|---:|---:|
| baseline | 1.207 | 2.026 | 2.200 |
| 선읽기 | 24.175 | 62.183 | 136.571 |

후보의 공통 입력 최대 cache miss는26,923개였다. 연구 진행 한도 p95≤250ms/max≤1,000ms는
통과했지만 baseline보다 비용이 크다. 제품 지연 수용 기준은 확정하지 않았으며 전체 입력/
Windows/최악 지연/모든 PC 성능의 상한으로 일반화하지 않는다. 두번째 프로세스 시간도 보존했다.

- 고정 seed4000·좌석2의3상대×3label=9대국 전체 trace/결과를 독립 단계에서 재현했다.
- baseline/candidate seed2811의12개 사람 action을 JSON roundtrip 후 전체 잔여57/70턴의
  human-turn hash와 완료 결과가 같았다. 변경 현재설정을 실제 전달해 복구는 저장profile,
  새대국은 변경profile을 사용함을 검사했다. unknown/변조/bool profile을 거절했다.
- 이는 주입 factory 격리이며 production policy3 decoder/실제 파일DB 복구 완료가 아니다.
- 기존 backend unittest129개55.360초, 대사pytest10개0.11초 통과. 소형 합성 손패/정보/예산/
  보호 판단 검사8개, 알려진 통계 집계1개 및 기존 공용 deadline/종료4개 검사도 통과했다.
- 원본 agent/policy1/2/legacy fixture와 기존 v1/v2/판단축 도구/근거는 변경하지 않았다.
  제품/Windows/build/browser/개인 Windows/인간상대/강도 holdout은 미검증이다.

## 재계산과 다음 조건

기존 backend 선언 의존성을 설치한 격리 Python 환경, 저장소 루트에서:

```sh
python spikes/w-diff-a/one-step/test_search.py -v
python spikes/w-diff-a/one-step/test_forecast.py -v
python spikes/w-diff-a/one-step/test_report.py -v
python spikes/w-diff-a/decision-probe/test_deadline.py
python spikes/w-diff-a/one-step/report.py spikes/w-diff-a/one-step/evidence
```

`experiment.py`는 근거 폴더가 있으면 재실행을 거절한다. 기존 근거를 지우고 재실행하는 것이
아니라 다음 승인된 연구에서 별도 경로/PLAN을 고정해야 한다. report.py는 원자료로 통계만
재계산한다. 코드/환경/근거/기준 source 무결성은 sources.json과 verification.json을 따른다.

이번 승인 범위는 마쳤다. 선읽기 동작·비용 검증을 강도 개선/10단계 완료로 바꾸지 않는다.
추가 후보/범위/표본은 별도로 정하며 제품 채택·DIFF-*·B 게이트는 유지한다.
