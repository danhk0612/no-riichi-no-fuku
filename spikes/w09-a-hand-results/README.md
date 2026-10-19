# W09-A 국 결과·화료 등급·표시/복구 진단

## 판정

**진단 완료, 점수 수집 경로 채택은 차단. 제품 구현 없음.** 권고는 원본 MJAI log의
국 identity/순서를 사용하되, 정확한 중간 국 점수 API 검증을 W09-B의 필수 선행으로 남기는 것이다.
점수 불명은 `unknown`이며 일반 구간/0점으로 바꾸지 않는다. viewer/native replay를 그대로
제품에 연결하거나 delta 크기로 화료 등급을 역추정하지 않는다. 후보 실패를 규칙 변경,
새 계산기/패키지·엔진 교체로 우회하지 않았다.

기준 source main `d90cc4dcb78c2f5ffa24e2a9a5b2fd32e36603b4`(PR #98 병합).
열린 PR은 #35(구 Docker 문서)뿐이며 이번 작업과 무관하다. GitHub GET으로 확인한 모든
tracked blob SHA와 로컬 준비 사본 `791fad6`을 대조해 차이 0, 전체 tree는
`99732c978df7757a28c332efafc8b1d5bd963393`으로 같다. 직접 Git 접속 지연으로
이 동일 tree 사본을 실행하고 GitHub Git-data API로 main 부모의 제출 commit을 만든다.
제품 backend tree `89349746cdd80386f1deff16ad378314ed0a67fc`를 변경하지 않는다.

## 재현·예산·증거

Linux Python 3.12.14 / RiichiEnv 0.4.8. 기존 환경 `/tmp/w08d-venv`를 재사용했다.
새 의존성·ComfyUI·실제 미디어/대사·사용자 DB는 사용하지 않았다. 아래 Python은 해당
기존 의존성 환경의 실행 파일로 바꿀 수 있다. 저장소 루트에서 실행한다.

```sh
python spikes/w09-a-hand-results/diagnose.py
python spikes/w09-a-hand-results/fixtures.py
python spikes/w09-a-hand-results/presentation_model.py
python spikes/w09-a-hand-results/analyze.py
```

`diagnose.py`는 evidence 폴더가 있으면 거절한다. 보존된 근거 위에 자연 표본을 다시 실행하거나
추가 seed로 실패를 희석하지 않는다. 별도 clean checkout에서만 원 실행을 재현한다.
분석만 재현할 때는 마지막 명령만 실행한다. `fixtures.py`는 합성 fixture이며 자연 대국을 추가하지 않는다.

- 사전 고정: seed701..704 × 전 좌석 Tier0/Tier2(policy2) × 수집 없음/있음 = **16대국**.
  성향은 각 agent 기본값 1.0, 좌석별 agent seed=`seed*10+seat`.
- 전체 실험 deadline 600초, worker당 부모 timeout/자체 alarm 30초, 최대5,000step.
  자연 표본 실행 **10.546초**, 최대 step/소요는 `analysis.json`/개별 JSON을 따른다.
  fixture/기존 경계 회귀도 같은 10분 window 안에서 마쳤다(`verification.json`).
- 8쌍 모두 행동 trace hash·scores·ranks·step·원본 MJAI digest 일치. 8개 고유 표본에서
  46국, hora40개, ryukyoku7개(복수 화료와 유국 결과가 섞일 수 있으므로 단순 합을 국 수로 쓰지 않음).
- 양쪽 실행의 공통 수동 계측은 trace/log·종료 경계 필드를 읽는다. 수집 있음은 추가로 첫 국 끝
  log를 복제하고, 대국 종료 후 복제 log의 viewer/native 후보를 평가한다. **후보 평가는 live
  step의 writer/lock 안에서 실행하지 않았다.** 실시간 매국 평가 비용/Windows 지연 검증이 아니다.
- viewer에는 `GameViewer(copy.deepcopy(log))`, native에는 소유 임시 JSONL만 전달했다.
  원본 env log의 before/after digest 불변. 이후 게임 RNG를 소비하는 callback이나 RNG 접근이 없다.
- 후보 비교는 고정 batch 완료 후 저장 근거로 실시했다. 첫 불일치에서 **채택**을 중단했으며,
  이미 완료된 뒤쪽 표본도 삭제하지 않았다. score 결과를 trace 통과와 혼동하지 않는다.
- `fixture-initial-failure.json`: 첫 복수 론 fixture가 반환 관측의 빈 legal action 배열까지
  선택하려다 IndexError. 반환 관측 중 실제 legal action이 있는 좌석만 제출하도록 harness만 고침.
  같은 합성 입력을 유지했으며 초기 실패를 보존했다. 제품/자연 표본 재실행 없음.

## 실제 데이터·수명

| 원본 | 확인 내용 | 한계 |
|---|---|---|
| `env.mjai_log` | `start_kyoku`→hora(0..N)/ryukyoku→`end_kyoku`, 마지막 `end_game`. start의 bakaze/kyoku/honba/oya/kyotaku/scores/tehais/dora_marker | 내부 hidden hand가 포함된다. UI에 원본 log를 노출하지 말고 필요한 결과 DTO만 보낸다 |
| hora | actor/target/deltas/type/ura_markers, 쯔모는 `tsumo:true` | han/fu/score band 없음. actor==target도 쯔모 확인에 사용 가능 |
| `win_results` | 마지막 화료 종료 후 seat→WinResult; is_win/han/fu/yakuman/yaku, ron/tsumo 지급액, pao_payer | 중간 화료 종료 경계 **32번** 모두 빈 dict. 같은 step에서 다음 국 초기화까지 진행돼 이미 소실 |
| observation.events | 한 실세계 hora를 여러 좌석에서 관측 | 원본 hora40개에 관측139개. 마지막 화료는 반환 observation에서 한 번만 보인 표본도 있음. 배열 content dedup/매번 index를 전역 ID로 쓰기 금지 |
| `pending_events()` | session에서 관측 events 누적 후 소비; `_restore`는 replay의 과거 pending을 비움 | 매국 영속 결과 큐가 아니다. 최종 pending에 의존해 국 결과 복구 불가 |

중간 경계의 한 step 안에 `hora,end_kyoku,start_kyoku,tsumo`가 함께 있었다.
다음 observation의 kyoku_index/현재 oya를 종료한 국의 값으로 쓰면 안 된다.
`start_kyoku`의 **log offset**을 국 identity로 고정하고, 그 국의 `end_kyoku`까지 모든 hora를
원본 순서대로 묶는다. `(bakaze,kyoku,honba)`만 사용하지 않는다(동일 식별 조합의 재등장 가능성).
국 경계는 누적 log의 append-only 여부/이전 prefix digest/offset을 검사한다. 짧아짐·prefix 변경·
끝 없는 결과/서로 다른 국 혼합·actor/target 범위 오류는 수집 실패로 보고한다.

기존 pending ordinal·action_version·음향 identity는 그대로 두고 **별도의 결과 source offset**을 둔다.
`AuthoritativeGameSession._step`에서 adapter.step 직후 누적 log의 새 suffix를 파싱하는 지점이 최소
identity 수집 경계다. CPU가 사람 차례까지 여러 step을 진행해도 모든 끝난 국을 보존할 수 있다.
`start()`가 자동 진행한 결과도 첫 create transaction에 포함해야 한다. 매국 점수는 이 경계에서
읽는 `win_results`로 확보되지 않으므로 점수 경로는 아직 차단 상태다.

## 점수 후보 비교와 중단 근거

| 후보 | 관측/비용 | 판정 |
|---|---|---|
| live WinResult 즉시 읽기 | 이미 다음 국으로 진행된 경우 빈 값. 값이 있으면 authoritative지만 전체 국 커버 불가 | 단독 채택 불가 |
| `MjaiReplay.from_jsonl(..., rule='tenhou')`→Kyoku→WinResultContext.actual/calculate | native 공식 API이나 생성 MJAI log의 최종 결과에서도 추가 yaku/han. expected_han/fu는 입력 log에 없어0 | **점수 불일치로 채택 중단** |
| `GameViewer.get_results` | 7개 최종 화료의 han/fu/yakuman/yaku가 live와 일치. raw 지급액은 본장 미포함. WinResult에 actor 없음 | 완전 결과 DTO로 바로 쓰지 않음. 한정 일치만 확인 |
| viewer han/fu→공개 `calculate_score`(honba0) | 새 계산기 없이3구간 정규화 후보. viewer 조건 재구성의 린샹/해저/더블리치·책임지불 정확성까지 입증하지 못함 | 조건부 후보, **미채택/추가 검증 필요** |

구체 실패: seed701/Tier0 최종 live는4han30fu, native는5han30fu(추가 yaku5).
seed704/Tier0 최종은 live4han30fu, native5han30fu로 **일반→고득점 band까지 달라진다**.
native actual과 같은 context.calculate가 서로 같아도 live와의 정확성 증거가 되지 않는다.
source별 raw 결과와 비용은 개별 JSON에 그대로 남겼다. viewer의 본장 없는 지급액을
live 지급액과 같다고 보고하지 않는다. 예: seed701/Tier0 최종 live ko2100/oya4000,
viewer ko2000/oya3900. 이 차이는 본장·반올림을 포함한 실지급과 본체값 차이이며 han/fu는 같다.

설치본 `visualizer/viewer.py`는 각 hora의 actor→WinResult 매핑을 직접 반환하지 않고, 유효한
res만 results에 append한다. 실패 시 GameViewer는 빈 결과로 fallback한다. 따라서 후속 조사에서도
hora 개수/actor 순서/round 개수 일치, is_win, 필수 필드 및 예외를 검사해야 한다. `zip`만 해서
누락된 화료자를 다른 결과에 연결하지 않는다. viewer의 함수에 HTML/Web viewer를 끼워 넣지 않는다.
코드상 `tsumo`에서 is_rinshan을 False로 다시 설정하고 Conditions의 haitei/houtei 등을
구성하지 않는 경로가 있어 특수 화료의 일반화 근거가 부족하다. native 오차의 정확한 내부 원인은
엔진 소스 조사 없이 단정하지 않는다. 라이브 판정 변경이나 native 재평가 보정은 수행하지 않았다.

공개 calculate_score 합성36조합: 친/자×론/쯔모×3han60/70fu,4han30/40fu,5/7/8/11/13han,
각 본장0/3을 확인했다. 분류 입력을 실제 delta로 바꾸지 않고, 기존 공식 score API의 **자 론,
본장0** 본체값으로 8,000/16,000 경계를 비교하는 방식을 조사했다. 실제 확정 yakuman은 항상
band3이고 반환 han 값만으로 일반 한수처럼 재해석하지 않는다. 독립 HandEvaluator의 국사무쌍
fixture는 yakuman=true/han26을 반환했으나 이 evaluator 기본 rule은 live default_tenhou 전체
경로 검증이 아니다. 실제 기본규칙의 역만·책임지불·린샹/해저/창깡은 **미검증**이다.
보너스가 있어도 등급을 delta에서 추정하면 안 되며, 실제 지급 일치 검사는 채택 후보 검증용으로만 사용한다.

## 복수 화료

공개 apply_event로 서로 다른 문전3색 손패 두 개를 구성하고 동일9s에 두 좌석의 합법 RON을
제출했다. 원본 log에 actor1/actor2의 hora가 모두 기록됐다. natural seed702/Tier0에도 같은 국에
복수 hora가 남았다. `sanchaho_is_draw=true`이므로 더블 론 가능과 트리플 론 유국 설정을 구분한다.
동일 국의 ryukyoku 존재만으로 화료자 전원을 버리지 않는다. 책임지불은 미검증이며 새 fixture를
만들기 위해 엔진 바이너리/규칙을 수정하지 않았다.

CG 표시 정책은 **사용자 결정 전 미확정**이다.

| 선택 | 효과 |
|---|---|
| A 원본 hora 순서로 승자별 배경을 순차 표시(권고) | 한 명도 버리지 않으며1국 안에서 하위 표시 cursor 필요 |
| B 결과에는 전원 표시하고 원본 첫 화료자를 배경 대표로 사용 | 단순하지만 다른 화료자는 배경 없음 |

어느 안도 점수가 큰 사람/최종1위만 남기거나 게임의 화료/정산 순서를 바꾸지 않는다.
플레이어 단독 화료는 기본 배경, 플레이어+CPU 복수 화료는 전원 데이터 보존 후 위 정책 결정에 따른다.

## 최소 DTO·소유(제안, 제품 schema 아님)

`HandResult v1 = {version:1, id, generation, session_id, hand_start_log_offset,
 hand_sequence, start:{bakaze,kyoku,honba,oya,kyotaku,scores}, end_log_offset,
 source_action_version, outcome:hora|draw|mixed, draw_event:null|{type,reason,deltas},
 winners:[{hora_log_offset,actor,target,win_kind,cpu_id:null|int,
 stage_at_hand:null|0..3,character_name,score:{status:verified|unknown,
 han,fu,yakuman,band:null|1..3,source_version},deltas,content_snapshot}],
 terminal, presentation_sequence}`。

- identity는 `generation/session_id/hand_start_log_offset`, 화료자 identity는 hora offset이다.
  결과 source offset과 기존 음향 ordinal, 추첨·이미지 job/cache ID를 구분한다.
- actor→CPU/이름/stage는 이미 저장한 대국 시작 `cpu_choices`/players snapshot에서 얻는다.
  stage는 해당 국 당시 값이며 최종4위 정산 후 stage를 참조하지 않는다. 오마케도3을 유지한다.
  플레이어의 cpu_id/stage는 null이다.
- content_snapshot은 캐릭터 content revision, 고정 대사 key/원문/한 번 치환한 표시 문구,
  허용 후보 stable ID/revision, 선택 복장·포즈·배경 P/N 원문을 소유한다(미선택은null).
  미승인 선택/조합 정책은 보류하며 모델/생성 seed/cache는 W10/W11의 책임이다.
- 현재 검증하지 못한 점수 경로를 verified로 표시하지 않는다. unknown을 band1로 보완하지 않는다.
  텍스트/기본 배경만으로 기본 대국을 유지하는 설계와 W09-B 착수 gate는 별개다.
- 최종 MatchPresentation v2와 W06 ending UUID/payload를 재사용하고 국 결과와 혼동하지 않는다.
  최종 결과는 stage_after, 화료 결과는 stage_at_hand다.

## 저장·표시·복구 경계 — 제안과 기존 구현 구분

기존 `GameRegistry.submit_action`은 engine을 진행해 action indices를 flush하고 API가 commit한다.
실패하면 cache evict→저장한 seed/actions로 재생한다. `settle`은 별도 transaction에서 최종 결과,
진행도/presentation과 필요한 ending_pending을 commit하고 publish_completed 후 발행한다.
completed 복구는 저장 결과만 읽고 재대국/재정산하지 않는다. 현재 UI는 human_turn/match_complete만
제공하고 국 결과 queue는 없다. 시작 시 active 다음에 ending_pending을 우선하므로 종료 직후
재시작하면 마지막 결과 표시를 건너뛸 수 있다. 현행 순서가 새 요구를 충족한다고 보고하지 않는다.

최소 영속 경계 제안:

1. create/action과 같은 SQLite writer/transaction에서 해당 action까지 새 국 결과DTO를 unique
   identity로 저장한다. 기존 action indices/policy/RNG는 바꾸지 않는다. 고정/저장 전 전송하지 않으며
   snapshot 저장 실패는 action 저장도 rollback하고 cache를 버린다. start의 자동CPU 진행도 포함한다.
2. 마지막 action 저장과 최종 정산의 기존 두 경계를 유지한다. 정산 전 crash는 저장 action 재생 후
   미정산일 때만 한 번 정산한다. 표시 ack는 stage 증가/정산을 호출하지 않는다. 국 결과가 이미
   저장됐으면 현재 설정으로 다시 resolve하거나 덮어쓰지 않는다.
3. 표시 queue는 원본 순서의 모든 미확인 국→마지막 국→기존 최종 presentation(순위/증가 후CG/
   고정 패배 문구)→기존 ending_pending→자유 대국이다. 비최종 국 확인 뒤 저장된 human_turn으로
   돌아가고 여러 국이 pending이면 모두 보존한다. 결과 확인 전에 사람 action/새 대국이 앞서지 않게 한다.
4. cursor/ack는 generation+session+event ID로 멱등 처리한다. 건너뛰기 거절, commit 후 응답 유실은
   같은 cursor를 반환한다. 파일load/생성/음악ended는 ack가 아니다. W06 ending ack와도 별도다.
5. GET/재시작은 가장 오래된 미확인 queue부터 복구하며 ending_pending을 먼저 보이지 않는다.
   다음 대국은 queue 완료를 확인한다. 표시 완료 저장은 ending ack/정산과 구분하고 CPU RNG나
   이미지 추첨을 실행하지 않는다. voice/SFX는 기존 replay 억제를 유지한다.
6. reset은 기존 generation을 갱신하고 active를 cancel한다. queue는 표시 대상에서 제외하되 과거
   snapshot/파일을 파괴하지 않는다. 늦은 socket/ack/job은 generation+session+표시ID로 차단한다.
   오마케도 같은 국 결과 queue를 쓰며 stage 진행/새 패배CG/엔딩 재발행 없이 기존 대사/음성을 유지한다.
7. queue가 없는 구 active/completed는 legacy 표시를 유지한다. 현재 content로 과거 log의 새
   snapshot을 자동 생성하지 않는다. 새 형식 version을 명시하고 기존 presentation v2 의미를 바꾸지 않는다.

`presentation_model.py`의11 assertion은 제안의 순수 합성 상태 검사이며 제품DB/GUI 검증이 아니다.
기존 local_play 회귀5개는 최종 단계/ending ack 멱등, 고정 대사 저장, 오마케, reset 뒤 늦은 legacy
정산 거절, commit 실패 rollback을 소유 임시DB에서 확인했다(2.338초).
새 국 queue/국 ack 응답 유실·Windows 재시작은 미구현/미검증이다. 진단만을 위해 Windows
package/CI를 새로 배포하지 않았으며 관계없는 전체build/회귀도 반복하지 않았다.

## 후속 시작 조건

독립 구현 지시문은 TASKS의 “W09-A 진단 후 구현 분해”에 있다. 관리/W09-B/W10~11/W11-U를
분리한다. **W09-B는 점수gate와 복수 화료 표시 정책이 미해결이므로 착수 차단**이다.
추가 진단은 기존0.4.8 공개API로 정확한 전 국 판정snapshot을 얻을 수 있는지, 또는 공식viewer의
조건/지급 검증으로 충분한지부터 한정 조사한다. 이번 예산을 연장하지 않았고 추가 자연seed,
의존성/엔진 교체·독자 점수 계산기를 구현하지 않았다. 추가 실행은 별도 명시 승인 범위에서 수행한다.
