# W09-B1 — 화료 점수 수집 adapter

기준 main711b537(PR #101). `spikes/w09-a2-hand-score/README.md`의 0.4.8 공개 API 경로를
제품 adapter에 연결한다. 엔진/규칙/의존성/CPU는 변경하지 않는다.

기존 전 좌석 합법 행동 검증 후 선택된 RON/TSUMO가 있을 때만 engine clone에서 같은 action map을
한 번 실행한다. clone에만 네 점수 -1,000,000을 설정하여 기존 음수 점수 종료로 WinResult를 보존한다.
원본만 실제 행동·지급·대국 진행·정산을 담당하며 clone의 최종 점수·순위·종료는 사용하지 않는다.

`hand_scores.py`는 원본 누적 MJAI의 마지막 start_kyoku offset과 개별 hora offset,
승자의 actor/target/deltas/ura, 한/부/역/역만/지급/책임지불 및 band를 불변 tuple/dataclass로 읽는다.
원본 step 뒤 hora 전체 필드와 승자 집합을 대조하고, 최종 live WinResult가 남으면 점수 전체도 대조한다.
더블론 원본 순서를 유지하고 트리플론 유국은 빈 tuple이다. band는 공식 scoreAPI의 본장0·자론으로
만관 미만1/만관·하네만2/배만 이상3이며 delta에서 추정하지 않는다.

`last_hand_wins`는 가장 최근 step만 보유하고 다음 합법 step에서 비워진다. session 소비/
영속 queue·HTTP/WS 결과 DTO·표시 ack·대사/CG 연결은 후속 작업이다. 현재 자료를 UI에 새로
전송하지 않으며 기존 음향 ordinal/화료 대사를 변경하지 않는다.

누락/불일치 오류는 일반 band로 대체하지 않는다. action transaction이 rollback되고 registry가
진행한 game 참조를 폐기/evict한다. WS는 hand_score_failed 후1011로 닫으며 재접속은 DB에
commit된 action만 replay한다. 복구 중 오류도1011이며 캐시에 저장하지 않는다. 기존 완료 저장은
과거 결과를 재계산하지 않고 읽는다. 새 상태/migration/호환 분기는 없다.
콜드 REST active 복구도 같은 검증 오류를503/detail.hand_score_failed로 반환한다. 실제 화료가 포함된
저장 행동 replay에 오류를 주입해 수정 전 미처리 예외·수정 후503, 기록/캐시 보존과 오류 해제 후
정상 재복구를 확인한다. 사용자 입력 오류/invalid_cpu_snapshot으로 잘못 분류하지 않는다.

새 회귀는 친/자 론·일반 쯔모·본장/공탁, 더블론/트리플론 유국, 점수 경계·역만,
책임지불 친/자 론/쯔모, 합법 ANKAN→영상개화 및 KAKAN→창깡,
70번째 공개 draw/discard의 해저/하저와 원본 불변을 확인한다. 책임지불은 공개 setter로
구성한 합성 상태이며 책임 성립 전체 대국을 재현했다고 주장하지 않는다.
자연 회귀는 기존 seed701 Tier0/2의 steps/actions/최종 점수/순위/log digest와 대조한다.
기존 replay/policy1/2/3·정산/저장·음향은 전체 backend 회귀에 포함된다.
WS 회귀는 원본 진행 직후 오류 주입→action 미저장·캐시 폐기→동일 턴 재접속·재시도를 확인한다.

최초 fixture의 빈 legal observation·물리 ID/빨간5 처리·모델 필드명 및 mock property 오류는
테스트 입력에서 수정했다. 엔진 패치/새 seed 탐색 없이 같은 회귀를 재실행했다.
실행 환경 재개 시 미push 작업/로그가 소실되어 대화에 보존된 작업을 복원했고 다시 검증했다.
Linux/정확한 SHA Windows CI/package/artifact hash는 CURRENT_STATE 및 PR에 기록한다.
개인 Windows PC 실기·실제 CG/음향·결과 UI/영속 queue는 이번 범위가 아니다.
