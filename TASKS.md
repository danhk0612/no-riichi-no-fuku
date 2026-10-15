# 개발 Task

모든 미착수 Task는 계획이며 실행 승인이 아니다. 상태는 구현/검증 사실로만 변경한다.
W00은 초기 분석·기준 문서 준비(완료); 본 파일은 후속 개발 명세다.
Task 목적·금지 범위·완료 기준 변경이 필요하면 사용자 결정 후 갱신한다.

## 순서와 우선순위

| ID | 작업 | 우선순위/상태 | 선행 | 권장 환경 |
|---|---|---|---|---|
| W01 | 기존 기능·회귀 기준 확정 | P0 / 기준 확정 완료(브라우저 환경 차단) | W00 | 저성능 Work |
| W02 | Windows 실행·엔진 번들 기술 검증 | P0 / 기술 검증 완료(Windows CI, 사용자 실기 미검증) | W01 | 고성능 Work |
| W03 | 실행·저장·프로필 정책 확정 | P0 / 정책·W04/W05 계약 확정 | W02 | 고성능 Chat |
| W04 | 로컬 저장·복구 기반 전환 | P0 / 완료(PR #61 병합) | W03 | 저성능 Work (구조 설계 필요 시 고성능 Work) |
| W05 | Windows shell·오프라인 게임 통합 | P0 / 구현·Windows hosted 검증·최종 검토 통과(개인 실기 미검증) | W04 | 저성능 Work |
| W06 | 고정 참가 명단·진행/오마케·초기화·사운드 | P0 / W06-A 설계 검토 통과, B/C 미구현 | W05, D04 | A 고성능 Work → B/C 저성능 Work |
| W07 | 콘텐츠·이미지 이벤트 계약 설계 | P1 / 결정 대기 | W01, D05~D10 조율 | 고성능 Work + 정책 조율 Chat |
| W08 | 캐릭터·공유 목록·후보 관리 | P1 / 대기 | W05, W07 | 저성능 Work |
| W09 | 공유 상황·대사·변수 연결 | P1 / 대기 | W08 | 저성능 Work |
| W10 | 독립 ComfyUI·Anima adapter | P1 / 대기 | W03, W07 | 저성능 Work |
| W11 | 이벤트 랜덤 조합·생성/파일 연동 | P1 / 대기 | W06, W09, W10 | 저성능 Work |
| W12 | Windows 통합·배포 준비 | P2 / 대기 | W11, D11 | 저성능 Work |

순차 경로: W01→W02→W03→W04→W05→W06.
W07 설계는 W02와 독립적으로 진행 가능하나 정책 결정은 필요하다.
W10 adapter는 W08/W09 관리 기능과 계약 확정 후 병렬 가능하다. 실행 host/API transport 파일은
W05가 먼저 확정한다. W08/W09는 공유 schema·UI를 만지므로 순차 진행한다.
병렬 작업 시 공통 models/API/main.tsx 및 기준 문서 수정 담당을 먼저 분리한다.

## Task 명세

### W01 — 기존 기능·회귀 기준 확정

- 결과: `5762267e2366fa5bdbdd69bc6f38672d141dcbc8`에서 unittest 72개, 대사 pytest 10개,
  frontend npm ci/build 통과. browser 4개는 Chromium 부재로 미검증. 코드→검사 대응·policy 1/2·
  legacy 보존·검증 누락/후속 조건은 [CURRENT_STATE.md](CURRENT_STATE.md)에 기록했다. 제품 변경 없음.

- 목적: 전환 중 보존해야 할 실제 동작과 재현 검증을 저성능 Work가 독립 사용하도록 정리.
- 범위: 기존 unittest·browser/live integration·legacy fixture를 읽고 실행 가능한 기존 검사 재현,
  규칙/CPU/HP/stage/복구/정산/CG 실패의 코드→검사 대응표를 CURRENT_STATE에 간결히 반영.
  누락은 기존 검사로 보장되지 않는 항목으로 기록. 실제 결함 수정은 별도 Task로 제안.
- 선행: W00 문서 PR 반영 또는 그 정확한 head에서 시작한다는 명시.
- 완료: 정확한 baseline SHA, 실행 명령/환경/결과/미검증과 보존 불변조건이 재현 가능;
  policy 1/2·seed/action replay, 중복 정산, CPU 부족/HP 0 보류 조건이 빠짐없이 인계됨.
- 금지: 제품 코드·의존성·migration·CPU 가중치·규칙·진행 정책 변경, 이미지 생성/바이너리,
  Windows 구현, 본 Task를 빌드 오류 수정으로 확대, 직접 병합/배포.
- 환경: 저성능 Work. 설계 선택 없이 코드/테스트 대조·기존 검사 실행·Git/문서 작업 중심.

### W02 — Windows 실행·엔진 번들 기술 검증

- 결과: code `a9268d4b3b5eed3b55b8b40e2f06bbf28a549cb5`, Windows Server 2022 x64 CI
  [38567208066](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38567208066) 전체 통과.
  Python 3.12.10/RiichiEnv 0.4.8 frozen + Electron 44.7.2, 한글/공백 ZIP 해제·health·same-origin
  REST/WS 108행동·12행동 복구·완료 정산 보존·포트 충돌/owned child 종료 확인.
  원본 source/frozen 72 unittest·10 대사 pytest 및 기존 browser 4개 통과.
  격리 spike/전용 CI뿐이며 제품 통합·기술 채택 없음. 정확한 hash/용량/조건은 CURRENT_STATE.
  clean Windows 10/11·OS 인터넷 차단·사용자 X 클릭/강제 종료 등은 미검증;
  사용자 증거는 PR #59 또는 Work 채팅, 실행법은 `spikes/w02/README.md`.

- 목적: 기존 엔진이 Python 사전 설치 없는 Windows에서 재사용 가능한지 증거 확보.
- 범위: 격리 spike에서 RiichiEnv 0.4.8/Python 3.12 x64 번들, Electron 우선 shell,
  대안의 WebView2 오프라인 요구 비교. dependency package 발견 오류, native DLL·migration/seed
  포함, 같은 origin REST/WS, ready/port/owned process 종료 검증. 제품 구조를 확정하지 않음.
- 선행: W01, Windows 실행 환경 또는 사용자 실기 결과 경로. 없는 환경은 미검증으로 남김.
- 완료: 실제 Windows 압축 해제 기동·health·동풍전·저장 재시작 증거 또는 정확한 차단과 재개 조건,
  후보별 재사용 범위/배포 부담/변경 파일 경계 및 W03 권고. 인터넷 차단 조건 구분.
- 금지: 라이브 사용자 DB/미디어 수정, 본 게임 재작성, 정식 패키징/Release, 자동 기술 확정.
- 환경: 고성능 Work. native/host/runtime/저장 경계가 얽힌 최초 검증.

### W03 — 실행·저장·프로필 정책 확정

- 결과: 2026-10-14 사용자 승인으로 여섯 정책 확정. REQUIREMENTS/ARCHITECTURE의
  로컬 저장·권한·writer·host 경계 계약을 따른다. 제품은 아직 미구현이다. 지원 OS/배포용
  Python patch 공급 조건은 W05 준비에서 확인하고 W12 전 확정한다.

- 목적: W04/W05가 설계 선택 없이 구현할 수 있도록 사용자 결정 확보.
- 범위: D01~D03와 관리 UI 통합/분리(D09), 지원 Windows·배포/데이터 경로·인증/프로필/슬롯·
  기존 데이터 이전 범위를 선택지/영향으로 제시. 채택된 실행/저장/수명/보안 계약을 문서화.
- 선행: W02 실제 증거/제약.
- 완료: 사용자 결정과 구조 경계·검증 기준·보류 기능·각 구현 파일 범위가 명시됨.
- 금지: 사용자 대신 기술/삭제/이전 정책 확정, 제품 기능 구현.
- 환경: 고성능 Chat. 좁혀진 선택의 집중 검토/상호작용. 복합 재설계 필요 시 고성능 Work.

### W04 — 로컬 저장·복구 기반 전환

- 목적: 확정 로컬 저장에서 행동 commit과 복구·진행 보존을 유지.
- 범위: W03 저장/프로필 계약 구현, Alembic/bootstrap/paths, 로컬 writer/동시 요청 제어,
  외래키/index/rollback·마지막 행동 후 정산 재시작, policy 1/2. 기존 데이터 이전은 승인 범위만.
- 선행: W03 확정 정책/구현 계약, W01 baseline. Windows UI/번들 버전 확정은 W05에서 다룸.
- 완료: schema/migration 재현, 진행/세션 동등 복구와 exactly-once, 동시·commit 실패 회귀 통과;
  사용자 자료 보존/전환 실패 재개 기준. 전원 차단 검증은 실측한 범위만 기록.
- 금지: CPU/룰/HP·완료 규칙, 공유 콘텐츠, ComfyUI, 미승인 기존 DB 덮어쓰기.
- 환경: 저성능 Work. ARCHITECTURE의 확정 경계로 구현하고 계약을 바꿔야 하면 별도 검토.
- 기존 검증 이력: PR #61 code SHA `3081dc56a2be95dd30ce0fa78a413da9b4bfeb29`에서
  Linux backend unittest 78/대사 pytest 10/frontend build와 Windows Server 2022 x64 hosted
  CI run [38572718064](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38572718064)이
  통과했다. artifact `11897978928`의 source SHA/test 로그 확인은 CURRENT_STATE에 기록돼 있다.
  이후 PR head `70c6d8bdc031803a713a324889e2f241c95750ac`도 Windows run 38573281946 및 기존
  78/10 성공이었으나 2026-10-15 검토에서 이름 저장·capability·read/write lock 결함이 재현됐다.
  이 기존 성공 이력은 보존하되 결함 보완/현재 수정 SHA의 검증으로 간주하지 않는다.
- 보완 검증: local profile의 PATCH→GET→별도 DB→runtime 재시작, REST/member/admin 및 WS의
  malformed capability 거절/4401, 기본 engine 동작 보존·local read/write 경계, 동시 writer/stale
  action/admin write, 파일 DB 정산 commit 실패 rollback/cache eviction/재기동 exactly-once를 추가한다.
  Linux Python 3.12.14 현재 검사 backend unittest 81, 대사 pytest 10, TypeScript/Vite build가
  통과했다. 정확한 code SHA `d46782bef4947ff448b2d40555ac4b387b2bc25a`의 Windows Server 2022
  x64 hosted run [38659727577](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38659727577),
  unittest 81/pytest 10/frontend build가 통과했다. artifact ID `11938706685` source SHA 및 ZIP
  SHA256 `c4f778a5cb4fcf51bc73ac59404dd2043c14968c6b77ca2956cb508d0e335bff` 검증은 CURRENT_STATE에 있다.
  기존 PR #61은 열린 상태다. Windows 사용자 UI·LocalAppData·OS 인터넷 차단·전원 차단 검증은 미실행이다.

### W05 — Windows shell·오프라인 게임 통합

- 목적: 기본 게임을 한 Windows 프로그램에서 실행.
- 범위: W03 확정 host에 React build/로컬 엔진 묶기, 기동 준비·포트·owned child 종료·오류 표시,
  확정 프로필 진입·복구 연결. 기존 테이블과 transport를 우선 재사용.
- 선행: W04, W02 증거와 W03 계약.
- 완료: Python/Node/Docker/PostgreSQL/ComfyUI 사전 설치와 인터넷 없이 기본 대국·결과·
  재실행 복구, UI 종료 시 owned 프로세스 처리, 사용자 데이터 보존을 실제 Windows에서 검증.
- 금지: UI 전체 재설계, ComfyUI 자동 기동, 다른 프로세스 종료, 진행 정책 변경, Release.
- 환경: 저성능 Work. 승인된 실행 계약 구현; 범위 밖 구조 판단은 인계.

### W06 — 고정 참가 명단·진행/오마케·초기화·사운드

REQUIREMENTS D04/R16~R19가 확정 정책이다. CPU HP는 별도 시스템이 아니며 기존 stage를 유지한다.
제품 구현은 저장/정산/초기화·엔딩/사운드의 계약을 좁힌 뒤 순차 진행한다.

#### W06-A — 저장·복구·리소스 구현 계약 설계 (검토 통과)

- 결과: main `e48aae9` 소스와 저장/정산/UI를 대조하고 ARCHITECTURE의 W06-A 계약을 작성했다.
  제품·migration 실행·새 Windows 검증은 없다. 2026-10-15 재검토에서 최초 명단 후보 API와
  local mutable HTTP의 response 전 commit/실패 검증을 명확히 했다. B는 A 병합 후 착수한다.
- 환경: 고성능 Work. 제품 코드 변경 없이 문서 설계/작업 분해/소스 대조.
- 범위: 게임 공통 자료와 고정 참가 명단·한 플레이의 진행 상태·대국 snapshot/action log·상시 사운드
  선택 설정의 최소 관계, schema/migration/API/UI, DB writer/transaction/cache 경계.
  초기화 확인/현재 대국 종료/이전 socket·요청 차단/자료 보존, 기존 저장 호환,
  엔딩 pending/표시/오마케 전환과 재접속·리소스 참조/재생 계약. 등록 CPU 삭제/비활성화가
  고정 명단·전체 완료 판정에 미치는 처리도 사용자 정책을 보존하는 최소 방식으로 설계한다.
- 완료: ARCHITECTURE에 구체 필드/관계·요청/응답·transaction/기존 저장 전환과 상태별 예시,
  TASKS에 독립적인 B/C 파일 범위·의존·검증·전체 지시문. 미확정 콘텐츠 D05~D11과 분리한다.
- 금지: 제품 구현/migration 실행, 무관 구조 정리, 실제 CG/음악/대사·더미 콘텐츠 생성,
  사용자 자료 초기화·삭제, 외부 오디오 생성 API/ComfyUI 기능, Release/tag·직접 병합.

#### W06-B — 진행·명단·초기화 구현 (A 검토 후)

- 환경: 저성능 Work. W06-A에서 확정한 최소 코드·migration/UI/API·회귀 구현.
- 범위: 참가 명단 확정/고정 및 대국 상대 선택, 플레이어 HP 제거, 완료 CPU Tier 0 보충,
  모든 참가 CPU 완료 판정·엔딩/오마케 상태, 오마케 Tier 2/진행·추가 이벤트 없음,
  확정 초기화와 저장/기존 세션 호환. 엔딩/사운드 실제 재생 연결은 C 계약과 분리한다.
- 완료: 미완료 인원 3/2/1/0, 참가 명단 밖 CPU 배제, 사람 4위 후 계속 플레이,
  완료 전 보충 CPU 승패 무변동/대사와 오마케 이벤트 억제, 정확히 한 번의 완료 판정,
  초기화 동시 요청·오래된 socket/지연 응답 차단·재기동 및 자료 보존 검사.
  기존 policy 1/2/legacy·local writer/정산 실패 회귀·정확한 SHA Windows CI/artifact 확인.
- 실행 기록: 2026-10-15 기준 main `24ed576`; 구현은 `task/w06-b-progression` PR로 제출한다.
  Linux backend unittest 88개, 대사 pytest 10개, frontend build와 임시 자료 보존 검사가 통과했다.
  exact-head Windows CI/artifact 결과 및 source/ZIP hash는 CURRENT_STATE의 W06-B 항목에 기록한다.

#### W06-C — 사운드 자료·설정 및 엔딩 리소스 연결 (A 및 B 검토 후)

- 환경: 저성능 Work. A의 등록/파일/API/재생 계약을 구현.
- 범위: 효과음 세트/배경음 목록 등록·관리, 설정의 상시 효과음 세트/사용 BGM 목록 변경,
  엔딩 CG/음악/대사 참조와 재생·완료 후 오마케 진입. 기존 캐릭터 고정 데이터·공유 후보
  관리 UI(W08)를 미리 전부 구현하지 않는다. 최소 등록/참조 경계는 A가 명시한다.
- 완료: 선택 설정 재시작 보존, CPU 명단과 독립 변경, 누락 리소스의 확정 처리,
  엔딩→오마케의 재접속/재기동·중복 이벤트 억제, 초기화 후 공통 등록/파일 보존.
  실제 제공 리소스 검증과 mock/미등록 경로를 구분한다. 실제 자료 없으면 실측 대기는 명시한다.
- 금지: 콘텐츠/모델/오디오 생성, 외부 생성 서비스 통합, 임의 seed/사용자 파일 삭제,
  새로운 플레이어/CPU HP·Tier 튜닝·대국 인원 변경·이미지 Level 자동 대응·ComfyUI 구현.

### W06-B/C 파일·검증 인계

계약 원본은 ARCHITECTURE의 W06-A 절이다. 아래는 구현 경계이며 별도 정책을 추가하지 않는다.

| Task | 수정/추가 가능한 파일 범위 | 선행/분리 |
|---|---|---|
| B | `backend/app/db/models/`의 local play/roster 및 session 모델·exports, `backend/alembic/versions/`의 0004 다음 migration, `services/game_setup.py`, `game_result.py`, `game_registry.py`, 새 `services/local_play.py`, `api/game.py`, 새 `api/local_play.py`, `schemas/game.py`, 새 `schemas/local_play.py`, `local_runtime.py`, `services/admin.py`의 명단 참조 보호 | A 검토/병합. local 경로만 새 규칙, 웹 legacy 유지. CPU agent 파일 수정/튜닝 금지 |
| B UI/검사 | `frontend/src/main.tsx`, `api.ts`, `CpuSelection.tsx`, `game/types.ts`, `game/MahjongTable.tsx`, 필요한 최소 `style.css`/새 명단·초기화·미등록 엔딩 컴포넌트, `backend/tests/` 관련 검사, `frontend/tests/`, `desktop/main.cjs`의 기존 smoke 경로, 기존 Windows workflow의 B branch trigger/검증 범위 | host 수명/보안 변경은 제외. 현재 smoke는 main.cjs 내부 구현이며 별도 파일로 분리하지 않음 |
| C | 새 `db/models/` media/effect-set/track 및 exports·B 다음 migration, 새 `services/local_media.py`, `local_sound.py`, 새 `api/local_sound.py`, `schemas/local_sound.py`, `local_runtime.py` route 연결, B `services/local_play.py`의 ending payload resolve, `api/game.py`의 commit 후 기본 SFX 전달 | B 검토/병합. B의 세대·정산·ack 계약 재작성 금지 |
| C UI/검사 | `frontend/src/api.ts`, `main.tsx`, `game/types.ts`, 새 최소 사운드/엔딩 설정·재생 컴포넌트, 필요한 style, 관련 backend/frontend tests·desktop smoke·Windows workflow, README | 최소 관리 화면만. W08 캐릭터/공유 후보 편집·외부 서비스·새 SFX hook 제외 |
| 공통 문서 | `ARCHITECTURE.md`, `CURRENT_STATE.md`, `TASKS.md` | 실제 구현/검증과 차이를 기록, 기존 검증 이력 보존 |

`db/session.py`의 W04 writer·인증·desktop/quit 계약은 우선 재사용한다. 계약상 불가능한 변경이
필요하면 해당 지점만 근거/영향을 보고하고 범위 밖 수정으로 우회하지 않는다.

| Task | 반드시 추가/보존할 검증 |
|---|---|
| B | 최소3·고정 명단/중복 확정·active 변경 참조 보호·명단 밖/추가 CPU 배제, 미완료 3/2/1/0·stage와 effective tier, 사람4위 HP 불변·보충CPU 1/4위 대사·오마케 대사/CG 억제 |
| B 저장 | 0004 파일 DB upgrade/반복 bootstrap/legacy active·completed/HP0·원 snapshot/policy1/2/108행동, 정산 commit 실패/rollback/evict/재시작, 두 start/두 reset/action·정산·reset 경쟁, stale WS/캐시/지연 응답 차단, cancelled/recent 필터, 초기화 자료 hash 보존 |
| B 엔딩 | 전체 완료/명단 확정 시 이미 완료인 경우, pending event 1개, 표시 중 재시작/중복 ack/ack 응답 유실·다른 event 거절, 미등록 안내로 omake 진입 |
| C | format/size/path/auth·한글/공백 파일명·업로드/metadata commit 실패 기존 파일 불변, 등록/설정 재시작·독립 변경/비활성 참조·빈 목록, B reset 후 등록/설정/파일 hash 보존 |
| C 표시 | event 중복·replay 무음·대사 없는 SFX·오마케 기본 SFX, BGM 목록 변경/엔딩 음악 분리, pending snapshot 불변·누락/실패/autoplay 거절·늦은 audio callback·명시 ack 후 omake 복구 |
| B/C 공통 | backend unittest·대사 pytest·frontend build·관련 browser/live-game·W04 writer/인증/정산 실패·W05 renderer/일반 종료/재시작. 정확한 head SHA Windows hosted CI/artifact source와 ZIP hash. 개인 PC/전원 차단은 별도 미검증으로 표시 |

기존 W05 workflow의 push trigger는 `task/w05-windows-shell`뿐이다. B/C에서 해당 작업 branch도
검증하도록 최소 확장하고 PR workflow의 exact head checkout을 유지한다. packaged smoke는 `desktop/main.cjs` 내부에 있다. 기존 smoke를 갱신하며 새 중복 smoke를 만들지 않는다.
C에 실제 제공 리소스가 없으면 mock/미등록 검사와 실제 CG·음악 출력 미검증(D11)을 분리한다.

### W07 — 콘텐츠·이미지 이벤트 계약 설계

- 목적: R07~R14를 구현 가능한 데이터/선택/표시 계약으로 좁힘.
- 범위: character P/N, 공통 Level/ID/label, 후보 참조, 상황→대사, 변수·삭제/빈 후보·신규 포함,
  event→상황, stage/Level·재렌더/복구·생성 지연·cache 및 파일 보존, 모델/LoRA·UI 경계 설계.
- 선행: W01. D05~D10은 사용자와 결정하며 미해결 경계는 구현 불가로 표시.
- 완료: 승인된 schema/API/UI 책임·migration/구 seed 호환·선택과 표시 불변조건·검증 예제가
  ARCHITECTURE/REQUIREMENTS에 있고 W08~W11 구현에 임의 정책 결정이 필요하지 않음.
- 금지: 실제 콘텐츠/CG 생성, 제품 구현, 규칙/CPU 정책 변경, 관리 부가 기능 추가.
- 환경: 고성능 Work, 좁은 사용자 정책 조율은 고성능 Chat.

### W08 — 캐릭터·공유 목록·후보 관리

- 목적: 외모/복장 P/N, Level별 공유 항목 및 네 종류 후보 선택·제외 편집.
- 범위: W07 확정 schema/API·migration·관리 UI, stable ID/label·CRUD·후보 참조·재시작 저장.
- 선행: W05, W07. shared dialogue 데이터 관리 포함, event 선택은 W09.
- 완료: R07~R09/R14 편집·저장, 캐릭터 간 격리·단계별 차이·삭제/빈 후보/추가 정책 검사.
- 금지: 공유 원문 캐릭터별 복제, 미승인 seed/갤러리/배치 기능, 생성 API·규칙 변경.
- 환경: 저성능 Work.

### W09 — 공유 상황·대사·변수 연결

- 목적: 실제 event에 맞는 허용 상황/대사를 기존 말풍선·결과로 전달.
- 범위: W07 event/상황/Level 정책, 상황 대사와 캐릭터 후보 교집합·변수 치환,
  기존 CPU별 event 대사의 승인된 호환, 기존 노출 확률/cooldown 경계 보존.
- 선행: W08 및 W07 D05/D10 결정.
- 완료: 상황별 다문장·캐릭터/Level 제외·변수·빈 후보·재접속/event 불일치 회귀 통과.
- 금지: 임의 조사/추가 변수·생성형 대사, CPU 판단·기존 노출 정책의 무관 변경.
- 환경: 저성능 Work.

### W10 — 독립 ComfyUI·Anima adapter

- 목적: 게임 정산과 독립인 로컬 생성 연결.
- 범위: W07 생성 계약, endpoint/object_info/workflow/model/LoRA/P/N, submit/status/result,
  실패/소유 job/종료 경계; Wayward 참고 파일 복사 시 개별 유래·고지·의존성 확인.
- 선행: W03 endpoint 수명/관리 UI 경계, W07 D07/D09 결정.
- 완료: mock 계약 검사 및 실제 StabilityMatrix ComfyUI/Anima 최소 생성 증거(별도),
  오프라인·미연결 게임 독립성. 사용자 모델/LoRA 배포 없이 설정 참조로 작동.
- 금지: Wayward/WML 의존, 게임 RNG/정산 결합, 승인 없는 ComfyUI 자동 기동/전역 interrupt,
  클라우드 AI·모델 번들·사용자 이미지 삭제.
- 환경: 저성능 Work. 미확정 node/model 기술 문제만 고성능 Chat 검토.

### W11 — 이벤트 랜덤 조합·생성/파일 연동

- 목적: 현재 캐릭터/Level 후보로 표시 이벤트의 이미지와 대사 연결.
- 범위: 허용 복장 상태/상황/포즈 선택→P/N 결합→파일 재사용/생성→표시,
  승인된 request/cache identity, 늦은 결과·재렌더·재시작·실패/대기 정책.
- 선행: W06, W09, W10, W07 D08 결정.
- 완료: 이벤트당 선택 안정성·허용 후보·설정 수정 후 재사용 기준·다른 캐릭터/시점의 지연 결과
  차단·파일 보존·ComfyUI 중단 후 대국 계속을 통합 검사. 실제 Windows/ComfyUI와 mock 구분.
- 금지: 렌더마다 재선택, CPU RNG 변경, 임의 cache 삭제/추가 백업·갤러리/배치 기능.
- 환경: 저성능 Work. 계약으로 해결되지 않는 복합 상태 문제는 고성능 Work로 분리.

### W12 — Windows 통합·배포 준비

- 목적: 오프라인 사용/데이터 보존/선택적 생성의 배포 후보 검증.
- 범위: 확정 설치/포터블 방식, 깨끗한 Windows 압축 해제·첫 실행·업데이트 데이터 보존,
  기본 대국/복구·ComfyUI 없음/정상/실패, 라이선스/고지·사용자 README·재현 build/CI.
- 선행: W11, D11 콘텐츠/권리와 사용자 테스트 환경.
- 완료: 정확한 SHA와 artifact·Windows 실측/미검증·의존 런타임/용량·업그레이드 보존 기록,
  공개 배포 가능한 범위 및 잔여 제한을 검토 가능하게 준비.
- 금지: 미승인 Release/tag/직접 병합, 모델/CG 권리 추측, 새로운 기능/대규모 정리.
- 환경: 저성능 Work. 공개 배포는 별도 명시 승인 후 별도 실행.

## W04 PR #61 보완 결과

이름 PATCH→GET→파일 DB→runtime 재시작 보존, REST/WS malformed capability 거절,
local 전용 write intent·동시 읽기·기본 engine의 원본 transaction 보존, 파일 DB 정산 commit
실패/rollback/cache eviction·재시작 후 exactly-once를 보완했다. 최종 code `455d400`의 실행
결과는 CURRENT_STATE를 따른다. 기존 보완 지시/성공 이력은 PR #61/#62와 Git에 보존한다.

## 다음 Work에 입력할 지시문 — W06-B

W06-A 문서 설계 검토/병합 후 사용한다. 권장 환경: **저성능 Work**.

```text
danhk0612/no-riichi-no-fuku의 W06-B만 수행해.
최신 main·현재 브랜치·열린 PR과 AGENTS.md 및 루트 기준 문서를 먼저 확인하고,
TASKS의 W06-B와 ARCHITECTURE의 “W06-A 구현 계약 — W06-B/C 인계” 전체를 따라.
A 설계가 검토/병합되지 않았거나 계약이 최신 코드와 충돌하면 그 지점만 보고해.
task/w06-b-progression에서 제품 구현·회귀·Windows 검증을 진행해.

범위는 Windows local runtime의 고정 참가 명단, HP 없는 새 진행 규칙,
stage와 effective_tier 분리, 엔딩 pending/event/ack와 미등록 화면, 오마케,
자료를 보존하는 초기화 및 기존 저장 호환이야. 웹 legacy/JWT/관리자 보안은 유지해.
ARCHITECTURE의 필드·API·상태·writer 순서·초기화 세대·표시 payload를 구현해.
새 프로필/슬롯/CPU HP를 추가하지 마. 기존 local stage는 전환 시 보존하고 명단은 명시 선택해.
최초 명단 후보 API에는 stage3도 포함해. 대국용 선택 가능 목록으로 명단 후보를 대신하지 마.
기존 active는 원본 agent/규칙 snapshot으로 끝내고 completed는 재정산하지 마.
새 대국에만 새 규칙을 적용하고 policy1/2·legacy seed/actions/RNG/fixture를 유지해.

local_play_states/roster와 session 필드/status migration은 기존 0004 다음에 추가해.
DB writer 예약→play/record 재조회→registry lock→commit→응답 순서를 지켜.
초기화는 active를 cancelled로 보존하고 local 진행/명단/엔딩만 재시작해.
이전 generation의 start/action/settlement/socket/cache/fetch/CG callback을 차단해.
정산 결과·stage·엔딩 event/payload는 같은 commit이며 실패 시 rollback/evict해.
mutable HTTP는 응답 전 명시 commit/function scope를 보장하고 override 후처리 순서를 가정하지 마.
start/roster/reset/ack commit 실패 시 HTTP 성공/새 세대·event 비노출 회귀를 추가해.
명단 CPU 비활성화는 409로 거절하고 새 등록 CPU가 명단·완료 대상에 자동 포함되지 않게 해.
오마케는 Tier2·진행/CG/캐릭터 대사/추가 이벤트 없음, 기본 마작 규칙/표시는 유지해.
완료 전 보충 CPU는 Tier0·stage 불변·기존 match_first/last 대사를 저장해 재접속에도 유지해.
엔딩 리소스 등록/사운드 재생은 C로 남기고 null payload·미등록 화면·명시 ack까지 연결해.

파일 범위는 TASKS의 B 파일 목록을 따라. 무관한 리팩터링/UI 변경·CPU 튜닝은 하지 마.
backend unittest/대사 pytest/frontend build와 관련 browser/live-game을 실행해.
미완료 3/2/1/0, 명단 밖 배제, 사람4위, 보충1/4위, 오마케 이벤트 억제를 검사해.
파일 DB에서 action/reset/settlement 경쟁·동시 reset·마지막 행동 뒤 미정산 재시작·정산
commit 실패·엔딩 ack 유실·이전 socket/지연 응답·캐시 우회·재기동을 검사해.
등록 자료·설정·미디어 hash가 초기화/전환 전후 보존되는지 임시 자료에서 확인해.
기존 legacy/policy1/2·local writer/인증·일반 종료 회귀를 유지해.
정확한 수정 head SHA의 Windows CI·packaged renderer/일반 종료·재기동·artifact source SHA와
ZIP hash를 확인해. 기존 smoke의 명단 없는 직접 start도 새 흐름으로 갱신해.
Linux/Windows hosted/개인 PC/전원 차단·미등록 resource를 분리해 기록해.

ARCHITECTURE/CURRENT_STATE/TASKS에 실제 결과·미검증·C 재개 조건을 반영해.
브랜치 commit/push·PR 제출·검증 CI는 허용한다.
직접 병합·Release/tag·W06-C 착수·ComfyUI·외부 오디오 API·콘텐츠 생성은 하지 마.
실사용 DB/파일을 수정하거나 기존 자료를 삭제·자동 초기화하지 마.
```

## 후속 Work에 입력할 지시문 — W06-C

A 및 B 검토/병합 후 사용한다. 권장 환경: **저성능 Work**. B와 병렬 작업하지 않는다.

```text
danhk0612/no-riichi-no-fuku의 W06-C만 수행해.
최신 main·현재 브랜치·열린 PR과 AGENTS.md 및 루트 기준 문서를 먼저 읽고,
TASKS W06-C와 ARCHITECTURE의 “W06-A 구현 계약 — W06-B/C 인계” 전체를 따라.
A/B 검토·병합과 B의 실제 schema/API/검증 결과를 먼저 확인해.
task/w06-c-sound-ending에서 최소 사운드 등록·선택과 엔딩 리소스 표시/재생을 구현해.

local_media_assets/sound_effect_sets/background_tracks와 공통 설정을 B 다음 migration으로 추가해.
등록/수정/비활성화·media 업로드/file·sound-selection·ending-resources API와
게임 내부 최소 관리/설정·엔딩 화면만 구현해. 캐릭터 P/N/공유 후보 관리 UI는 W08로 남겨.
초기값은 효과음 null/BGM 빈 목록/엔딩 미등록. 실제/더미 CG·음악·대사를 생성·seed하지 마.
asset UUID/상대 key·한글 경로·형식/크기·root 이탈 보호·인증·immutable 파일 계약을 지켜.
파일 교체/참조 해제 시 기존 파일을 삭제하지 마. hard DELETE/자동 청소/변환 기능은 추가하지 마.
명단과 사운드 선택은 독립이고 진행 중 설정 변경·재시작 보존을 지원해.
B 엔딩 event/ack/generation 계약을 재설계하지 말고 리소스 resolve만 연결해.
pending payload는 완료 시 한 번 고정하며 이후 설정 변경으로 바꾸지 마.

선택 BGM은 목록 순서 순환, 기본 마작 6개 SFX는 대사 존재와 독립시켜.
commit 뒤 event identity로 중복/복구 과거 재생을 막고 오마케에서도 기본 SFX는 유지해.
오마케 캐릭터 대사/CG/승패 이벤트는 계속 억제해. 캐릭터 voice/새 SFX hook은 추가하지 마.
엔딩은 일반 BGM 중지→등록 CG/음악 1회/평문 대사→명시 계속하기 ack→오마케 순서야.
미등록/누락/비활성/재생 실패/autoplay 거절은 안내·무음으로 처리하고 대국/계속하기를 막지 마.
음악 ended나 GET/파일 실패로 자동 ack하지 마. pending 재기동은 같은 엔딩,
ack 응답 유실 뒤는 omake로 복구해. 초기화/화면 이탈/늦은 load/ended callback도 세대로 격리해.

TASKS의 C 파일 범위·검증표를 따라 backend/frontend/browser 및 기존 B/legacy/writer/정산 회귀를
실행해. 실제 사용자 폴더 대신 소유 임시 자료로 파일/설정/초기화 보존을 검사해.
정확한 수정 SHA의 Windows CI·artifact source SHA/ZIP hash·packaged 흐름을 확인해.
mock 재생/미등록 경로와 실제 제공 리소스의 CG 표시·오디오 출력 검증을 구분해.
실제 자료가 없으면 완료로 과장하지 말고 PR에 D11 실측 대기와 정확한 재개 조건을 남겨.
사운드 설정·pending/ack 후·reset 후 재실행과 한글/공백 경로를 검사해.

CURRENT_STATE/TASKS/ARCHITECTURE와 사용자 README를 실제 구현 범위에서 갱신해.
브랜치 commit/push·PR 제출·검증 CI는 허용한다.
직접 병합·Release/tag·W07 착수·공유 콘텐츠 정책 확정·ComfyUI·외부 사운드 생성 서비스·
파일/콘텐츠 생성·사용자 자료 수정/삭제는 하지 마.
```
