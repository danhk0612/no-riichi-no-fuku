# W09-A2 — 동일 엔진 복제본에서 화료 점수 보존

## 판정

0.4.8 공개 `clone`/`set_scores`/`step`/`win_results` 경로를 **후속 구현 후보로 채택**한다.
중간 국 결과 소실을 피하는 기술 경로는 확보했다. 제품 적용 완료나 모든 특수 화료 검증 완료가 아니다.
W09-A의 native/viewer 경로는 계속 미채택이며 원자료를 수정하지 않았다.

화료 직전 원본을 복제하고 복제본의 네 점수만 -1,000,000으로 설정한 뒤 **동일 action map**을
한 번 제출한다. 기존 음수 점수 종료 분기가 다음 국 초기화보다 먼저 작동하여 WinResult를 보존한다.
실제 대국에는 원본 action만 제출하며 원본 점수·정산·RNG·규칙·CPU를 변경하지 않는다.
복제본의 인위적 최종 점수·순위·종료·로그 전체를 제품 상태로 사용해서는 안 된다.

## 근거와 한계

기준 main2291583. Python3.12.14/RiichiEnv0.4.8. 실행 전 고정한 PLAN/diagnose hash는
`evidence/analysis.json`, upstream hash는 `source-audit.json`에 보존했다.

| 검증 | 결과 |
|---|---|
| seed701..704 × Tier0/2 × 수집 전후 | 16대국, 12.582초 |
| 8쌍 steps/trace/점수/순위/log digest | 모두 동일, 기존 W09-A baseline과도 동일 |
| 39화료 경계/40화료자 | 원본·복제본 hora 전체 필드 동일 |
| 중간 32경계 | 복제본 결과 보존, 원본은 기존처럼 소실 |
| 최종 live 결과 7경계 | WinResult 전체 필드 동일 |
| 합성 공개 API fixture | 11건 통과 |
| 복제+fingerprint/검증 비용 | 평균1.387ms, 최대4.345ms; 제품 성능 수치 아님 |

합성은 친/자 론, 첫 턴 친/자 쯔모(천화/지화), 본장/공탁, 더블론, 트리플론의 기존 유국,
만관/배만 이상/국사무쌍을 포함한다. 자연 화료 band는 일반38/중간2/상위0이며 상위는 합성으로만 확인했다.
일반 쯔모는 자연 표본에 포함된다. 책임지불·영상/창깡·해저/하저를 독립 구성한 특수 fixture와 Windows는
미검증이다. 구현 수용 전에 이 경계 회귀 및 정확한 SHA의 Windows 검증을 수행한다.

합성 harness 오류2건은 실패 스크립트/traceback을 보존했다: 첫 턴 쯔모를 일반 점수로 예상한 오류,
트리플론 손패의 같은 패6장 구성 오류다. 기대값/입력만 고쳤으며 후보/자연 표본은 재실행하지 않았다.
분석 도구의 최초 system Python 실행은 설치환경 차이로 version 조회에 실패했고 venv로 분석만 재실행했다.
전체 측정 window는 단조시계로 직접 계측하지 못했다. 첫 worker 파일 mtime부터 분석 종료까지+30초로
추정한360.843초/600초를 `window.json`에 명시한다. 정확한 전체 실행시간이나 엄밀한 상한으로 주장하지 않는다.

## 고정 upstream 소스 검토

[RiichiEnv v0.4.8](https://github.com/smly/RiichiEnv/tree/0c1e575a3bf678e30e068149cd0fffa635d001a9),
PyPI0.4.8 provenance의 commit과 대조했다. 소스는 읽기 전용 조사이며 복사/빌드/패치하지 않았다.

- `riichienv-python/src/env.rs`: clone358~371, set_scores405~421, 결과getter606~609.
- `riichienv-core/src/state/mod.rs`: 쯔모 조건/평가/지급680~865, 론950~1112,
  다음 국 초기화1595의 음수 점수 종료, 초기화1729의 결과 clear. 화료 평가/지급은 기존 점수에 의존하지 않는다.
- `state/legal_actions.rs`: 점수 의존 검사는 리치1000점 조건이다. 수집은 이미 선택된 RON/TSUMO를
  포함한 동일 응답 map으로 한정하며 새 판단/리치 행동을 선택하지 않는다.
- native replay는 builder의 최종 left_tile_count와 iterator의 DealTile 재차감 구조가 보인다.
  이는 기존 해저/하저 역 증가의 원인 후보라는 소스 추론이며 수정/원인 확정 실험은 하지 않았다.

## 후속 구현 계약

제품 코드·DB·UI 변경은 없다. W09-B1은 이 후보를 격리한 점수 수집 adapter와 회귀까지만 먼저 구현한다.
0.4.8 고정, 원본 즉시 불변/최종 action trace 보존, 새 hora의 actor/target/지급/event 필드와
후보 WinResult 승자 집합을 대조한다. 트리플론 유국은 결과를 만들지 않는다.
불일치를 일반 band나 delta 추정으로 숨기지 않으며 원본 정산을 복제본으로 대체하지 않는다.
실패 시 writer rollback/cache evict 등 기존 경계와 맞춘 오류 처리를 구현 계약에서 검증한다.

점수 band는 엔진 WinResult의 한/부/역만과 본장0·자론 기준 공식 scoreAPI로 구분한다.
국 결과 영속 queue/고정 문구/표시순서/ack·UI는 B1 다음 단계다. 복수 화료는 원본 전원 보존,
별도 독립 RNG로 표시 순서1회 저장, 전환효과로 전원 표시하며 재진입에 재추첨/음향 재발행하지 않는다.
화료 당시 stage와 최종 패배 stage_after를 분리한다. 인간 기본 배경·오마케 화료 CG 정책은 유지한다.

## 저장 근거 재분석

설치된 0.4.8 환경에서 `python spikes/w09-a2-hand-score/analyze.py`는 저장 근거만 재분석하여
analysis.json과 동일성을 검사한다. diagnose는 evidence 존재 시 거절한다. fixtures는 처음 실패
입력을 보존한 실행 harness이며 별도 복사에서만 재현한다. 원자료 덮어쓰기/새 seed 실행을 하지 않는다.
