# W09-B2 PR #104 — 수용 전 보완

검토 기준: main `8f041fc9c6efaf3e229272114ffa65a955375102`, PR #104 head
`3574586f255593df4173437c8158e9a5fe712b4b`. 구현 branch는
`task/w09-b2-hand-results`다. 이 문서는 새 기능 계약이 아니라
[기존 B2 계약](W09_B2_HAND_RESULTS_CONTRACT.md)의 수용 검사와 보완 지시다.

## 확인 결과

- 독립 Linux Python3.12.14/RiichiEnv0.4.8에서 backend unittest171개/76.581초,
  dialogue pytest10개/0.11초 통과. `git diff --check` 통과.
- 최신 head의 Windows W04 run39203736892, W05 run39203736828은 success다.
  제출 문서의 이전 source `f9d2754` 근거와 최신 head 근거는 구분한다.
- 두 artifact를 다운로드해 source-sha.txt와 GitHub digest/실제 SHA256을 대조했다.
  W04/W05 각각 unittest171·대사10 통과. W05 브라우저4종, renderer30검사와
  일반 종료/재시작 JSON의 child 종료→window 파괴·host 정상 종료를 확인했다.
  read-only hand-results.json에는 revision0012, marker1 완료 대국의 sequence1..4,
  마지막 row만 terminal=true, 참가자 stage `[null,0,0,0]`이 기록됐다.
  이전 source의5국 기록과 다른 대국이며 반복 실행의 국 수를 고정값으로 보지 않는다.
- 기존 리뷰의 출력 잘림 문자열/대규모 문서·테스트 유실은 최신 diff에서 복구됐다.
  `test_content_packs.py`/`test_local_runtime.py`의 최종 차이는 migration 기대값뿐이다.
- 정상 저장·active replay 대조·completed 엔진 미호출·reset 보존 구현은 확인했다.
  아래 결함/검증 누락 때문에 아직 B2 수용·병합 완료로 취급하지 않는다.

| 최신 head 다운로드 근거 | ID / SHA256 |
|---|---|
| W04 artifact | 12165216214 / fe4964e33193bb3782ee3676fc3aef5e4588fff14762be74a802f7edfe2b9e7b |
| W05 artifact | 12165450166 / d8d9ceafde8fca6aa9bf867e9f54c70c39d390abb01719a6423cd6301be07829 |
| W05 내부 Windows ZIP | 1342f15b3c28c036a8895a69b4ee9264e4dbc46f61b79f96a08ff3e500af3f63 |

개인 Windows PC 실기·전원 차단은 실행하지 않았다. 새 frontend build/browser 실행이나
고정 seed 성능 비교 재실행은 하지 않았고, 위 Windows browser는 artifact 근거다.

## R1 — 과거 로그의 in-place 변경을 놓치는 prefix snapshot

`HandResultCollector.consume` 마지막의 `self._prefix = list(log)`는 이벤트 dict와
중첩 리스트를 입력과 공유한다. 이전 입력의 `start_kyoku.honba`나 `scores[0]`을 바꾸고
같은 log를 다시 주면 저장된 prefix도 같이 바뀌어 비교가 통과한다.

독립 재현: 유효한 start_game/start_kyoku를 consume한 뒤 원래 start dict의 honba를99,
scores[0]을99999로 변경했다. 두 번째 consume은 예외 없이 끝났다. 새 dict로 교체하는 기존
prefix 검사는 이 경우를 다루지 않는다. 실제 엔진이 과거 로그를 변경한다는 관측은 아니며,
기존 계약의 변경 감지 보장이 alias 때문에 성립하지 않는다는 최소 재현이다.

보완: 비교 기준을 입력과 분리된 snapshot으로 보관한다. 필요한 내부 원본 보관과
DB payload whitelist를 혼동하지 않는다. dict scalar/중첩 리스트의 in-place 변경,
이벤트 교체, 로그 단축을 모두 거절하고 정상 append는 허용하는 회귀를 추가한다.
기존 고정 seed 성능 비교는 단일 표본 근거로 보존하며 새 seed 탐색으로 확대하지 않는다.

## R2 — 중복 identity의 sequence 비교가 자기 자신을 비교함

`append_facts`의 `sequence_by_start`는 기존 row.sequence에서 만들고, 같은 row.sequence와
비교하므로 항상 같다. sequence가 국 offset의 원본 순서와 맞는지 검증하지 않는다.

독립 helper 재현은 저장 row 두 개를 sequence1/start4, sequence2/start1로 두고,
동일 payload/end/action_version의 fact를 start1→start4 순으로 재제출했다.
`load_rows`와 `fact_payload`만 fixture로 고정한 실제 `append_facts`가 이를 허용했다.
active cold replay는 별도 검증에서 거절하지만 append의 동일 identity 검사 자체는
계약대로 sequence 충돌을 거절하지 못한다.

보완: sequence가 나타내는 원본 국 순서와 batch 순서를 검증하고, 동일 identity는
기대 sequence/end/action_version/payload가 모두 일치할 때만 멱등으로 허용한다.
정상 동일 재시도와 기존 중복+새 suffix는 보존한다. DB의 sequence 교환,
역순/반복 batch 및 end/action_version/payload 충돌을 각각 검사한다.
과거 row를 덮거나 재정렬하는 자동 수복은 금지한다.

## R3 — 기존 검사표의 실제 B2 경로 회귀가 부족함

추가된6개 unittest는 정상 수집/복구 일부를 검증하지만 아래 항목까지 수용한 근거는 아니다.
기존 B1 점수 검사는 B2 collector/DB를 호출하지 않으며, 기존 웹 최종 action crash 검사도
marker NULL이다. 기존 local 정산 실패 검사는 엔진을 `_FinishedGame`으로 교체하므로
terminal 사실 row 보존·재접속을 증명하지 않는다.

| 기존 계약 항목 | 보완할 실제 검사 |
|---|---|
| 수집 | 같은 국 복수 hora+B1 대응, mixed win/draw, triple-ron draw, 본장 반복/같은 국 번호의 별개 offset, 여러 step 동안 pending 누적과 음향 drain 독립 |
| start batch | 시작 자동 진행에서 종료국이 생기는 제어 fixture로 version0 저장/active 복구·drain 대조 |
| create 실패 | parent flush와 결과 insert 오류 구분, 결과 flush/commit 실패 후 parent/rows/cache 없음, ActiveGameExists 오분류 없음 |
| action 실패 | 실제 결과 batch가 있는 action의 serialize/flush 실패·rollback·game 참조 폐기/cache eviction·같은 저장 턴 복구 |
| 영속 복구 | helper 비교만이 아니라 파일 SQLite의 row 누락/변조/sequence 충돌을 cold GET/WS 복구에서 거절, GET 무쓰기 |
| 최종 경계 | marker1 terminal row/action commit 직후 정산 전 재시작과 정산 commit 실패 뒤 재접속; row/payload 불변·단계 증가1회 |
| 저장 snapshot | 현재 캐릭터 이름/진행도 수정 후 저장된 참가자 이름/stage 유지, unknown marker/payload version controlled failure |
| 호환·모드 | NULL local active/completed 및 신규 web의 marker/rows, 완료 보충/오마케의 marker1 사실, reset 후 구세대 접근 거절·사실 보존 |

기존 검사에 assertion/fixture를 최소 확장해도 된다. 새 검사가 어떤 계약 항목을 검증하는지
PR/상태 문서에 대응하고 미검증을 완료로 쓰지 않는다. 새 자연 seed 탐색이나 콘텐츠 작성은 없다.

## 다음 Work

권장 환경은 저성능 Work다. 새로운 B3/표시 Task를 만들지 말고 PR #104를 보완한다.
최신 main/PR head·AGENTS/루트 문서와 본 문서/기존 계약을 먼저 읽는다.
동일 branch의 다른 작업이나 문서 이력을 덮지 않는다. 검토 문서 병합 후 main 변경을
구현 branch에 정상 병합하고 CURRENT_STATE/TASKS의 이번 보완 우선순위를 유지한다.

R1/R2의 수정 전 실패를 먼저 회귀로 고정한 뒤 최소 수정하고 R3을 보강한다.
전체 backend/대사·기존 build/browser와 최종 수정 source SHA의 W04/W05를 실행한다.
두 artifact source/hash, 내부 Windows ZIP hash 및 packaged read-only hand-results.json을
확인해 PR과 CURRENT_STATE에 정확히 기록한다. 개인 PC/전원 차단은 별도 미검증으로 둔다.

사실 payload/schema/규칙/CPU/음향 정책을 새로 설계하지 않는다. 필요한 내부 검증과
테스트·최소 문서만 수정하고 원래 계약의 파일 범위를 지킨다. 표시 API/ack/UI/gate,
문구 이전·CG/사운드 생성·Release/tag·직접 병합은 제외한다.
완료 시 commit/push하고 기존 PR #104에 제출한다. 수용 검토 뒤에만 후속 계약으로 진행한다.
