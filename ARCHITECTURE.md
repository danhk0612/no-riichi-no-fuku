# 구조와 전환 검토

## 현재 실제 구조

분석 기준 main `ba4fc43a89a39a328c7c308d6c90e145ab489d58`.
`frontend/src/main.tsx`, `api.ts`, `game/MahjongTable.tsx`가 인증·CPU 선택·대국·결과를
연결한다. Vite 개발 proxy 또는 nginx가 같은 origin의 `/api` REST/WS를 FastAPI로 전달한다.
`file://`로 HTML만 열면 상대 API와 `window.location.host` 기반 WS가 작동하지 않는다.

| 책임 | 실제 코드 |
|---|---|
| 인증/권한·웹 API | `backend/app/api/`, `core/security.py`, `core/config.py` |
| 규칙/턴 진행 | `mahjong/riichienv_adapter.py`, `mahjong/session.py` |
| CPU 판단 | `mahjong/tier0.py`, `tier1.py`, `tier2.py`, `services/game_setup.py` |
| 저장/복구/정산 | `services/game_registry.py`, `game_result.py`, `db/models/game_session_record.py` |
| 대사 | `services/dialogue_service.py`, `seeds/cpu_dialogues.json`, `api/game.py` |
| CG 파일/metadata | `services/result_assets.py`, `db/models/cpu_result_asset.py`, `api/admin.py` |
| DB/bootstrap | SQLAlchemy 2, Alembic 0001~0004, `services/bootstrap.py` |
| 기존 운영 | `docker-compose.yml`, `backend/Dockerfile`, `frontend/nginx.conf` |

RiichiEnv는 정확히 0.4.8로 고정하고 `4p-red-east` + `GameRule.default_tenhou()`를 사용한다.
CPU 성향 6개와 stage 난이도는 별개다. 새 대국 CPU snapshot은 policy 2,
버전 없는 기존 snapshot은 policy 1이다. seed + CPU/좌석 snapshot + 사람 합법행동 index
로그로 대국을 재생한다. 승인된 사람 행동마다 commit; 완료 결과/HP 또는 stage 정산을
같은 DB transaction에 기록한다. 객체는 process cache이고 DB가 복구 기준이다.
대사 정책/RNG는 별도이며 과거 이벤트는 복구 후 버린다. 향후 이미지 RNG를 CPU RNG에
공유하거나 replay에 이미지 생성/랜덤 콘텐츠 선택을 끼워 넣으면 안 된다.

DB는 users, cpu_characters, user_cpu_progress, cpu_dialogues, cpu_result_assets,
game_settings, game_sessions다. 기존 대사는 **CPU별 event 문장**이며 공유 상황 대사와 다르다.
CG는 CPU·stage 1/2/3별 단일 metadata 슬롯; 파일은 `MEDIA_ROOT` 아래 별도 저장한다.
다중 이미지 조합 캐시나 캐릭터 외모/복장 프롬프트 구조는 없다.

## 채택한 목표 구조 — 제품 미구현

W02 검증 후 2026-10-14 사용자 승인으로 **Electron + 기존 React + 번들 Python/FastAPI/RiichiEnv
+ SQLite**를 채택했다. ZIP 실행·LocalAppData 저장·단일 로컬 프로필·게임 내부 관리 UI다.
아래 대안 비교는 선택 근거이며 지금 추가 대안 구현을 지시하지 않는다.

| 후보 | 재사용/유지보수 | 실행·배포 고려 | 판단 |
|---|---|---|---|
| Electron | React/TS와 브라우저 회귀 자산 활용, Python을 별도 자식 프로세스로 유지 | Chromium/Node 번들 크기·메모리와 런타임 업데이트 부담 | 우선 검증 권고 |
| Tauri + WebView2 | React/Python sidecar 유지 가능, Rust host·권한·빌드 추가 | WebView2 없는 PC의 오프라인 설치/고정 런타임 포함 확인 필요 | 비교 대안 |
| .NET + WebView2 | React/Python 유지, Windows host/수명 코드를 추가 작성 | .NET 및 WebView2 동봉/사전 설치 조건 확인 필요 | Windows 전용 대안 |
| 브라우저+로컬 런처 | UI/API 변경 최소 | 외부 브라우저 수명·프로그램 일체감·독립 실행 관리 부담 | 조사/개발 기준용 |

위 구현 범위 판단은 현재 저장소의 언어/구조에 근거한 권고이며 성능 실측이 아니다.
Python 엔진 재작성이나 TypeScript 엔진 이식은 현재 필요 근거가 없다.
Electron utility process는 Node용이며 Python EXE 자체를 실행하는 기술로 오해하지 않는다.
Python EXE/번들 런타임 실행·회수는 host의 자식 프로세스 관리로 별도 검증한다.

로컬 엔진에서 React 정적 build와 `/api`를 같은 loopback origin으로 제공하는 방안을
우선 검증하면 상대 REST/WS를 가장 많이 재사용할 수 있다. 엔진 자동 기동, 준비 확인,
단일 소유 프로세스, 포트 충돌, 종료·미완료 저장 보존을 검증한다. API를 외부 인터페이스에
노출하지 않고 로컬 제어 권한/세션을 결정한다. 웹 회원 체계를 임의로 제거하거나
하드코딩된 관리자/JWT로 대체하지 않는다. 로컬 인증/저장 구현 계약은 아래 W03 절을 따른다.

## W02 격리 실행 후보와 W03 경계

`spikes/w02`와 `.github/workflows/w02-spike.yml`만 실행 시험 코드다. 제품 entry point·
pyproject·React/CPU/정산/migration은 수정하지 않는다. 실측과 차단은 CURRENT_STATE에 둔다.

| 후보 | 재사용 범위 | 오프라인 실행/배포 부담 | W03 판단 조건 |
|---|---|---|---|
| Electron + PyInstaller onedir | 기존 React production build와 FastAPI API/WS, ORM/seed/replay·native RiichiEnv | Chromium/Node/Python·native DLL 동봉, 큰 폴더와 런타임 보안 업데이트; installer/signing은 미구현 | 우선 후보 유지, Windows 실행 증거와 실제 용량 확인 후 사용자 채택 |
| Python embeddable + Electron | 동일 게임 자산, Python 소스 및 wheel vendoring | `python312._pth`의 import 경로·package/DLL·UCRT 포함을 직접 관리; pip 기본 미포함/일반 pip 관리 미지원 | 이번 executable 후보보다 단순한지는 미실측. 3.12 보안 patch binary 공급 경로 비교 필요 |
| Tauri + WebView2 | 동일 React 및 Python sidecar 가능 | Rust host/권한/sidecar 수명 추가. 미설치 PC 오프라인은 Evergreen standalone installer 또는 Fixed Runtime 필요 | shell 미구현·크기/속도 미실측. 시스템 WebView2만 가정하면 R01 충족 보장 불가 |
| .NET + WebView2 | 동일 React/Python 가능 | .NET self-contained 또는 runtime 설치, WebView2 loader·관리 assembly·offline runtime 조건 추가 | C#/수명 코드를 새로 작성하는 비용과 supported OS 검증 필요 |

spike는 socket을 먼저 bind(127.0.0.1, port 0)하고 기존 Alembic/bootstrap 뒤 정적 build를 `/`에
mount한다. host는 ready 파일의 identity/PID와 실제 identity/health 응답을 모두 대조한다.
상대 REST와 `location.host` 기반 WS를 유지하며 renderer Node 비활성/contextIsolation/sandbox,
외부 요청·새 창·navigation 제한을 시험한다. 이 제한은 OS 인터넷 차단 증거가 아니다.
stdin EOF로 owned Python child 종료를 요청하고, timeout 때 해당 child만 종료한다.
현재 spike는 instance마다 새로운 marker-owned 임시 DB를 만들고 smoke 안에서만 같은 DB로
재기동한다. 이 경로·인증 유지·test seed/stage 주입은 제품 저장/프로필 정책의 채택이 아니다.

**W03 후 구현 파일 경계:** W04는 `db/session.py`, 저장/복구 services, migration/bootstrap와
확정 경로 계약을 담당한다. W05는 새 host/엔진 launcher·static serving·startup/shutdown과
transport 연결을 담당한다. `api/game.py`·CPU agents·legacy fixture·frontend table의 규칙/대국
로직은 우선 재사용한다. spike 코드를 그대로 제품 entry point로 승격하지 않는다.
보안/인증·중복 instance·writer/FK·강제 종료 복구와 지원 OS는 아직 결정/검증이 필요하다.
D01~D03/관리 UI는 이후 W03에서 사용자 승인됐다. D04 주요 정책은 이후 2026-10-15 사용자 결정으로 갱신됐다. 아래 W06 경계를 따른다.

공식 근거(2026-10-14 접속·내용 확인; 후보 설명이며 이 게임 실측과 별개):
- [Python 3.12.10 release](https://www.python.org/downloads/release/python-31210/):
  Windows x64 installer/embeddable 제공. 이후 3.12는 security-only다. W01 Linux 3.12.14와
  동일 patch 공급을 Windows Actions에서 가정하지 않는다.
- [Python embeddable 설명](https://docs.python.org/3.12/using/windows.html#the-embeddable-package):
  pip 미포함, vendoring 및 Microsoft C Runtime 제공 책임.
- [PyInstaller usage](https://pyinstaller.org/en/stable/usage.html): onedir/data/hidden imports 수집.
- [Electron security](https://www.electronjs.org/docs/latest/tutorial/security): renderer 격리·Node 비활성 근거.
- [WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution):
  Evergreen offline standalone 또는 Fixed Version 동봉. Fixed Version은 자동 업데이트하지 않고
  공식 문서상 250 MB 초과이며 UNC/network 경로 제약·Windows 10 v120+ ACL 조건이 있다.
  이를 이 게임의 bundle 크기/호환성 실측으로 기록하지 않는다.

## W03 구현 계약 — W04/W05 인계

이 절은 승인된 여섯 정책을 구현할 기술 경계다. W04의 실제 구현·검증 상태는
`CURRENT_STATE.md`를 기준으로 한다. 아래 W05는 미착수 계약이다.

### W04 로컬 DB·프로필·권한

- LocalAppData 루트 아래 `game.db`, `media/`, `config/`를 분리한다. DB 안의 미디어 key는
  기존 상대 key 정책을 재사용한다. 실행/빌드 폴더·cwd·웹 `.env`에서 자료를 자동 수집하지 않는다.
  개발 검사는 명시적으로 전달한 임시 data root만 사용한다. 기본 사용자 폴더를 검사에 쓰지 않는다.
- 로컬 전용 초기화가 Alembic head→기존 CPU/대사/CG 슬롯 seed→로컬 플레이 프로필 생성
  순서로 실행된다. 반복 실행은 기존 이름/HP/stage/설정/이미지/active session을 보존한다.
  초기 이름은 고정 개인정보 대신 `플레이어`를 사용하며 기존 이름 편집 API로 변경 가능하다.
- 기존 users/progress/session 관계를 우선 재사용한다. 플레이 가능한 member 프로필은 1개다.
  기존 관리자 API 재사용에 필요한 내부 관리 principal은 별도 플레이 프로필로 표시하지 않는다.
  사용자 입력 비밀번호/웹 로그인은 필요하지 않고 로컬 실행에서 회원가입·회원관리 기능은 노출하지 않는다.
- 로컬 전용 app/runtime 경계에서 기존 member 게임·profile API와 관리 API를 재사용한다.
  loopback이라는 이유만으로 무인증 admin을 열거나 웹 get_current_user/role 검사를 전역 해제하지 않는다.
  현재 엔진 실행마다 임의 local capability를 메모리에서 발급해 소유 host에 private channel로
  전달한다. REST와 WS 모두 현재 capability와 해당 내부 principal을 확인한다. URL·명령줄·
  사용자 DB/일반 로그에 secret을 넣지 않는다. 이전 실행의 capability는 새 실행에서 거절한다.
  같은 실행의 장시간 대국에 웹 JWT의 60분 만료를 그대로 적용하지 않는다. 웹 JWT 규칙은 유지한다.
  실제 host 채널/preload·화면 진입은 W05, local runtime 발급/확인과 검사는 W04다.
- DB 쓰기는 하나의 소유 engine process만 한다. 동일 data root에 두 엔진이 쓰기 시작하지
  못하도록 local runtime이 프로세스 간 소유 잠금을 먼저 확보하고 종료 시 해제한다.
  잠금 실패 시 DB 초기화/정산은 시작하지 않는다. host 중복 창 처리는 W05다.
- SQLite 연결마다 FK를 활성화하고 partial unique active-user index를 검증한다.
  쓰기 transaction은 BEGIN IMMEDIATE로 시작해 요청별 직렬화한다. lock 대기와 commit 실패 시
  DB rollback/cache eviction을 유지하고 실패를 성공 응답으로 바꾸지 않는다.
  엔진 전역 lock을 event-loop thread에서 다른 coroutine을 막는 방식으로 추가하지 않는다.
- 기존 사람 행동 commit과 최종 정산 commit은 별개다. 최종 행동 저장 뒤 미정산 재시작은
  replay 후 정산하고 결과/HP 또는 stage를 같은 정산 transaction으로 한 번만 반영한다.
  policy 1/2·seed/좌석/성향·legal action index 순서와 fixture는 그대로 보존한다.
- 기본 SQLite journal/durability를 약화시키지 않는다. WAL·새 백업/복원·export·수동 슬롯은
  이번 최소 구현에 추가하지 않는다. 전원 차단 보장은 실측 없이 주장하지 않는다.

W04 코드는 `backend/app/local_runtime.py`에서 로컬 data root·소유 잠금·SQLite/Alembic/seed·
로컬 profile/capability 경계를 구성한다. local REST 인증은 요청의 저장 Session에서 member/admin을
조회해 이름 수정과 같은 transaction에 연결한다. capability는 ASCII 형식을 확인한 뒤 상수 시간 비교로 malformed/비ASCII/고립 surrogate
입력을 정상 거절한다. `backend/app/db/session.py`의 SQLite FK/busy-timeout/쓰기 예약 처리는 local opt-in 경계에만
설치한다. 기본 engine은 W04 이전 main의 동작을 유지하면서
local session의 쓰기 의도만 명시적으로 `BEGIN IMMEDIATE`로 시작한다. local 읽기는 writer 예약을
얻지 않으며 HTTP method와 WebSocket 행동/정산 transaction이 쓰기 의도를 지정한다.
`backend/app/api/game.py`에는 local WS capability와 행동/정산 write boundary가 있다.
웹 JWT 인증은 유지한다. W04는 UI, Electron host channel/preload, 실행창, 제품 번들 entry point를
포함하지 않는다. 보완 구현·검증의 현재 SHA와 Windows hosted evidence는 `CURRENT_STATE.md`를 따른다.

### W05 실행창·번들·자동 진입

Electron은 한 data root의 단일 소유 host로 동작하고 번들 engine을 자동 기동한다.
같은 loopback origin에서 정적 React와 기존 API/WS를 제공한다. 준비 identity/health를
확인한 뒤 local capability를 제한된 host 채널로 전달해 로그인 화면 없이 profile/active
session으로 진입한다. renderer Node 비활성/contextIsolation/sandbox를 유지한다.
engine/DB 구현은 W04 결과를 사용하며 spike의 임시 DB·시험 seed/stage·시험 helper를
제품 진입점으로 복사하지 않는다. 이름 편집·일반 대국 화면은 기존 자산을 활용한다.
정상 종료는 `desktop/quit.cjs`의 단일 quit coordinator를 거친다. 창 닫기(X/Alt+F4),
`app.quit()`, 마지막 창 종료 이벤트는 같은 공유 Promise를 사용한다. host는 우선 창 입력을
막고 engine의 graceful shutdown을 요청한다. engine은 진행 중인 요청/저장 처리를 마치고 닫히며,
timeout 시 host는 자신이 소유한 child만 강제 회수한다. child close가 확인된 뒤 창을 파괴하고
최종 Electron 종료를 허용한다. 회수 실패 때는 종료를 허용하지 않고 다시 시도할 수 있다.
Windows packaged 일반 모드의 programmatic close/반복 quit·timeout·PID 종료 순서와 같은 data root
재실행을 검증했다. 기존 active 대국 저장 복구도 renderer smoke에서 engine 재시작 후 확인했다.
다른 프로그램·ComfyUI를 종료하지 않는다. host crash/전원 차단은 별도 미검증이다.
배포용 Python binary/지원 OS의 남은 조건은 번들 검증 전에 확인하고 필요한 선택 변경은 사용자에게 제시한다.
캐릭터/공유 목록/생성 설정 관리 화면의 실제 기능은 W08~W11이며 W05에 앞당겨 구현하지 않는다.

## 저장 전환에서 해결할 점

- SQLite tests와 실제 프로세스 재시작 test가 있지만 제품 기본은 PostgreSQL이다.
  `DATABASE_URL`은 이미 SQLite 연결을 허용하므로 전체 ORM 재작성은 불필요하다.
- `with_for_update()`와 process-local RLock은 SQLite에서 PostgreSQL 행 잠금과 같은
  보장을 주지 않는다. 단일 writer/동시 요청/중복 기동/transaction 경계를 W04에서 검증한다.
- SQLite 외래키 적용, 활성 대국 unique partial index, migration/기본값, 정산 exactly-once,
  commit 실패 후 복구, 파일 DB durability를 확인한다. 테스트 성공이 전원 차단 안전성을 뜻하지 않는다.
- 재생 호환성에는 엔진 버전·CPU 정책·성향·합법행동 순서가 중요하다. 기존 policy 1 fixture
  및 새 policy 2를 보존한다. RiichiEnv 업그레이드는 이번 전환에 섞지 않는다.
- DB/이미지/생성 설정은 설치 코드와 분리해야 한다. 정확한 경로·portable 모드·백업 및
  웹 데이터 이전은 D02/D03/D08 결정 후 구현한다. 기존 DB/볼륨을 덮어쓰지 않는다.
- `MEDIA_ROOT=/data/media`, Compose startup migration/bootstrap, PostgreSQL 환경변수와
  웹 관리자 인증 흐름을 그대로 Windows 기본값으로 가져오지 않는다.
- `pyproject.toml`은 엔진만 고정하고 나머지는 범위 지정이다. editable 설치의 setuptools
  자동 package 발견이 실패했다. W02에서 번들 빌드 경로와 의존성 재현 기준을 검증한다.

## W06-A 구현 계약 — W06-B/C 인계

설계 기준: main `e48aae94e37f19fc445717f456b18321354b30a2` (2026-10-15).
이 절은 REQUIREMENTS D04/R16~R19를 구현할 기술 명세다. **제품·migration은 아직 미구현**이며
B/C는 이 설계 검토 후 순차 착수한다. 아래 필드/API 이름은 구현 계약이다. D05~D11을 확정하지 않는다.
적용 범위는 Windows local runtime이다. 기존 웹 JWT/관리자 보안과 웹의 legacy 진행 경로는 보존한다.

### 소스 대조와 변경 지점

| 현재 코드의 사실 | B/C에서 바꿀 경계 |
|---|---|
| `game_setup.py`는 active/stage<3만 선택, HP>0 요구, `CpuChoice.defeat_stage`로 agent 선택 | B: local 명단/phase 검증, stage와 `effective_tier` 분리 |
| `game_registry.py`는 `asdict(CpuChoice)`/seed/actions 저장, 완료 JSON 재사용 | B: 진행 규칙 snapshot/세대 검증 추가. 기존 snapshot decoder와 RNG 보존 |
| `game_result.py`는 사람 HP 감소, stage 3 CPU 정산 거절 | B: 새 local 규칙만 별도 정산. 결과/진행/엔딩을 같은 commit |
| `api/game.py`는 WS auth 뒤 cache 객체 유지, send 중 정산, 결과 대사/CG를 매번 조회 | B: 세대 확인/정산 후 응답, 저장된 결과 표시 payload, 오마케 대사 억제 |
| `local_runtime.py`의 recent는 사용자 전체에서 최신 record 조회 | B: 현재 세대만 조회. 초기화 뒤 옛 completed record 재진입 금지 |
| `UserCpuProgress`는 user+cpu PK, stage 0~3; `GameSetting`은 key+JSON | B: stage 재사용, 현재 플레이만 별도 관계. C: 공통 설정 key 사용 |
| `services/admin.py`의 CPU PATCH는 active 포함 자유 수정; CPU 삭제 API는 현재 없음 | B: 명단 참조 active 변경 차단. C/W08에도 같은 보호 규칙 적용 |
| `result_assets.py`는 상대 key/서명 검사/임시 파일/원자 rename/인증 file 응답 | C: 경로 보호 패턴 재사용, 기존 CG 업로드의 교체/삭제 의미는 바꾸지 않음 |
| `main.tsx`는 active→recent→상대선택, HP/game_over 결과와 load version으로 CG 표시 | B: 플레이 상태 우선 복구·명단선택·초기화. C: 사운드 설정/엔딩 표시 |

### B: 최소 저장 관계와 migration

공통 캐릭터/대사/CG/설정과 파일은 그대로 둔다. 새 프로필/세이브 슬롯/CPU HP는 만들지 않는다.
`users.current_hp/max_hp` 및 기존 HP 설정은 legacy용으로 유지하되 새 local 진행/응답/UI에서는 사용하지 않는다.

| 저장소 | 필드·제약과 책임 |
|---|---|
| 새 `local_play_states` | `user_id` PK/FK users RESTRICT, `generation` UUID 문자열 UNIQUE NOT NULL, `phase` CHECK `roster_required/progress/ending_pending/omake`, `ending_event_id` nullable UNIQUE UUID, `ending_payload` nullable JSON. member 1명당 현재 행 1개 |
| 새 `local_play_roster` | `(user_id,cpu_character_id)` PK, 양쪽 FK RESTRICT. 현재 확정 명단이며 stage는 복사하지 않고 기존 progress join. 명단 확정은 최소 서로 다른 성인 active CPU 3명(4인 대국의 필수조건), 상한은 등록 수 |
| 기존 `user_cpu_progress` | 현재 플레이 stage의 유일한 원본. 명단 밖의 행도 보존하되 완료 판정/선택에서 제외. 새 캐릭터 추가가 명단을 늘리지 않음 |
| 기존 `game_sessions` 추가 | nullable `play_generation` String(36)/index, nullable `rules_snapshot` JSON, nullable `presentation` JSON. status CHECK에 `cancelled` 추가; active partial unique index 유지 |

state 불변조건은 service에서 검증한다: roster_required는 빈 명단/엔딩 NULL,
progress는 명단 3명 이상/엔딩 NULL, ending_pending·omake는 명단 전원 stage 3와
non-null event/payload다. ack 후 event/payload는 반복 ack 판별을 위해 유지하고 reset에서만 비운다.
새 session의 play_generation은 생성 당시 값이며 reset 때 history 값을 새 값으로 바꾸지 않는다.

`rules_snapshot` 새 local 값은 `{version:2, mode:"progress"|"omake"}`. CPU snapshot에는
`effective_tier:0|1|2`를 추가하고 `defeat_stage`는 시작 당시 영속 stage, `policy_version`은 기존대로
보존한다. version 2에서 effective_tier 누락/범위 오류는 저장 손상으로 거절한다. unknown version도
명시 실패하며 legacy로 추측하지 않는다. 기존 규칙은 `rules_snapshot IS NULL` 또는 명시 version 1로
구별하고, 기존 `CpuChoice`와 동일하게 effective tier=저장된 stage, 누락 policy=1로 복구한다.
progress/omake와 CPU policy 1/2는 서로 다른 버전 축이다. Tier 구현·seed*10+seat·legal action 순서·
RiichiEnv 버전·legacy fixture를 변경하지 않는다. 새 stage 3 CPU를 stage 0/2로 바꿔 저장하지 않는다.

B migration은 기존 0004 다음의 additive revision이며 SQLite batch로 status CHECK만 확장한다.
원래 seed/CPU choices/actions/scores/ranks/settlement JSON을 재작성하지 않는다. 웹 사용자에게
local state를 일괄 생성하지 않는다. local bootstrap이 소유 잠금 확보·migration 뒤 기존 local member에
state가 없을 때만 generation과 `roster_required`를 한 writer transaction으로 만든다. 반복 bootstrap은
기존 phase/명단/stage/설정을 유지한다. 기존 세션은 이 최초 bootstrap 때 해당 local member의
NULL generation 기록을 현재 generation에 연결하되 규칙 snapshot/기록 내용은 그대로 둔다.
이는 호환 연결이며 사용자 선택 없이 명단을 추정하거나 stage/HP를 초기화하는 migration이 아니다.
전환 실패는 rollback/실패 표시로 멈추고 DB 삭제·다시 seed해서 복구하지 않는다.

### B: 기존 저장 호환과 진행 상태

| 상태/예시 | 계약 |
|---|---|
| 최초 설치·명단 없음 | `roster_required`, active 없음. 등록 CPU에서 명단을 명시 확정한 뒤 상대 3명 선택 |
| 업그레이드 시 legacy active | 명단 미확정이어도 그 active 대국부터 원 snapshot으로 재생/완료. 최초 명단 확정은 active 종료 전 409. 완료 시 기존 정산을 한 번만 적용하고 다음 대국부터 새 규칙 |
| 업그레이드 시 legacy completed/HP 0 | 완료 JSON/CG/결과는 원본대로 조회, 재정산 없음. local 결과 화면은 HP/game_over로 새 플레이를 차단하지 않음. 이어서 명단 선택, 보존된 stage로 시작 |
| 명단 확정 시 일부 stage 보유 | 기존 stage를 보존. 참가 명단 외 progress는 완료 인원에 포함하지 않음. 전부 stage 3이면 즉시 ending_pending을 한 번 생성 |
| 미완료 3명 이상 | 그 명단의 stage<3만 선택 가능. 예: [0,1,2,3]이면 앞의 3명만 |
| 미완료 2명/1명 | 명단 내 stage 3도 Tier 0 참가 가능. 상대 3명은 사용자가 선택하며 미완료 전원 강제 참가 같은 규칙을 추가하지 않음 |
| 마지막 미완료 CPU 4위 | stage 2→3·session completed·ending_pending/event/payload를 동일 commit. 사람 4위/완료 CPU 4위는 진행 불변 |
| ending_pending | 새 대국 시작 불가, 결과 확인 후 엔딩. 표시 중 종료/재접속이면 같은 event와 payload 재표시 |
| 엔딩 확인 완료 | 같은 generation/event의 명시 acknowledge commit 후 omake. stage 3 그대로, 모두 effective Tier 2 |
| omake | 기본 마작 event/점수/순위는 유지. 진행/캐릭터 대사/결과 CG/승패 대사/새 엔딩 이벤트는 발생시키지 않음. 일반 마작 조작 SFX/BGM은 사용 가능 |

legacy active 정산은 legacy HP/stage 규칙을 보존하는 **기존 한 대국에만 한정한 호환 경로**다.
새 version 2 대국은 HP를 읽거나 바꾸지 않는다. legacy 완료가 명단 없는 상태에서 전체 완료 엔딩을
추측하지 않는다. legacy 손상(예: active snapshot stage 3, 필요한 progress 누락)은 명시 오류/증거를
남기며 새 agent 선택·자동 초기화로 덮지 않는다. 웹 경로는 계속 legacy로 신규 대국을 만든다.

명단 확정 이후 명단 CPU의 `active=false`와 hard delete는 local 관리 API에서 409
`roster_reference_conflict`로 거절한다. active 상태를 몰래 바꿔 전체 완료 대상에서 빼지 않는다.
명단 밖 CPU는 기존 active 변경 가능. 이름/설명/성향 편집은 등록 자료 수정이며 진행도는 바꾸지 않는다.
이미 시작한 대국은 저장된 이름/성향/난이도를 사용한다. 초기화 후에는 이전 명단 보호가 해제된다.
미래 삭제 API도 남은 progress/history 참조를 고려해야 하므로 B에서 새 삭제 API는 추가하지 않는다.

### B: API/UI와 세대·transaction 경계

아래 `/api/local/`는 local runtime에만 등록하고 기존 capability/member/admin dependency를 사용한다.
웹에 무인증 경로를 열지 않는다. `generation`은 공개 상태 식별자이며 capability의 대체물이 아니다.

| 요청 | 입력 → 응답/거절 |
|---|---|
| GET `/api/local/play` | `{generation,phase,roster:[{cpu_character_id,defeat_stage}],ending_event_id,active_session_id,recent_session_id,legacy_active}`. recent는 현재 세대의 completed만, cancelled 제외 |
| GET `/api/local/play/roster-candidates` | 현재 generation과 등록된 active/adult CPU 목록(ID/이름/설명/현재 stage) 반환. 최초 명단용이므로 stage 3도 포함하며 대국 선택 가능 목록과 구분. 명단 확정은 별도 POST에서 검증 |
| POST `/api/local/play/roster` | `{generation,cpu_character_ids:[...]}` → play 상태. roster_required·active 없음·고유/active/adult/최소3 검사. 확정 뒤 변경/중복 제출은 409 |
| POST `/api/game/sessions` (local 확장) | 기존 cpu_character_ids + `generation` → 기존 session_id/players + generation. 명단·phase·3명·가능 인원 검증 후 rules/agents snapshot 저장 |
| WS authenticate/action (local 확장) | authenticate에 generation, action에 generation + 기존 action_version/index. 모든 human_turn/match_complete/dialogue_event/error 응답은 generation/session_id 포함 |
| POST `/api/local/play/reset` | `{generation,confirm:true}` → 새 generation/roster_required. false/누락 400, 이전 세대 409 `play_generation_stale`. 화면에 현재 대국 종료·진행/명단 초기화·등록 자료 보존 확인 표시 |
| POST `/api/local/play/ending/ack` | `{generation,ending_event_id}` → omake 상태. 동일 event 반복은 성공/동일 상태, 다른 event/세대 409. 시간 경과/GET/음악 ended만으로 ack하지 않음 |

local profile은 HP 없는 전용 응답 또는 optional legacy HP 필드를 사용하고 desktop에서 HP를 노출하지
않는다. 기존 웹 response schema는 유지한다. 새 local `match_complete`는 기존 점수/순위와
`{progression_version:2,mode,cpu_character_id,defeat_stage,stage_changed,cpu_completed}` settlement,
`result_asset`, `result_dialogues:[]`, `ending_event_id`를 보낸다. HP/game_over는 새 local 필수 필드가
아니다. legacy 저장 JSON은 전용 decoder/응답 adapter로 읽어 UI의 새 타입에 맞추며 원본을 변경하지 않는다.

`presentation`은 version 2 정산 때 선택한 결과 CG 참조와 대사 목록(문장 포함)을 JSON으로 저장한다.
일반 stage 상승은 기존 `defeat_stage_N` 대사/CG를 재사용한다. 완료 전 보충 CPU 1위/4위는 기존
`match_first`/`match_last` 대사 pool을 별도 콘텐츠 RNG로 선택해 저장하며 stage/CG unlock은 불변이다.
승자와 패자의 대사가 함께 필요할 수 있으므로 배열로 전달한다. pool 없으면 빈 배열로 표시하고
새 문장 seed는 만들지 않는다. 재접속은 같은 저장 payload이며 새 선택/진행 이벤트를 만들지 않는다.
오마케에서는 pending engine events를 소비하되 `extract_game_events`/대사 선택·CG 표시를 호출하지
않는다. 리치/치/퐁/깡/론/쯔모의 기본 규칙 이벤트 자체는 버리지 않는다.

writer 순서/수명은 다음을 지킨다.

1. local mutable 연산(명단확정/start/action/settlement/reset/ack)은 **첫 조회 전에** W04
   `mark_write_intent`/BEGIN IMMEDIATE. 공통 순서는 DB writer 예약→현재 play/record 재조회→
   registry/registered lock→변경/flush/commit→cache 정리/응답이다. 현재 send 함수의
   registered lock→DB writer 순서는 B에서 이 local 경로에 맞춰 조정해 교착을 피한다.
   await/network/audio/file IO 동안 writer나 registry lock을 잡지 않는다.
2. DB에서 current generation=요청 generation=record generation, status/phase를 매번 검사한다.
   `get_owned` cache hit도 이 검사를 우회하지 못한다. 객체가 있거나 같은 user라는 이유로 옛 대국을
   허용하지 않는다. local mutable HTTP는 endpoint/service의 명시 commit 또는 실제로 response 전
   실행되는 function-scope dependency로 commit을 완료한 뒤에만 성공 응답을 허용한다. 현재
   yield dependency override의 후처리가 response 전에 실행된다고 가정하지 않는다. 인증 조회와
   변경은 같은 Session을 사용하고 기본 웹 dependency 의미는 바꾸지 않는다. start/roster/reset/ack의
   commit 실패 주입으로 실제 HTTP 성공 응답/새 generation·event가 노출되지 않음을 검사한다.
3. 행동 log commit 뒤 정산은 기존처럼 별도 transaction. 마지막 행동 뒤 crash면 snapshot replay 후
   정산한다. session completed 결과/진행 stage/결과 presentation/엔딩 생성은 한 정산 commit이다.
   record completed를 먼저 확인해 중복 정산하지 않는다. commit 실패는 rollback+cache eviction,
   재접속에서 DB 재생한다. commit 전 만든 메모리 ending/settlement를 성공으로 보내지 않는다.
4. reset은 writer 안에서 active record를 `cancelled`로 바꾸고 log/snapshot은 보존한다(정산 안 함).
   기존 completed/history도 지우지 않는다. local member의 progress만 모두 stage 0, roster 비우기,
   generation 교체·phase roster_required·ending 필드 NULL을 같은 commit. 이름/프로필·공통 자료·
   HP legacy 열·settings·media/config 파일은 변경하지 않는다. 다른 member/웹 자료는 건드리지 않는다.
5. reset commit 후 해당 user cache eviction·이전 socket close(4409)를 수행한다. close 실패와 무관하게
   다음 DB 검사에서 옛 세대는 거절된다. 취소 record는 restore/recent/정산 대상에서 제외한다.
   reset 실패 시 옛 세대/대국/진행 유지, 영향 cache만 evict 후 재조회한다.
6. 정산이 writer를 먼저 얻으면 그 commit 뒤 reset이 모두 초기화한다. reset이 먼저면 미정산 최종
   행동 log가 있어도 cancelled/옛 세대로 정산 거절한다. 양쪽 모두 새 플레이에 이전 stage/엔딩을
   반영하지 않는다. 두 reset 중 첫 요청만 새 세대 생성, 두 번째는 stale 409다.
7. UI는 초기화 확인 후 입력 잠금·socket 분리·fetch/CG/audio load 토큰 무효화 후 reset 전송.
   모든 비동기 callback은 요청 당시 generation과 화면 load token/socket identity를 대조한다.
   새 generation 수신 후 play부터 재조회한다. 실패·응답 유실이면 play 재조회로 commit 여부 확인;
   이전 reset을 새 generation으로 자동 재시도하지 않는다. 늦게 도착한 old generation 상태는 폐기한다.

### C: 사운드/엔딩 등록과 파일 계약

공통 자료는 최소 등록/목록/수정/비활성화 UI만 제공한다. 기존 CPU 목록은 B의 명단선택에서
재사용하고 캐릭터 P/N·공유 후보 CRUD는 W08로 남긴다. 오디오 제작/보이스팩/볼륨 프리셋/플레이리스트
편집기/외부 API는 추가하지 않는다. 게임 내부 설정 화면만 사용한다.

| 저장소 | 최소 필드/참조 |
|---|---|
| 새 `local_media_assets` | UUID PK, `kind` CHECK image/audio, `storage_key` UNIQUE 상대 key, `mime_type`, `byte_size`. 파일은 LocalAppData media/w06 아래 immutable key. 사용자 원본 경로/외부 URL 저장·직접 재생 금지 |
| 새 `sound_effect_sets` | UUID PK, `label`, `active`, `clips` JSON (`event_key:media_asset_id`). 키는 현재 전달 가능한 `chi/pon/kan/riichi/ron/tsumo`만. 각 clip audio FK 상당 검증을 service에서 수행 |
| 새 `background_tracks` | UUID PK, `label`, `active`, `media_asset_id` FK RESTRICT (audio) |
| `game_settings[local_sound_selection]` | `{effect_set_id:null|UUID,bgm_ids:[UUID,...]}`. 중복 BGM ID 거절; 빈 목록/효과음 null은 무음. 누락 key 기본은 null/[]이며 seed로 자동 선택하지 않음 |
| `game_settings[local_ending_resources]` | `{cg_asset_id:null|UUID,music_track_id:null|UUID,dialogue_text:null|string}`. 단일 엔딩 슬롯, 전부 optional. 대사는 입력된 평문만, D10 변수 치환 없음 |
| B `local_play_states.ending_payload` | 전체 완료 commit에서 `{version:1,cg_asset_id,music_asset_id,dialogue_text}`를 현재 등록 설정에서 한 번 snapshot. event UUID는 그 세대의 완료 식별자, ack까지 payload 불변 |

C migration은 B revision 다음으로 추가하며 기존 CPU CG 테이블/슬롯은 엔딩용으로 전용하지 않는다.
B는 엔딩 설정이 없어도 null 필드의 version 1 payload를 만들 수 있게 구현한다. C는 그 생성 helper를
실제 자료 resolve로 확장한다. 새 완료 시점에 선택된 ending BGM이 여전히 active일 때만 그 track의
audio asset을 pending payload에 snapshot하며, 비활성 track은 새 ending에서 누락/무음 처리한다.
B가 이미 만든 pending payload에 뒤늦은 등록 설정을 소급 주입하지 않는다.
공통 등록 수정은 다음 엔딩/새 재생에 반영된다. 초기화는 이 표의 공통 행·설정을 모두 보존한다.

로컬 admin/capability 경계의 API는 다음과 같다. 목록 응답은 ID/label/active 및 참조 ID만 담고,
파일의 실제 절대 경로를 노출하지 않는다. 모든 JSON 쓰기는 W04 writer를 따른다. 등록/설정 쓰기는 local admin, 게임의 media/선택 설정/엔딩 읽기는 local member로 제한한다.

- POST `/api/local/media` multipart file+kind → `{id,kind,mime_type,byte_size,url}` (201).
  image는 기존 JPEG/PNG/WebP·5 MiB 검사 재사용. audio는 MP3/WAV/Ogg의 서명/확장자/MIME 일치와
  32 MiB 업로드 상한(기술상 버퍼/보관 제한)을 검사한다. 실제 decode 가능 여부는 renderer에서
  별도 확인하며 MIME 성공만으로 재생 성공이라 기록하지 않는다. 범위 밖 형식은 400/크기 초과 413.
- GET `/api/local/media/{id}/file` → 인증된 FileResponse(no-store, audio Range 지원 여부 검증).
  상대 key resolve/root 이탈 거절은 기존 storage_path와 동일한 보호를 사용한다.
- GET/POST `/api/local/sound-effect-sets`, PATCH `/{id}`: `{label,active,clips}`.
  GET/POST `/api/local/background-tracks`, PATCH `/{id}`: `{label,active,media_asset_id}`.
  참조 asset 존재/종류 검사. PATCH는 metadata/참조 교체이며 옛 asset/file을 삭제하지 않는다.
- GET/PUT `/api/local/sound-selection`: 위 local_sound_selection JSON을 전체 교체/반환.
  PUT은 현재 active 자료만 허용(404 missing/409 inactive), CPU 명단/진행/대국 snapshot은 바꾸지 않음.
- GET/PUT `/api/local/ending-resources`: 위 local_ending_resources JSON. nullable 필드는 명시 해제 가능.
  유효 image/active BGM 참조만 저장. 진행 상태/ending_pending payload는 변경하지 않음.
- GET `/api/local/play/ending?generation=...&event_id=...`: pending이면 저장 payload와 안전한
  media URL/누락 상태를 반환. omake의 같은 event는 `{acknowledged:true}`만, stale는 409.

C는 공통 등록의 hard DELETE나 미사용 파일 청소를 제공하지 않는다. 비활성화된 선택 ID는 설정에
보존하되 현재 재생에서는 unavailable/무음으로 응답·표시하고 사용자가 다시 선택할 수 있게 한다.
엔딩 pending의 immutable asset 참조는 등록 목록의 active 변경과 독립으로 읽을 수 있다.
사용자가 외부에서 파일을 지웠다면 missing으로 표시한다. DB 참조만 믿고 임의 파일을 생성하지 않는다.
업로드는 제한 크기 스트림→소유 temp 파일→서명 검사→unique key rename→metadata commit 순서.
실패 시 해당 요청이 만든 temp/새 파일만 정리한다. crash로 남은 orphan 파일은 자동 청소하지 않는다.
기존 사용자 파일·기존 참조 파일을 overwrite/unlink하지 않는다. startup/migration/reset에 파일 IO는 없다.

### C: 재생·엔딩 화면과 재시작

- 기본 BGM은 선택 bgm_ids 순서로 순환 재생한다(첫 항목부터, RNG 없음). 목록 변경 시 현재 track이
  남아 있으면 유지하고 제거/비활성화면 중지 후 새 목록 첫 곡. 전부 없으면 무음. renderer 재시작은
  첫 곡부터이며 재생 위치 영속화는 하지 않는다. 엔딩 중에는 일반 BGM을 멈추고 엔딩 음악을
  1회 재생, ack 뒤 일반 BGM을 다시 시작한다. 선택 곡이 하나면 같은 Audio의 위치를 초기화해
  반복한다. 목록 순서가 바뀌어도 현재 곡 ID를 유지하며 같은 ID의 media URL이 바뀌면 새 media로
  다시 로드한다. 엔딩 음악은 일반 사용 BGM 목록과 독립 참조다.
- SFX는 기존 기본 마작 event에서만 재생하며 대사 문장의 존재에 의존하지 않는다. B/C는 규칙 event와
  dialogue_event를 구분해 `{generation,session_id,action_version,event_index,event_key}` 식별을
  commit 성공 후 전달한다. 같은 renderer 연결의 중복 ID는 재생 안 함. snapshot replay는 과거 event를 버리는 현재
  계약 유지. 오마케도 이 기본 SFX 가능, 캐릭터 대사/콘텐츠 이벤트는 불가. 패 내려놓기/섞기/점수봉 등
  아직 노출되지 않은 새 SFX hook/캐릭터 voice 시스템은 C 범위가 아니다.
- 오디오와 CG는 같은 origin의 인증된 요청으로 가져온 blob/object URL만 사용한다. 부하/재생 promise
  실패는 표시하고 무음으로 계속한다. 파일/decode 실패는 다시 시도 안내를, autoplay 거절은 사용자
  재생 버튼을 제공한다. 이전 Audio의 load/ended/play rejection callback은 현재 Audio와 화면 토큰을
  확인해 폐기한다. 외부 URL,
  renderer 파일시스템 직접 접근, codec 변환·FFmpeg·추가 runtime은 필요하지 않다.
- UI는 `play`→active 복구→pending 엔딩→현재 세대 recent 결과 또는 명단/상대 선택 순으로 진입한다.
  마지막 대국 직후에는 결과/단계 CG를 먼저 보고 '엔딩 보기'로 진입한다. 엔진 재시작 시 pending
  상태는 엔딩으로 돌아와도 되며 같은 event를 새로 만들지 않는다. 엔딩 화면은 CG·음악·대사와
  '계속하기'를 제공하고 성공 ack 뒤 omake 선택 화면으로 전환한다. B에서도 미등록 엔딩 안내와
  명시 ack 버튼을 연결해 검증 가능한 흐름으로 남긴다.
- 실제 resource가 없으면 각각 미등록 안내/무음/빈 대사로 표시하고 '계속하기'는 항상 사용 가능하다.
  파일 누락/재생 오류/브라우저 종료로 자동 ack하지 않는다. 표시만 한 상태의 crash는 같은 pending
  엔딩을 다시 표시·음악 처음부터 재생할 수 있다. **DB 완료 전환은 exactly-once, 인간이 봄/들음의
  exactly-once는 보장하지 않는다.** ack 응답 유실 후 재접속은 omake여서 다시 엔딩을 재생하지 않는다.
- 화면 이탈/초기화/종료에서 이전 SFX audio 정지·object URL 해제, 늦은 load/play callback은 generation+
  화면 토큰으로 차단한다. `match_complete`는 이미 commit된 최종 SFX를 취소하지 않으며 결과 화면에서
  재생이 끝날 수 있다. 다음 대국/화면 이탈·reset/새 generation은 남은 SFX를 무효화한다. 소리 재생/
  파일 로딩은 action/정산 DB commit을 기다리게 하지 않는다.

### 구현 분리와 검증 예제

B는 저장/진행/초기화·엔딩 event/ack·미등록 화면까지, C는 공통 미디어 등록/선택과 실제 표시/재생까지다.
B/C는 동일 main.tsx/models/API/문서를 수정하므로 병렬 구현하지 않는다. B 검토/병합 후 C를 시작한다.

| 검사 | 필요한 기대값 |
|---|---|
| 명단 [0,1,2,3], [2,3,3], [3,3,3] | 순서대로 미완료 3만 가능 / 완료 Tier0 가능 / pending→ack 후 모두 Tier2 |
| 사람4위 / 보충 CPU4위·1위 / omake | HP 변화 없음 / stage 불변·match_last/first 저장 / stage·CG·대사·엔딩 변화 없음 |
| 마지막 stage 증가 commit 실패·동시 재접속 | stage/result/pending 전부 rollback, 재시작 한 번 정산·한 event |
| 마지막 행동 저장 후 reset과 정산 경쟁 | writer 순서에 따른 결과, reset 뒤 옛 요청/캐시/socket이 새 진행을 변경하지 못함 |
| reset 성공 응답 유실·두 번 클릭·old fetch/media callback | 새 세대 1개, stale 거절, 옛 화면/오디오 재등장 없음 |
| legacy active/completed, policy1/2/누락, HP0 | replay 원본 보존·completed 재정산 없음·명단 명시 선택 후 HP 없는 새 규칙 |
| 명단 CPU 비활성화·새 CPU 등록 | 참조 conflict / 전체 완료 대상 변동 없음 |
| 엔딩 표시 중 종료 / ack commit 후 응답 유실 | 같은 event/payload 재표시 / omake로 복구·추가 엔딩 없음 |
| sound 설정 변경·reset·한글 파일명·업로드 실패 | 재시작 보존/명단 독립·등록/파일 hash 보존·root 이탈 거절·기존 파일 불변 |
| 빈/누락/비활성 asset·autoplay 거절 | 무음/안내·계속 가능, 정산/ack를 자동 변경하지 않음 |

필수 회귀는 기존 backend unittest/대사 pytest/frontend build·browser/live-game·policy1/2/legacy
108행동·파일 DB writer/정산 commit 실패 및 packaged 일반 종료/재시작이다. Windows workflow의
exact head checkout/artifact source SHA/ZIP hash를 대조한다. CI에 맞춰 임시 데이터만 사용하고
사용자 자료는 실행하지 않는다. C의 mock 재생과 실제 제공 리소스의 Windows 출력은 따로 기록한다.
실제 자료가 없으면 '미등록/모의 검증 완료, 실제 CG·오디오 출력 미검증(D11)'로 남긴다.

D05 stage↔Level/event→상황, D06 공유 후보 삭제, D07 모델/LoRA, D08 생성 캐시/파일 삭제,
D09 ComfyUI 수명, D10 공유 대사/변수 이전, D11 실제 목록/권리는 이 계약으로 결정하지 않는다.
W06에 필요한 등록 슬롯/기본 마작 SFX/평문 엔딩만 독립시켰다. 실제 리소스/권리 확보는 C의
실측·W12 배포 조건이며 B 저장 구현을 막지 않는다. 새 제품 정책 결정을 요구하는 차이가 발견되면
그 지점만 보류/보고하고 이 계약을 임의 확대하지 않는다.

### W06-C 구현 상태

2026-10-16 구현은 B migration `20261015_0005` 뒤 `20261016_0006`에서 media UUID·상대 storage key,
효과음 세트, BGM track 테이블을 추가했다. Windows local runtime에 `/api/local/media`,
`/sound-effect-sets`, `/background-tracks`, `/sound-selection`, `/ending-resources`,
`/play/ending`을 등록했다. 파일 원본은 LocalAppData media root 아래 immutable key로 저장하며
교체/비활성화/초기화는 기존 파일을 삭제하지 않는다. 오디오 단일 byte-range 요청도 지원한다.

`local_play_states.ending_payload`는 기존 B version 1 형식을 유지하며 완료 시점의 CG asset UUID,
엔딩 track의 media UUID, 평문을 고정한다. 기본 마작 여섯 event SFX는 대사와 독립해 committed
action snapshot에 generation/session/action/event identity와 함께 전달한다. frontend는 중복 identity,
세대 지연 callback, 재생 객체 URL을 관리하고, 선택 BGM은 설정 배열 순서대로 순환한다. 실제 리소스
미등록·파일 누락은 안내/무음 상태이며 재생이나 파일 로딩은 엔딩 ack를 호출하지 않는다.

## W06-B 구현·보완 상태 (2026-10-15)

W06-A 계약을 local-only service/API 경로로 구현했다. migration `20261015_0005`는
`local_play_states`, `local_play_roster`, session generation/rules/presentation 및 cancelled status를
추가한다. 새 local settlement snapshot은 rules version 2와 mode를 기록하고 CPU별
`effective_tier`를 stage와 분리한다. 정산/진행/presentation/ending pending은 writer transaction에서
함께 저장되며 저장 완료 뒤에만 registry 결과를 공개한다. reset은 이전 active를 cancelled 처리하고
새 generation을 만든다. CPU/설정/파일과 기존 session/action 이력은 보존한다.

PR #68 보완에서 legacy/version2 정산의 취소·세대 검증과 cached settlement 차단, 웹 member/HP
생성 조건, ending_pending 명단 확정, reset/ack 응답 복구, 지연 start/confirm/ack 응답 generation·
request-token guard를 보강했다. 고정 명단, 초기화, stale 응답, 자료 보존 및 정산 commit 실패 회귀는
`backend/tests/test_local_play.py`, `backend/tests/test_game_websocket.py`,
`frontend/src/main.tsx`, `desktop/main.cjs`의 검증 경로에 있다.

정확한 코드 SHA `9bab63ecdfe7775130f98791f44b306e8eaac429`의 Windows Server 2022 W05 run
[38778254234](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38778254234)은
backend, frontend build, packaged renderer·일반 종료 smoke 모두 성공했다. W06 reset 오류 복구 뒤
renderer 재연결, 정상 local 대국 완료, active/completed 재기동 및 종료가 통과했다. artifact
`11994663467`의 source SHA는 checkout에서 생성한 `source-sha.txt`와 run SHA로 대조했고,
artifact archive SHA256은 `dc65ae3918d35d28ce6e1e5bf076ea8ede188ac9b5b56d115dd7030375988e5d`.
보조 Windows storage run [38778254269](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38778254269)도 성공했다. 자세한 pre/post 회귀와 run/artifact 근거는 CURRENT_STATE에 있다.

사용자의 개인 Windows PC, 전원 차단 내구성 및 실제 ending CG/음악 출력은 미검증이다. W06-C
등록/선택/엔딩 참조 구현과 exact-SHA mock/Windows 검증은 CURRENT_STATE의 “W06-C PR #70”에
기록한다. PR #70은 main `1b548ae`에 병합됐다. 위 source/run은 당시 검증 이력이며
최종 source `efd5a03`의 증거와 실제 미검증 범위는 CURRENT_STATE를 따른다.

## W07 중간 요구 반영 — 팩·이미지·화면 설계 순서

2026-10-16 사용자 중간 검토로 기존 초안을 갱신한다. 확정 요구 원본은 REQUIREMENTS의
R20~R29와 “중간 검토”다. 아래는 후속 설계/구현 배분이며 schema/팩 manifest가 확정된 것은 아니다.
W06-C의 UUID 업로드·6개 선언 SFX·BGM 순환 목록은 현재 구현/회귀 자산으로 보존하고, 새 팩 방식과
동일하게 구현됐다고 기록하지 않는다. W06 당시 voice/새 SFX hook 제외는 그 Task 범위였으며,
이번 사용자는 별도 후속 Task에서 캐릭터 음성·패 타격/리치봉 등 기본 소리를 연결하도록 요청했다.

| 계약 축 | 먼저 설계할 관계·책임 | 후속 담당 |
|---|---|---|
| Level/3종 이미지 | CPU+stage/Level+image kind(profile/full_body/CG)와 prompt/selection/artifact 관계. Level은 0~3 고정, label과 editable P/N 분리. 서로 다른 종류/단계의 결과가 같은 cache 참조를 잘못 덮지 않음 | W07→W08→W10/W11 |
| 영문 ID/폴더 | 캐릭터팩은 캐릭터 영문 ID, SFX/BGM은 각 고유 영문 ID, 음성팩은 캐릭터 영문 ID를 최상위 루트로 사용. DB 내부 PK와 배포용 ID를 구분하고 image pack/voice pack은 별도 종류/등록 관계 | W07→W08 |
| 팩 규격 | 버전/metadata·상대 참조·공유 후보 의존성·미디어 슬롯·프롬프트를 한 팩으로 배포 가능하게 정의. 정확한 폴더명/파일명/manifest는 다음 계약에서 확정. 원본 팩과 런타임 생성 파일의 소유·수정/보존 경계 정의 | W07→W08, 실제 자료는 W12 |
| 기본 음향 | SFX/BGM 각각 한 팩 ID 선택. slot별 selected→default→silence. 시작/선택 화면 등 BGM slot과 패 타격/리치봉 등 SFX event 목록을 source와 대조해 확정. W06 old selection/파일을 삭제하지 않고 호환 경계 설계 | W07→W08-S |
| 음성/텍스트 | 캐릭터는 image pack과 독립인 voice pack ID 기본값/현재값. 음성 누락은 무출력. 기본 선언은 간단한 공통 화면 텍스트, 음성은 actor 캐릭터의 선택팩. 캐릭터별 Level 패배 텍스트·음성 event slot은 별도 참조로 확정 | W07→W08/W08-S→W09 |
| 생성 입력 | 외모+적용 상의/하의 속옷+Level 복장 상태+상황+포즈와 이미지 종류별 구도의 책임 정리. 모든 관련 prompt는 추가/수정 가능, 구도·의상 문구를 코드 상수로만 고정하지 않음. 실제 모델/파일은 생성·seed하지 않음 | W07→W08→W10→W11 |
| 화면 | 선택 목록의 정사각 프로필·hover/선택 정보/CG+전신, 좌석 프로필/클릭 상세, 단계 상승 결과 연출·CG→전신·하단 대화·CG 전용/줌/팬. 렌더는 확정 selection을 표시하고 hover/줌 자체로 재추첨/생성하지 않음 | W08 데이터 계약→W11-U |

D04-count 재확인으로 W06의 미완료 `<3` 조건을 유지한다. 진행 코드 변경은 필요 없다.
W09는 공통 기본 선언 표시와 선택 voice pack의 actor/event 매핑을 구분하고, 음성 파일/문장 후보의
존재 여부가 기본 선언 텍스트를 숨기지 않도록 계약을 작성한다. 기존 캐릭터 상황 말풍선의 확률/
cooldown을 기본 선언 텍스트나 해당 음성의 표시 여부로 무조건 재사용하지 않는다. 기존 W06의
선언 SFX를 캐릭터 음성과 중복 재생하지 않는 전환·event identity 검증을 W08-S/W09에 배분한다.
Level 변경 패배 대사와 기타 캐릭터 이벤트의 노출 정책은 기본 선언과 별도로 유지한다.

선행 순서는 배포 ID/팩 규격·단계/이미지·텍스트/음성 event 계약→등록 데이터/팩 인식→음향 선택/재생과
대사 연결→독립 생성/3종 artifact 연결→화면 통합→실제 팩 배포 검증이다. 폴더 추가 인식은 요청됐지만
실시간 watcher, ZIP 자동 설치·공개 업로더·팩 제작 도구·온라인 저장소는 요청되지 않았다.
캐릭터팩의 공유 항목 참조를 배포 시 어떻게 포함/매핑하는지, 음성팩 루트 ID와 연결 대상 캐릭터 ID의
독립성·중복/버전 규칙은 W07에서 먼저 명세하고 폴더 이름이 같다는 이유로 이미지와 음성을 결합하지 않는다.

기존 game.db/UUID media/key·pending ending/event snapshot을 배포 폴더 구조로 즉시 옮기거나
파일을 자동 삭제하지 않는다. 선택 변경/reset 뒤 늦은 decode/play/job callback 차단·no-store 인증 blob·
단일 writer와 replay 호환을 재사용한다. SFX/BGM의 기본 팩이 미제공이면 무음 경로를 먼저 유지한다.
사용자 제공 기본 오디오는 별도 리소스 commit/권리/고지 대조 대상으로 취급하고, 외부 제작 프로그램을
게임에 통합하지 않는다. 실제 CG/모델/사용자 자료는 기존 보존·미검증 정책을 유지한다.

다음 기술 계약은 종류별 프로필/full body/CG 출력 크기·선택 수명·캐시와 재생 event/slot matrix,
폴더/파일명/ID 충돌·default 의미·재인식·설정/이전·빠진 파일 처리를 구현 가능한 수준으로 명세해야 한다.
자료 미제공을 이유로 placeholder를 실제 콘텐츠 검증으로 간주하지 않는다. 결과 UI·pack 재시작 보존·
한글 경로·stage3/omake 억제·4/3/2/1/0 NPC 경계는 각 후속 구현의 회귀 항목이다.

## W07 구체 기술 계약 — 2026-10-16 정책 응답과 분리

기준 main `eaaae74`. PR #72~#74 병합, 열린 #35는 Docker 문서로 이번 범위와 무관하다.
이 절은 최신 기술 명세이며 아래 최초 초안과 충돌하면 이 절을 따른다. **W07 부분 설계**이며,
등록 기반의 실제 구현은 아래 W08-A 절과 CURRENT_STATE를 따른다.
정책 독립 필드는 구현용 계약으로 정리하되 `조건부`는 REQUIREMENTS 응답 뒤에만 채택한다.
문서 PR 병합이나 예시 JSON은 미응답 정책 승인·후속 구현 착수 승인이 아니다.

### 팩 identity·manifest v1·파일 소유

- 배포 ID는 `[a-z][a-z0-9]*(?:-[a-z0-9]+)*`, 최대 80자, 소문자 ASCII다. 표시명은 Unicode다.
  DB CPU 정수 PK와 배포 ID는 별개이며 `character_id`는 기존 CPU slug와 명시 대응한다.
  slug를 새 규격에 맞춘다는 이유로 기존 PK/slug/명단을 변경하지 않는다. 대응 불가 구 자료는 legacy로 보존한다.
- 사용자 데이터 루트 아래 `packs/characters/<character_id>/manifest.json`,
  `packs/sfx/<pack_id>/manifest.json`, `packs/bgm/<pack_id>/manifest.json`,
  `packs/voices/<character_id>/<pack_id>/manifest.json`을 검색한다. 음성 배포물 최상위도
  `<character_id>`이며 내부 `<pack_id>`로 같은 캐릭터의 여러 음성팩을 구별한다.
  이미지팩 ID는 character_id, 음성 identity는 `(voice, character_id, pack_id)`다.
  SFX/BGM은 `(kind, pack_id)`. 같은 영문 문자열이 다른 종류에 있어도 충돌하지 않는다.
- 공통 필수 manifest 필드: `schema_version:1`, `kind:character|sfx|bgm|voice`, `id`,
  `version`(팩 작성자 버전 문자열), `label`. voice는 `character_id` 필수다.
  `schema_version`은 parser 호환, `version`은 작성자 표시, `manifest_digest`는 정규화한 JSON 내용 식별, `content_digest`는 manifest와 참조 파일 bytes를 합친 revision 식별로 구분한다.
  unknown schema_version은 비지원 상태로 등록하지 않으며 기존 유효 revision을 덮지 않는다.
- DB `content_packs`의 UUID PK, kind/namespace/id unique, current_revision FK;
  `content_pack_revisions`의 UUID, pack FK, manifest_digest/content_digest, manifest JSON, revision 정수와
  파일별 digest/immutable media UUID 대응을 저장한다. 동일 content_digest 재인식만 no-op다. manifest JSON이 같아도 참조 파일 bytes가 바뀌면 새 revision 후보로 인식한다.
  원본 폴더는 읽기만 하며 인식 시 참조 파일을 런타임 immutable UUID 미디어로 복사한다.
  과거 snapshot은 revision/media UUID를 고정하므로 원본 폴더 교체가 과거 표시를 바꾸지 않는다.
- 경로는 팩 루트 기준 `/` 상대 경로만 허용한다. 절대 경로·drive/UNC·`..`·URL·symlink/junction
  밖 참조를 거절하고 resolve 후 루트 내부 여부를 확인한다. renderer에 로컬 경로/ComfyUI URL을 넘기지 않는다.
  업로드와 팩 파일은 기존 JPEG/PNG/WebP 5 MiB, MP3/WAV/Ogg 32 MiB 한도를 사용한다.
  생성 결과 한도는 아래 기술 검증 뒤 별도 확정한다. 파일명은 Unicode/공백 가능하다.
- 시작 시 로컬 엔진이 한 번 scan하고 설정의 팩 목록 진입 시 scan한다. 상시 watcher는 만들지 않는다.
  `POST /api/local/packs/rescan`은 같은 scan을 명시 호출한다. GET은 DB 목록만 읽는다.
  중복 identity의 서로 다른 manifest가 한 scan에 있으면 둘 다 conflict, 기존 정상 등록은 유지한다.
  같은 위치의 새 content_digest는 새 revision으로 등록하되 기존 파일을 삭제하지 않는다. 적용/로컬 편집 병합은 확정된 Q-PACK A를 따른다.
  불완전 복사/오류 팩은 진단 목록에 남기고 대국 기동을 막지 않는다. 사라진 폴더도 기존 복사본/등록을 삭제하지 않는다.
- scan은 파일 읽기·검증·복사를 writer 밖에서 수행하고 pack 단위 metadata를 한 transaction에 commit한다.
  실패 시 기존 current revision과 설정은 불변. 이번 시도 소유 임시 파일만 정리하며 등록된 파일은 삭제하지 않는다.
  content_digest는 canonical manifest와 경로 순으로 정렬한 참조 파일의 상대 경로·SHA256 목록으로 계산한다.
  같은 scan 재시도는 pack별 unique content_digest로 중복 등록되지 않는다. 진행 초기화는 팩·revision·media·설정을 보존한다.

| 종류 | v1 전용 필드/참조 | 의미 |
|---|---|---|
| character | `character_id`, `metadata`, `prompts`, `levels`, `shared_dependencies`, `default_voice_pack`(nullable `{character_id,id}`) | name/adult=true/기존 설명·style. voice 기본 참조는 배포용 복합 identity, 미설치 가능 |
| sfx / bgm | `slots:{slot_key:relative_path}` | 누락 슬롯 허용. default 팩 identity는 각 종류의 `default`, 없으면 무음. 임의 첫 팩을 기본으로 삼지 않음 |
| voice | `character_id`, `slots:{slot_key:relative_path}` | 이미지/CG 의존성 없음. character_id는 음성 배포 namespace이며 연결 대상 CPU를 제한하는 FK가 아님. 명시 선택은 독립 팩 identity로 수행 |

character `levels`는 정확히 0/1/2/3 네 키다. 각 값은
`images:{profile:null|path,full_body:null|path,cg:null|path}`,
`framing:{profile:{positive,negative},full_body:{positive,negative},cg:{positive,negative}}`다.
이미지 12개 슬롯은 모두 존재하되 아직 생성하지 않은 파일 참조는 null이다. kind/Level 대체 참조는 금지한다.
`prompts`는 `appearance:{positive,negative}`, `upper_underwear:{positive,negative}`,
`lower_underwear:{positive,negative}`를 가진다. 각 쌍은 독립 편집하며 `base_clothing` 제안은 대체한다.
겉옷은 공유 복장 상태 P/N이 담당한다. 미구현 schema 제안 변경이며 기존 사용자 문구를
속옷으로 자동 분류/이전하지 않는다.
속옷 P/N은 적용 부분만 포함하고 미적용 부분은 P/N 모두 제외한다. Level 3은 둘 다 제외한다.
Q-UNDER는 확정됐다. Level 0 정상 복장, Level 1 상의 겉옷만 벗어 브래지어가 보이고
하의 겉옷은 유지, Level 2 상·하의 겉옷 없이 브래지어/하의 속옷 세트, Level 3 전체 탈의다.
Level 2는 누적 탈의이며 Level 1에서 브래지어를 제거하지 않는다. 공유 복장 상태와
적용 속옷 P/N은 이 상태와 일치시킨다. 구체 의상/프롬프트 문구는 임의 생성/seed하지 않는다.
각 이미지 구도 P/N도 편집 가능한 데이터이며 얼굴 정사각/전신/CG의 출력 크기는 생성 설정과 분리 검증한다.
`shared_dependencies`는 `{namespace,id,revision_digest}` 목록으로 원본 공유 ID를 참조한다.
부족한 의존성은 unresolved로 표시한다. 출력 시 최신 기본값 계약에 따라 지정된 유효 기본만 확인하며 임의 다른 후보로 대체하지 않는다.
공유 항목 자체를 팩에 포함하는 배포 범위·후보 표현은 D06 응답 전 확정하지 않는다.
팩 자체와 의존 해소 상태는 분리해서 목록에 표시한다.

### W08-A 등록 구현 계약 — 적용과 분리

이번 사용자 승인 범위는 4종 registry만이다. `schemas/local_content.py`는 v1의 필수 구조와
엄격한 ID/종류/상대 경로를 검증한다. manifest는 UTF-8 JSON 최대 1 MiB이며 중복 key·NaN/Infinity를 거절한다. character의 `id=character_id=폴더명`, sfx/bgm의
`id=폴더명`, voice의 `character_id=상위 폴더명`·`id=하위 폴더명`이 필수다.
팩/캐릭터/음성 namespace ID는 Windows 폴더명으로도 유효해야 하므로
`con/prn/aux/nul/com1..9/lpt1..9` 예약 장치명을 파일 경로와 동일하게 거절한다.
`console`·`aux-pack`·`com10` 등 일반 이름까지 제외하지 않는다.
metadata는 `name`(비어 있지 않은 문자열)·`adult:true`만 필수로 검증하며 description/style은
문자열로 보존한다. 미결정 Q-META의 추가 metadata는 JSON 그대로 보관하고 능력치/단위를 추측하지 않는다.
slot은 v1 표의 sfx 3개, bgm 4개, voice 선언 6개·defeat_stage_1/2/3·match_first/last만 허용한다.
승리 신규 slot은 D-WIN 결정 전 추가하지 않는다. null이 아닌 참조 파일은 모두 존재/형식/한도를 검증한다.

migration 0007은 content_packs(kind/namespace/pack_id unique), content_pack_revisions
(pack/revision 및 pack/content_digest unique), content_pack_files(revision/relative_path PK,
media FK/digest), content_pack_scan_entries(source 상대 식별자/identity/status/issues)를 추가한다.
`current_revision_id`는 **적용된** revision용 nullable FK로 예약하며 W08-A는 항상 null로 둔다.
GET의 `registered_revision`은 마지막 성공 scan이 인식한 revision(`registered_revision_id` FK)이며
`applied_revision_id`와 별개다. A→B→A 복원 시 A 포인터만 변경하고 revision/파일은 추가하지 않는다.
과거 content_digest 재인식은 unchanged이며 새 revision/적용을 만들지 않는다. 원본 manifest JSON과
canonical manifest SHA256, 정렬된 `[상대경로,SHA256]` 목록을 함께 canonical JSON으로 해시한
content_digest를 저장한다(UTF-8, ensure_ascii=false, sort_keys=true, separators=(',',':')).

시작 scan과 POST rescan은 동일 service의 process lock으로 직렬화한다. 인증 조회 transaction은
해제하고 source 검증/복사는 writer 밖에서 수행한다. 참조 파일과 manifest를 다시 읽어 digest/파일
identity·size·mtime이 바뀌면 incomplete_copy로 보류한다. 정상 파일 전체의 UUID 복사가 끝난 뒤
pack별 BEGIN IMMEDIATE/원자 commit한다. DB 실패 시 이번 시도 소유 복사본만 지운다.
상시 watcher·완료 marker는 없으므로 두 읽기 사이 안정된 파일을 대상으로 하며 제작자가 유효한
부분 팩으로 manifest까지 완성한 시점을 추측하지 않는다. 파일을 다 넣고 manifest를 마지막에 놓는다.
symlink/junction/reparse point는 source 경로 각 구성요소에서 거절하며 Windows drive/UNC/ADS,
예약 장치명·후행 공백/점·상위 이동·URL도 거절한다. 목록에는 절대 경로/예외 원문을 노출하지 않는다.

GET `/api/local/packs?kind=character|sfx|bgm|voice`는 DB만 읽고
`{schema_version:1,packs:[identity,registered_revision,applied_revision_id,status,issues,revisions],
scan_entries:[source,identity,status,issues]}`를 반환한다. POST `/api/local/packs/rescan`은
accepted/unchanged/conflicts/issues와 같은 목록 snapshot을 반환한다. 둘 다 local capability가 필요하다.
목록 진입 시 rescan 호출은 후속 설정 UI가 담당하며 이번에는 UI를 추가하지 않는다.
상태는 normal/unresolved/conflict. 잘못된/비지원 manifest·파일 누락은 scan_entries의 unresolved,
충돌은 conflict다. 기존 정상 등록/revision은 진단 실패와 독립적으로 남는다. source_missing도
원본 등록/복사본을 제거하지 않는다. 중복 claim은 모든 후보를 conflict로 보류한다.
shared_dependencies는 현재 공유 registry가 없어 비어 있지 않으면 unresolved이며 등록 snapshot은 보관한다.
미설치 default_voice_pack도 unresolved 진단만 남긴다. 캐릭터 CPU/voice 연결·기본 적용은 하지 않는다.
팩 디렉터리가 없어도 시작 가능하고 새 콘텐츠 seed는 없다. 진행 초기화는 registry를 변경하지 않는다.

### 최신 기본값 해석·삭제 계약 — 2026-10-16 사용자 확정

REQUIREMENTS의 D-DEFAULT/D06-b/삭제 정책을 적용한다. 목록 표시 순서와 기본값 식별은 분리한다.
배포 manifest의 stable identity를 로컬 pack UUID/공유 UUID로 resolve해 영역별 기본 참조로 보관한다.
SFX/BGM의 기존 `default` identity, 캐릭터의 default_voice_pack 등 명시 기본 참조를 사용하며
파일명순/DB 조회 첫 행을 기본으로 삼지 않는다. 공유 항목의 기본 참조도 kind/Level 및 대사는
situation 등 기존 허용 관계를 만족해야 한다. 기본값 복귀로 타 Level·타 event 제약을 우회하지 않는다.

미설정 또는 연결 대상이 없으면 지정 기본값을 확인한다. 유효 기본값까지 없으면 해당 출력 생략;
규칙·정산·편집 저장은 계속한다. 명시 off/enabled=false는 자동 기본 연결과 구분해 보존한다.
단일 팩 연결은 유지한다. voice는 팩 자체가 없을 때만 기본 팩으로 resolve하고, 유효한 팩의
음성 슬롯만 없으면 그 슬롯은 무음이다. SFX/BGM의 파일 슬롯 fallback은 기존대로다.
source 폴더가 사라져도 immutable 복사본/등록이 유효하면 연결 대상이 없어진 것으로 간주하지 않는다.

삭제 UI는 연결된 대상과 변경될 기본 연결을 먼저 표시한다. 확인 요청은 삭제 대상과 영향받는
참조 revision을 검증하며 영향 목록이 바뀌었으면 다시 확인한다. 확인 뒤 새 선택에서 제외하는
논리 삭제·연결 해제·기본 재연결은 같은 writer transaction에서 commit한다. 삭제될 항목 자신을
기본으로 재연결하지 않는다. 유효 기본이 없으면 null/빈 후보와 생략 상태로 남긴다.
실패 시 모두 rollback하며 과거 selection/presentation과 immutable 파일은 변경/삭제하지 않는다.
Level 이동·상황 소속 변경과 신규 항목 자동 포함은 이번 삭제 계약으로 결정하지 않는다.
실제 기본 자료는 D11 제공 뒤 등록하며 이번 문서로 임의 데이터/음성/이미지를 seed하지 않는다.

### W08-C 기존 캐릭터팩 적용 계약

W08-A/B 다음의 독립 구현이다. `character_content.pack_revision_id`가 CPU별 적용 revision이다.
이 FK에서 팩 identity를 얻으므로 별도 연결 테이블/migration은 필요 없다. registry의
registered_revision_id(마지막 성공 인식)와 구분하며 팩 전역 current_revision_id는 변경하지 않는다.
같은 팩을 여러 기존 CPU에 명시 연결할 수 있으며 각각 독립 적용 revision/편집 기록을 갖는다.

- POST `/api/local/characters/{cpu_id}/pack-application`:
  `{expected_revision, pack_id: registry UUID, registered_revision_id: revision UUID}` 필수.
  최초 연결과 동일 팩 갱신만 허용, 다른 팩 교체/해제는 미제공. 선택 CPU는 UI에서 빈 선택으로 시작한다.
- 로컬 요청 writer 예약은 인증 읽기 전 BEGIN IMMEDIATE를 획득한다. 편집 PATCH와 적용 POST는 같은
  content revision을 검사한다. stale content/등록 revision은 409, CPU/팩 누락 404, 비캐릭터 팩 422,
  충돌/미해결 소스·공유 의존·보관 파일 오류 409. default voice 참조는 적용하지 않으며 누락도 이미지팩
  적용을 막지 않는다(W08-S 경계). 원본 소스 없음만으로 정상 보관된 revision을 무효화하지 않는다.
- 적용 시 기존 명시 override가 없는 기본 3쌍/Level 0..3 × 3종 구도의 P/N만 원본에서 복사한다.
  문자열별 편집 목록은 그대로 유지하며 값 비교로 해제하지 않는다. content revision은 적용마다 증가,
  구도 row revision도 증가한다. 이미 적용한 revision 재요청은 충돌 검사 후 no-op다.
- GET content는 `pack`에 identity/적용·등록 revision/갱신 가능 여부를, 각 Level/kind `media`에
  `{media_id,url,digest}` 또는 null을 추가한다. media는 적용 revision의 immutable 파일 참조이며
  편집/재검색에서 파일을 이동·교체하지 않는다. 원본 P/N/과거 revision은 registry 조회로 확인한다.
- GET `/api/local/characters/{cpu_id}/pack-revisions/{revision_id}`는 연결된 같은 팩의 특정 보관 revision을
  원본 prompts/levels/media와 함께 반환한다. 로컬 편집을 과거 원본에 투영하지 않는다. 현재 content
  응답은 현재 편집값이고 과거 게임 표시 snapshot과 다르다. game session/pending/ending은 전혀 갱신하지 않는다.
- UI의 최초 연결은 CPU와 팩을 명시 선택 후 버튼으로 적용한다. 같은 팩 갱신은 별도 버튼이며 재검색은
  자동 적용하지 않는다. 미저장 초안이 있으면 적용을 잠그고 실패 시 초안을 보존한다. 적용/저장 동안
  입력 잠금, 캐릭터 전환·화면 이탈 후 늦은 응답은 request identity로 무시한다.

### 편집/저장 모델과 API envelope

아래는 새 local 전용 경계이며 웹 admin/인증 경로를 대체하지 않는다.
캐릭터 로컬 편집은 원본 팩 JSON을 수정하지 않는다. 기본 외모/상의 속옷/하의 속옷 P/N은
`character_content`(cpu_id unique, pack_revision_id nullable, revision, prompts JSON,
문자열 필드별 overrides)에 저장한다. W08-B의 Level 0..3·profile/full_body/cg 구도 P/N은
이미지 참조/업로드를 포함하지 않는 `character_level_framing`(cpu_id/level/kind unique,
revision, positive/negative, 문자열 필드별 overrides)에 분리 저장한다. 선택/진행과 콘텐츠 revision은 별개다.
Q-PACK A를 채택한다. P/N은 각 문자열 필드 단위의 로컬 편집 여부를 기록한다. 예를 들어
appearance.positive 편집이 appearance.negative를 자동 override로 만들지 않는다. 빈 문자열도
명시 편집값이면 보호한다. 새 원본과 값이 같다는 이유만으로 편집 기록을 지우지 않는다.
원본/적용 revision과 로컬 편집을 분리해 미편집 필드만 새 원본에서 resolve한다.
조회/재검색은 편집 표시를 만들지 않으며 과거 snapshot은 당시 값/revision 그대로다.
W08-B GET은 저장 전에는 DB 쓰기 없이 빈 값을 반환한다. PATCH는 resource revision을 검사하고
요청에 명시된 문자열만 기록한다. 빈 문자열도 override이며 null/생략은 편집과 구분한다.
기본 쌍과 구도 중 어느 하나라도 수정하면 resource revision이 증가하며 구도 row revision도 증가한다.
팩 목록 탭 진입은 POST rescan을 호출하고 일반 GET은 registry DB 조회만 한다.
W08-B는 기존 CPU의 독립 편집/기록만 구현하고 팩 첫 연결·실제 적용·자동 갱신은 후속으로 분리한다.
`character_voice_links`는 cpu_id unique, default_pack_id nullable, selected_pack_id nullable,
selection_mode `default|selected|off`, revision을 저장한다. Q-PACK A에 따라 연결된 동일 팩 갱신 적용 때 default만 갱신하고 selected/off는 유지한다. W08-B는 이 연결/재생을 구현하지 않는다.
DB default_pack_id/selected_pack_id는 content_packs UUID FK다. 배포 manifest의 `{character_id,id}`를
voice namespace에서 UUID로 resolve하며 같은 내부 pack_id만 비교하지 않는다. 캐릭터 이미지팩과
음성팩의 character_id가 같아야 한다는 제한을 추가하지 않는다. 미설치 선택 참조는 unresolved로 표시하고 캐릭터 지정 기본 팩을 확인한다. 기본 팩도 없으면 무음이다.
선택 팩의 슬롯 누락 시 default로 돌아가지 않는다. `off`는 무음이며 미선택 기본 연결과 다르다.

공유 원본은 stable UUID, kind, level, label, positive/negative, revision, active를 가진다.
대사는 situation FK·text, event binding은 situation FK·event_key unique 관계다.
명시 후보 stable ID 참조를 저장하며 새 공유 항목은 자동 포함하지 않는다(D06-a A).
같은 Level의 허용 후보끼리 조합하고 상황별 복장 상태/포즈 제약 관계는 추가하지 않는다(D06-d A).
미설정/대상 누락은 지정 기본값, 기본값도 없는 빈 후보는 출력 생략한다. 삭제는 확인 후 기본 재연결한다.
이동 동작·event 매핑 편집 방향·변수 검증은 남은 D06-c/D05-c/D10-a 응답에 따라 확정한다.
미응답을 nullable 기본값이나 임시 seed로 우회하여 구현하지 않는다.

응답은 `schema_version:1`, entity `revision`을 포함한다. PATCH/PUT은 `expected_revision` 필수,
불일치 409 `revision_conflict`, 없는 ID 404, 필드/종류/단계/잘못된 참조 422,
미해결 의존/중복 identity 409, 권한은 기존 local capability 401/403을 유지한다.
변경 성공은 commit 뒤만 반환한다. 오류 body는 FastAPI `detail:{code,message,fields?}`;
사용자 경로/비밀값 대신 필드명과 팩 ID를 반환한다. 파일은 기존 인증 blob/Range 읽기를 재사용한다.

| method / local 경로 | 요청·응답 핵심 | 담당/게이트 |
|---|---|---|
| GET `/packs?kind=…` / POST `/packs/rescan` | pack identity/revision/status/issues; scan 결과 accepted/unchanged/conflicts/issues | W08-A 4종 scanner, W08-S 적용/재생은 별도 |
| GET/PATCH `/characters/{cpu_id}/content` | W08-B는 기본/구도 P/N·문자열별 override·expected_revision만 편집 | metadata/default voice·팩 실제 적용은 후속 W08/W08-S |
| GET/PUT `/characters/{cpu_id}/levels/{level}/images/{kind}` | immutable media_id nullable, framing P/N, expected_revision | W08, 자동 생성은 없음 |
| GET/PUT `/characters/{cpu_id}/candidates/{level}` | 네 kind의 명시 stable ID 집합·revision, 미설정의 지정 기본값과 구분 | W08; 신규 자동 포함 없음, 같은 Level 허용 후보 조합 |
| GET/POST `/content/{kind}` / PATCH/DELETE `/content/{kind}/{id}` | 원본 필드·참조 영향·revision; DELETE는 영향 확인 후 논리 제외·기본 재연결을 원자 commit | W08; D05-c/D06/D10-a |
| GET/PUT `/audio-selection` | sfx_pack_id/bgm_pack_id nullable, enabled flags, revision | W08-S; legacy 전환 Q-AUDIO 승인 후 |
| GET/PUT `/characters/{cpu_id}/voice-selection` | selection_mode, selected_pack_id, revision | W08-S; Q-PACK A 확정, 실제 연결/재생은 해당 Task에서 구현 |
| GET `/characters/{cpu_id}/display?context=selection` | 아래 CharacterDisplay | W11-U 읽기, W08 asset 공급 |
| GET `/presentations/{selection_id}` | snapshot·이미지 상태·artifact·재시도 허용 여부 | W11, D08 승인 후 |
| POST `/presentations/{selection_id}/retry` | expected_generation/request_id, 명시 재시도만; 202 job 또는 기존 job | W11; D08-c 승인 후 |
| GET/PUT `/generation-settings` | revision, endpoint/adapter/workflow/model 입력 | W10; D07/D09 응답·node 검증 후 필드 확정 |

### W08-B 독립 편집 계약 — 생성/팩 실제 적용 전

대상은 기존 cpu_characters PK다. 기존 name/slug/adult/style·성향 값은 조회용이며 바꾸지 않는다.
`character_content`에 cpu_id unique, nullable pack_revision_id(이번에는 null), revision,
appearance/upper_underwear/lower_underwear P/N과 해당 문자열별 override 기록을 저장한다.
단계별 3종 구도 P/N은 cpu_id/level/kind unique로 분리하고 P/N 각각의 편집 여부를 저장한다.
이미지 참조/파일 업로드는 이번 편집 모델에 함께 넣지 않는다. 기존 result asset을 옮기지 않는다.

GET `/api/local/characters/{cpu_id}/content`는 저장 행이 없으면 빈 P/N·revision 0을 반환하며
DB를 쓰거나 문구를 seed하지 않는다. 구도도 Level 0..3/profile/full_body/cg별 빈 쌍을 조회할 수 있다.
PATCH content는 세 기본 쌍과 Level/kind별 구도의 **명시된 문자열 필드만** 받는다. 기존
expected_revision/commit 뒤 응답/409 충돌/local admin capability 계약을 유지한다.
PATCH에 명시한 문자열은 override=true로 기록하고 다른 필드 기록은 보존한다. 프론트는
실제로 변경한 필드만 전송해 전체 폼 저장으로 미편집 항목까지 보호하지 않는다.
빈 문자열은 유효한 편집값이며 null/필드 누락과 혼동하지 않는다.

최소 내부 관리 UI는 기존 캐릭터 선택·세 기본 P/N·Level별 이미지 종류 구도 P/N의 편집/저장,
등록된 팩 목록/상태/진단·명시 재검색만 제공한다. 팩 목록 진입 시 rescan 호출을 직렬화하고
일반 목록 GET은 DB 조회만 한다. 캐릭터 전환 후 늦은 응답/저장 결과가 다른 캐릭터 폼을 덮지 않는다.
저장 실패/충돌 시 입력을 보존하고 이미 저장된 값이라고 표시하지 않는다.
저장 응답을 기다리는 동안 P/N 입력은 비활성화해 이후 입력을 응답으로 지우지 않는다.
캐릭터 선택을 바꾸어도 이전 저장은 새 폼에 반영하지 않는다. 팩 scan 진행 ref로 탭 재진입과
명시 재검색의 중복 요청을 차단한다. 전용 content browser 검사는 W05의 기존 Vite 단계에서 실행한다.

재시작/진행 초기화 후 편집 내용과 override 기록을 보존한다. 팩 등록/재검색이 로컬 값을
덮지 않아야 한다. 팩 CPU 생성/연결/적용, 공유 후보/대사/변수, 모델/LoRA, metadata 확장,
이미지 생성·미리보기·파일 편집·승리/음성 hook은 후속 범위다. 실제 프롬프트 작성은 최소화한다.

### 텍스트·음성·기본 음향 event 계약

기본 선언 공통 텍스트는 chi=치, pon=퐁, kan=깡, riichi=리치, ron=론, tsumo=쯔모다.
캐릭터별 문장 후보나 음성 유무와 무관하다. actor 좌석→저장 CPU mapping→선택 voice pack으로 resolve한다.
사람 actor는 연결된 NPC 음성이 없으므로 NPC 음성을 대신 쓰지 않는다.
기존 문장 확률/cooldown은 별도 상황 대사에만 보존한다. 공통 선언·voice를 문장 후보 존재에 묶지 않는다.
오마케는 기본 공통 텍스트/SFX 유지, 상황·승패/CG 이벤트는 기존대로 억제한다.
기본 선언 voice를 추가 캐릭터 이벤트로 취급해 억제할지는 Q-OMAKE-VOICE 응답 전 확정하지 않는다.
기본 선언/음성 분리 확정만으로 오마케 음소거 정책을 추가하지 않는다.

| domain | v1 slot / source | 처리 |
|---|---|---|
| voice | chi/pon/kan/riichi/ron/tsumo | 기존 event mapper의 reach→riichi, 세 깡→kan, hora target/actor→ron/tsumo. actor CPU의 팩만 |
| character result | defeat_stage_1/2/3 | 증가 후 Level의 캐릭터별 텍스트 지정·같은 키 음성. 텍스트와 오디오 참조는 별도 |
| completed support | match_first/match_last | W06 기존 보충 승패 대상만, stage=3 불변. D-WIN으로 일반 승리 범위를 자동 확대하지 않음 |
| voice 승리 | D-WIN 응답 뒤 slot 결정 | ron/tsumo 선언과 승리 대사 중복 여부도 응답 전 hook 금지 |
| SFX 후보 | tile_discard / tile_shuffle / riichi_stick | discard/reach_accepted/국 시작의 정확한 emission·한 국 1회 섞기 source 검증 후 W08-S 연결. hook 부재 시 임의 action 호출로 만들지 않음 |
| BGM | title / selection / game / result | 해당 화면 진입 시 slot resolve, 같은 resolved media면 재시작하지 않음. ending은 W06 전용 음악/pending 계약 유지 |

SFX 후보는 사용자가 언급한 패 타격/섞기/리치봉 범위다. 실제 event source 검증이 없으면
미연결로 보고하고 규칙 코드를 확장하지 않는다. 임의 새 음향 슬롯/샘플을 추가하지 않는다.
각 slot resolve는 enabled일 때 selected→동일 kind default→null이다. 선택 팩 파일이 누락/비활성/
읽기 불가면 default를 확인하고 default도 실패하면 무음. voice는 selected/default 연결에서 정한
**하나의 유효 팩 안에서만** 찾으며 파일 실패도 무음이다. 선택 팩 자체가 없으면 지정 기본 팩으로 resolve한 뒤 슬롯을 확인한다. 실행 중 재생 실패는 대국 진행을 막지 않는다.
팩 전환 시 audio generation을 증가시켜 기존 pending play callback을 격리하고 현 BGM을 재평가한다.
기본 선언 voice와 같은 파일을 공통 SFX로 중복 재생하지 않는다. W06 6개 구 슬롯 이전은 Q-AUDIO 대상이다.

source identity는 `(play_generation, session_id, action_version, source_kind, source_ordinal, actor_seat, event_key)`.
`api/game.py`의 `pending_events()` 한 번 소비 직후 원본 tuple의 enumerate index를 붙이고,
JSON parse/mapper/후보 필터/우선순위 정렬 이후에도 그 index를 유지한다. 잘못된 원소를 건너뛰어도
뒤 index를 당기지 않는다. result는 source_kind=result, ordinal=좌석 0..3, stage 변경 키로 고정한다.
`reach_accepted` 같은 비선언 source를 riichi voice로 재매핑하지 않는다.
동일 배치 내 서로 다른 index를 내용 같다고 합치지 않으며 관측 중복은 실제 mapper 회귀로 확인한다.
정확한 event source가 추가로 필요하면 엔진 변경 없이 수집 가능한지 별도 검토한다.
W06 SFX identity·엔딩 UUID·action index·rules snapshot은 바꾸지 않는다.

### W06 보존과 additive migration

현행 Alembic head `20261016_0006` 다음에서 신규 관계만 추가한다. W08이 다음 revision을 소유하고
W08-S/W09/W10/W11은 앞 PR 병합 뒤 실제 head에서 번호를 정한다. 당시 W07 문서 작업에서는 migration을 실행하지 않았으며, 후속 W08-A에서 0007을 구현했다.
CPU PK/명단/progress, seed/actions/policy1/2, 기존 completed presentation version 2와
ending pending snapshot/ack는 재작성하지 않는다. 새 콘텐츠 DTO version과 progression_version은 별개다.
신규 표시만 content_schema_version=1을 가지며 legacy는 기존 renderer adapter로 계속 읽는다.

- 기존 `local_media_assets`, `sound_effect_sets`, `background_tracks`, `local_sound_selection`과
  ending 설정·UUID 파일은 그대로 둔다. 새 audio-selection은 별도 키다. 없으면 legacy 재생 경로를 유지한다.
  새 API가 구 선택을 빈 값으로 덮거나 한 BGM만 몰래 선택하지 않는다. Q-AUDIO 승인 후 일회 전환한다.
- `cpu_dialogues`의 기본 선언 행은 보존하지만 새 local 공통 텍스트 fallback에는 쓰지 않는다.
  기존 defeat_stage/보충 승패 행의 새 관계 이전 범위는 Q-LEGACY에 따른다. 원본을 shared로 강제 병합하지 않는다.
  승인 시 `legacy_content_map(source_table,source_id,target_id)` unique로 재실행 중복을 막고 한 transaction에 이전한다.
- 기존 CPU seed/대사 seed·CG 슬롯은 유지한다. 새 팩/프롬프트/치수/음성/이미지는 seed하지 않는다.
  기존 자료에 팩 ID를 자동 할당하거나 엔딩 snapshot을 현 팩으로 다시 resolve하지 않는다.
- reset은 새 등록/수정/voice 연결·음향 설정·파일도 보존하며 generation만 이전 표시와 job에서 격리한다.
  재시작/반복 upgrade·bootstrap·reset 검사에서 기존 자료 byte hash와 PK/JSON 값이 같아야 한다.

### 선택·좌석·결과 화면 DTO와 수명

`CharacterDisplay={schema_version:1,cpu_id,character_id,name,level,content_revision,
metadata,mahjong,images:{profile,full_body,cg}}`.
image 항목은 `{kind,level,asset_id:null|UUID,url:null|string,status:ready|missing|failed,
revision}`다. metadata 치수 필드는 Q-META 응답 후만 추가한다.
mahjong은 기존 style/설명·성향 여섯 값 및 표시용 effective_tier를 읽으며 새 능력치를 계산하지 않는다.
선택 화면 Level은 현재 진행, 대국 좌석 Level/Tier는 해당 대국 CPU snapshot,
결과 Level은 committed stage_after다. 보충 stage3/Tier0의 이미지 Level을 0으로 낮추지 않는다.

선택 목록은 프로필을 제공하고 hover/선택은 상단 이름·정보/CG/전신의 **조회만** 유발한다.
최초 생성·재생성 시점은 Q-IMAGE 응답 전 hook을 두지 않는다. 대국 상세 클릭도 asset 조회만 한다.
zoom/pan/CG 전용은 renderer 로컬 transform/visibility이며 DB 정산·추첨·생성을 호출하지 않는다.
이미지 fetch 완료는 `(generation,context,cpu_id,level,kind,asset_id,view_token)` 일치 때만 반영하고
화면 이탈/hover 변경은 이전 object URL을 해제한다. 오류는 이미지 칸 안내이며 진행 버튼은 유지한다.

`StageResultDisplay={schema_version:1,selection_id,generation,session_id,cpu_id,stage_before,
stage_after,stage_changed,character_snapshot,text_snapshot,voice_ref,images}`를 정산 transaction에 고정한다.
stage_changed=true일 때 단계 애니메이션→after CG→after 전신, 하단 after profile/대화 순이다.
완료 보충/오마케는 이 연출을 새로 만들지 않는다. 마지막 완료 결과의 순위/단계 표시 후 기존
ending_pending으로 이어지고, 엔딩 계속하기만 기존 ack를 호출한다. 연출 완료/파일 실패는 ack가 아니다.
연출 재시청·복구는 stage 증가를 반복하지 않으며 자동 voice replay는 하지 않는다.

### 생성 입력·job 수명 — 정책 조건부 계약

공통 `GenerationInput v1`은 cpu_id/character_id, level, image_kind, content revision,
선택 후보 ID/revision, 구도 P/N, 최종 P/N, workflow_digest/adapter_version,
model/encoder/VAE 참조+사용자 revision, 순서 있는 LoRA 참조/강도,
width/height/steps/CFG/sampler/scheduler, 독립 seed를 가진다.
구도와 최신 프롬프트 구성 요소의 정확한 결합 위치는 Q-FRAME/D07-a 응답 후 고정한다.
D07-b 응답 전 캐릭터 override 필드를 구현하지 않는다. 모델 실파일은 복사/배포하지 않는다.

cache는 canonical JSON(SHA256, UTF-8, key 정렬, 배열 순서 유지, 숫자 표현 고정)의
최종 생성 입력으로 식별하고 이미지 kind/Level도 포함한다. label/화면 token은 제외한다.
D08-a A면 seed 이전 입력 digest→최초 독립 seed/artifact 매핑을 unique로 보존,
B면 event identity+독립 seed를 포함한다. 같은 이름의 모델 교체를 자동 감지했다고 주장하지 않고
사용자 model revision을 입력에 포함한다. 실제 지원 node의 fingerprint 유무는 W10 기술 확인 항목이다.

job은 `queued→submitting→running→succeeded|failed|unknown`과 owned request/client/prompt ID를 저장한다.
외부 submit은 commit 뒤 writer/game lock 밖에서 수행한다. prompt ID 수신 전 연결 유실은 unknown이며
자동 중복 submit하지 않는다. 재기동은 저장된 자기 prompt ID만 조회하고, 불명 상태는 명시 재시도
전까지 보류한다. 재시도는 새 request UUID, 같은 selection/입력 snapshot을 사용한다.
D09-a A 채택 시 게임 종료는 polling만 중지, 원격 프로세스/다른 job interrupt 금지다.
초기화/새 대국 뒤 완료한 파일은 보존해도 현재 화면으로 연결하지 않는다.
D08-b A는 현재 selection을 별도 writer transaction에 저장 성공 후 발행하고,
B는 순간 표시를 재기동 복구하지 않는다. 행동 commit 뒤 selection 저장 전 crash는
행동만 복구하고 과거 pending replay로 생성하지 않는다. 결과 snapshot은 정산과 원자 저장한다.

ComfyUI endpoint/object_info·Anima workflow/node·encoder/VAE/LoRA 호환·output fetch 계약은
실제 환경에서 확인하지 않았다. W10은 승인 정책과 별도로 지원 workflow 1개의 구체 input/output,
출력 크기/형식/디코딩·소유 결과 경로 제한을 기술 검증한 뒤 adapter를 고정해야 한다.
미검증 node명을 지어내거나 mock 통과를 실제 출력 성공으로 기록하지 않는다.

### 후속 수용 사례 — 실행 결과 아님

1. stage 0→1/2→3에서 after Level 세 종류만 표시, 보충3/Tier0와 오마케3/Tier2는 이미지3 유지.
2. 한 배치 `[bad,chi,pon]`의 source ordinal 1/2 유지; actor별 voice, 슬롯 누락은 무출력,
   공통 선언은 문장 후보가 없어도 표시. 재접속/replay 중 과거 voice/SFX는 재생하지 않음.
3. SFX 선택 tile_discard 누락/default 존재→default, 양쪽 누락→무음. voice 미설정/선택 팩 자체 없음→캐릭터 기본 팩; 유효 팩의 슬롯만 없음→무음. 명시 off 유지.
   공유 후보 미설정/대상 누락→허용 관계 내 지정 기본값, 기본도 없음→출력만 생략.
   연결 영향 표시→삭제 확인→해제/기본 연결 원자 commit; 영향 변경 재확인·commit 실패 rollback·자기 기본 재연결 금지·과거 파일 보존.
4. 동일 content_digest 재scan no-op, JSON 불변·참조 음성/이미지 bytes 변경은 새 revision 후보.
   같은 내부 pack_id의 다른 voice namespace와 명시 교차 연결도 올바르게 resolve.
   충돌/잘못된 경로/불완전 파일로 기존 revision 불변. 복사 후 metadata 실패,
   수정/재시작/reset에도 기존 W06 UUID/선택/ending snapshot/파일 hash 유지.
5. 빠른 A→B hover, 결과 표시 뒤 팩 교체, reset 후 늦은 job/play/load는 현 화면 불변.
6. 신규 공유 항목 추가 후 기존 명시 후보 집합 불변, 같은 Level 허용 후보 조합·타 Level 거절을 검사한다.
   외모/상의 속옷/하의 속옷 P/N 독립 편집, 미적용 속옷은 P/N 모두 제외·Level 3 양쪽 제외를 확인한다.
   Q-UNDER 확정 상태표대로 1의 브래지어/하의 겉옷, 2의 속옷 세트/겉옷 없음, 3의 속옷 없음 및 stage=Level을 검증한다. D06/D08 각 승인 조합대로 후보 고갈·삭제/참조·입력 수정/재사용·복구를 검사한다.
   결과 GET/연출 재실행·CG 전용 복귀가 stage/정산/추첨/submit 횟수를 증가시키지 않아야 한다.

## W07 콘텐츠·이미지 계약 초안 — 정책 승인 전 구현 금지

분석 기준 main `1b548ae8ca901e97407cd02ccc45973a1539add7`, PR #70 병합 확인(2026-10-16 KST).
R07~R14의 최초 관계·책임을 정리한 **미승인 기술 초안**이다. 2026-10-16 중간 요구(R20~R29)가
아래의 미승인 권고와 충돌하면 위 최신 배분과 REQUIREMENTS가 우선하며, 최초 초안을 그대로 구현하지 않는다. 아래 이름/경로는 제안이며
현재 table/API가 아니다. 사용자 질문/권고/선택의 원본은 [REQUIREMENTS.md](REQUIREMENTS.md)의
“W07 사용자 질문”이다. D05~D10 답변 후 W07 계약 확정 검토를 거쳐야 W08~W11에 착수할 수 있다.

### 현재 소스와 재사용 경계

| 요구/영역 | 현재 코드에서 확인한 사실 | 재사용 및 필요한 차이 |
|---|---|---|
| R07/R14 캐릭터 | `db/models/cpu_character.py`, `services/admin.py`, `api/admin.py`: 성인 CPU ID/성향/설명·활성 상태, P/N 없음 | CPU PK/명단 보호·관리 권한 유지. P/N 편집·공유 관리 UI만 추가 대상으로 분리 |
| R08/R09 공유·후보 | 공유 Level/상황/포즈/후보 관계 없음. 기존 `cpu_dialogues`는 CPU FK+event_key+text+active | 기존 대사 행을 공유 데이터로 간주하지 않음. 공통 원본과 캐릭터 참조 관계를 새로 설계 |
| R12/R13 행동 대사 | `dialogue_service.py`: CPU 좌석만, active 대사 ID 순 최대 100개 중 choice. `reach→riichi`, 치/퐁, 세 깡→kan, hora의 target/actor로 ron/tsumo 구분 | event 해석·노출 정책을 보존하고 그 다음 상황/후보 교집합을 선택. 기존 100개 제한을 공유 후보 정책으로 자동 계승하지 않음 |
| 기존 노출 수치 | ron/tsumo 확률 1·우선 60, riichi .9·50, kan .75·40, pon .45·30, chi .35·20. CPU/event cooldown은 kan 2/2, pon 2/3, chi 2/3, 나머지 0/0. 한 turn 한 발화 | 정책의 우선순위/확률/cooldown/빈 문장일 때 미소비 경계 유지. 이미지 유무가 대사 노출 확률·SFX를 바꾸면 안 됨 |
| 이벤트 원본 | `mahjong/session.py`가 pending observation의 events를 누적·소비. `api/game.py`가 한 pending batch를 대사·SFX에 사용 | 현재 배열 index는 해당 batch 기준이며 엔진 전역 event ID가 아님. 관측 중복 정규화나 규칙 hook 변경을 W07 준비에서 수행하지 않음 |
| R10 표시/복구 | `game_registry.py`는 seed·CPU snapshot·사람 index replay 뒤 `pending_events()`를 비움. 행동 대사 policy는 cache 객체, 영속적인 표시 selection 없음 | 과거 행동의 대사/이미지 생성 재발행 금지. 복구할 현재 표시의 별도 snapshot 여부는 D08-b |
| 결과/완료 CPU | `_settle_local`은 stage 증가 뒤 defeat_stage_N 대사/CG, 완료 보충 CPU match_first/last 대사, version 2 presentation을 정산 transaction에 저장. 완료 GET은 저장 presentation 사용 | stage 3 결과와 보충 CPU는 구분. 새 공유 결과로의 대체는 승인 후. 오마케는 대사/CG/추가 이벤트 금지 유지 |
| R11 생성 | prompt/model/LoRA/ComfyUI/cache 구현 없음 | 기존 엔진을 생성기로 오해하지 않음. 독립 adapter·콘텐츠 RNG·artifact 관계 필요 |
| CG/파일 | `result_assets.py`: CPU/stage 1~3의 mutable 슬롯·해금 검사, 기존 교체/삭제 API. `local_media.py`: W06 immutable UUID 파일·서명/경로 검증 | W06 보존형 저장 패턴은 재사용 가능. 구 CG 슬롯 ID는 교체 때 가리키는 bytes가 달라질 수 있어 immutable 생성 artifact로 직접 전용 금지 |
| UI | `main.tsx`: generation/request token/CG load version/인증 blob, `MahjongTable.tsx`: 말풍선·결과/엔딩 | 늦은 fetch/object URL 차단·평문 표시 패턴 재사용. 렌더는 ID를 표시하며 후보/프롬프트 선택을 하지 않음 |
| 초기화/엔딩 | `local_play.py`, W06-C media/sound: 세대 교체, 등록 자료/파일 보존, pending 엔딩 고정 payload·명시 ack | 콘텐츠 편집을 명단/진행 초기화와 결합하지 않음. 엔딩은 공유 대사/이미지 이벤트로 전환하지 않음 |

### 정책에 독립적인 불변조건과 관계 초안

정책과 무관하게 유지할 경계: 기존 CPU/진행 PK와 seed/action/policy replay, 공유 원본 참조,
렌더별 재추첨 금지, 콘텐츠 선택/생성과 규칙 RNG 분리, 게임 transaction의 외부 생성 대기 금지,
오마케 이벤트 억제, 파일 임의 삭제 금지, 같은 origin/capability·단일 writer 권한이다.
테이블 수·새 version 번호·Level 범위·삭제 방식·후보 포함 의미는 이 절만으로 채택되지 않는다.

| 제안 관계 | 최소 데이터/소유 | 미확정 또는 승인 뒤 명세화할 부분 |
|---|---|---|
| CharacterContent | 기존 CPU FK, 외모/상의 속옷/하의 속옷 P/N, 변경 revision | D07-b override 필드, revision 증가 범위. 규칙 성향 snapshot과 분리 |
| ContentLevel | 안정 ID/표시 label | D05-a의 Level 집합/대응. label을 stage/난이도 판정 키로 사용하지 않음 |
| ClothingState / Situation / Pose | 안정 ID, Level FK, label, P/N, revision | D06-c 삭제/이동. 별도 entity 또는 공통 kind schema는 후속 기술 선택 |
| SituationEventBinding | situation FK와 engine event_key 관계 | D05-c 편집 방향·D05-b 이미지 대상 목록. unknown event에 무조건 fallback 금지 |
| SharedDialogue | 안정 ID, situation FK, label, 평문, revision | D10 변수·D06-c 상황 이동. 대사는 상황 소속 Level로 검증 |
| CharacterLevelCandidates | CPU FK+Level FK+kind+공유 ID 관계 | D06-a A 명시 후보 참조. 신규 자동 포함 없음. 타 Level·kind·상황 관계 검증 |
| PresentationSelection | event identity, CPU/Level, 선택 ID·revision, 표시 문자열/이름·최종 P/N·설정 snapshot | 영속 범위 D08-b, 이미지 대상 D05-b, 빈 후보 D06-b/D10-b. 원문을 캐릭터마다 복제하는 것과 이벤트 snapshot은 다름 |
| GenerationRequest / Artifact | selection 참조, 요청 ID, endpoint/client/prompt ID, 최종 입력 digest·seed, 상태, immutable media 참조 | D07 실제 workflow·D08-a 동일성·D09 수명/복구. 전역 latest key로 다른 CPU job를 덮지 않음 |

후보 계산 순서는 event를 해석하고 오마케/노출 조건을 확인→CPU/Level 확인→허용 상황과
캐릭터 상황 후보의 교집합→그 상황의 대사와 캐릭터 대사 후보 교집합이다. 이미지 대상이면
해당 Level 복장 상태/포즈 후보도 별도 선택한다. D06-d A 확정으로 상황별 추가 제약 관계는 만들지 않는다.
대사 없음과 이미지 없음은 별개이며, legacy fallback(D10-b)까지 답변받기 전 동작을 고정하지 않는다.
P/N 결합 순서·구분자·모델 보정은 D07-a에 의존한다. 각 입력 원문·최종 결과를 혼동하지 않는다.

### event identity·RNG·늦은 생성 결과

- 규칙 원본은 기존 승인된 session/action 경계다. 콘텐츠 identity 초안은
  `(generation, session_id, action_version, source_kind, source_ordinal, cpu_id, event_key)`이다.
  행동은 **원본 pending batch index**를 정렬 전에 붙여 유지한다. 결과는 `source_kind=result`와
  CPU/event로 안정 구분하며 마지막 증가 후 stage를 snapshot한다. 생성 job ID·cache digest·
  엔딩 event UUID는 서로 다른 식별자다. 재접속할 때 새 UUID를 만들어 같은 표시를 새 이벤트로 만들지 않는다.
- W06 SFX identity는 그대로 유지한다. 신규 콘텐츠 identity가 엔진/합법 행동 index나 SFX를 재정의하지 않는다.
  관측 배열에서 같은 실세계 이벤트가 여러 번 관측되는지 별도 회귀로 확인하되 게임 규칙 이벤트 제거와
  혼동하지 않는다. source ordinal 확정 알고리즘은 실제 emission 경계와 함께 W07 후속 명세에 적는다.
- CPU RNG/engine seed/action log와 별도 콘텐츠 RNG를 쓴다. 기존 대사 policy RNG의 소비 횟수를
  이미지 추첨으로 바꾸지 않는다. 이미지 seed도 독립이며 D08-a 승인 방식으로 snapshot한다.
  UI 재렌더·GET·복구 replay는 새 추첨/submit의 원인이 아니다.
- D08-b A일 때 현재 selection 저장 및 event unique 제약을 제안한다. 새 이미지 선택은 행동 commit 후
  별도 짧은 writer transaction에서 고정하고 저장 성공 전 전송/submit하지 않는다. 콘텐츠 저장 실패는
  이미 commit된 마작 행동을 rollback하거나 거짓 성공으로 덮지 않는다. 중간 crash 시 미표시로 남는
  경계와 현재 표시 조회/재시도는 후속 계약에서 명시하며 미선택 과거 replay로 자동 복원하지 않는다.
  결과의 선택 snapshot은 현재 정산 presentation transaction을 재사용하되 네트워크 생성은 commit 이후다.
  D08-b B면 행동 표시의 영속 관계는 제외하고 완료 결과만 보존한다.
- UI는 generation+session+selection ID+현재 화면 토큰을 대조하고, job 완료도 selection/request ID로 연결한다.
  캐릭터 A 요청이 B 화면 뒤 완료, 새 대국/초기화 뒤 완료, 설정 수정 뒤 이전 job 완료 모두
  새 화면을 덮지 못한다. 파일 보존 여부와 현재 화면 표시 허용 여부는 별개다.
- adapter submit/status/result는 DB writer lock·registered game lock을 잡은 채 기다리지 않는다.
  같은 요청의 중복 submit 차단과 submit 응답 유실은 분리한다. prompt ID를 받기 전 연결이 끊긴
  요청을 무조건 재제출하면 중복 생성될 수 있으므로 자기 client/job 확인 후 명시 재시도하는 기술안을
  W10 계약에 작성한다. 재시작 때 미확인 job를 성공으로 간주하거나 전역 interrupt하지 않는다.

### 재사용 식별·파일 경계 초안

D08-a A 권고 시 selection identity와 cache identity를 분리한다. 같은 최종 입력의 다른 이벤트가
같은 artifact를 참조할 수 있다. 정규화한 versioned 입력에는 최종 P/N, 실제 모델·encoder/VAE,
순서/강도를 포함한 LoRA, workflow/node revision, 크기·steps·CFG·sampler/scheduler와 seed 정책을 넣는다.
최초 독립 seed/실제 요청 입력은 artifact metadata에 보관한다. B면 event 독립 seed도 입력 식별에 포함한다.
라벨/원본 경로/파일명만으로 동일성을 판단하지 않으며, 모델 내용이 같은 이름으로 바뀔 수 있으므로
파일 fingerprint를 얻을 수 없는 endpoint의 사용자 revision 처리도 W10에서 확정해야 한다.

기존 immutable media 서비스의 relative key/root 검사·인증 읽기·임시 파일→rename→metadata commit을
재사용할 수 있다. 생성 output 크기/형식과 실제 decode 검증·저장 subdirectory는 후속 기술 명세 대상이며
W06 업로드 제한을 생성 결과에 무조건 적용하지 않는다. ComfyUI가 반환한 경로나 URL을 renderer에
직접 전달하지 않는다. output fetch는 설정된 endpoint/자기 job 결과 범위로 제한하는 기술 계약을 준비한다.

기존 CG slot 파일을 이동/덮어쓰지 않는다. 설정 수정은 새 입력 식별로 이어지며 기존 파일/과거 snapshot은
자동 삭제하지 않는다. 외부 파일 누락은 metadata 성공만으로 정상 표시라 하지 않는다. D08-c 대기/실패
안내와 기본 대국 계속을 분리한다. 파일 삭제/복원/백업·갤러리·일괄 생성 UI는 이 설계에서 승인되지 않는다.

### API·UI 책임 초안과 migration/구 자료 호환

| 담당 | 제안 경계 | 승인 의존 |
|---|---|---|
| W08 local admin | `/api/local/characters/{id}/content`, `/content/levels`, `/content/{kind}`, `/characters/{id}/candidates/{level}`의 읽기·편집. 실제 HTTP method/오류/DTO는 후속 계약에서 확정 | D05-a/c, D06 전체, D07-b, D10-a/b |
| W08 UI | 게임 내부 캐릭터의 외모/복장 P/N·Level별 네 후보, 공유 원본 label/P/N·상황 대사 편집 | 후보/삭제/이동 정책 승인. 별도 Manager·기존 테이블 전체 재설계 없음 |
| W09 local engine | event→상황/대사 resolve·변수 치환·버전 있는 표시 payload. 현재 `dialogue_event`/결과와 호환 adapter | D05, D06-b, D08-b, D10. 노출 policy/웹 legacy 유지 |
| W10 local admin/adapter | `/api/local/generation-settings`, 모델 조회·연결 확인·submit/status/result의 내부 서비스 | D07/D09 및 D08-a 입력 형식. 실제 ComfyUI object_info/workflow 증거를 확보한 뒤 확정 |
| W11 local member/UI | 소유 selection 읽기·이미지 조회·승인된 재시도. renderer는 안전 URL/표시 상태 사용, prompt/job 소유권은 engine | D05/D08. 구체 endpoint·pending/retry 오류·취소 경계는 후속 계약 대상 |

현재 로컬 capability/member/admin·same-origin REST/WS·W04 단일 writer·응답 전 commit을 유지한다.
새 관리 쓰기는 진행/명단/정산을 암묵 변경하지 않는다. 낙관 revision 등 동시 편집 방식도 후속
DTO/오류 명세에 필요하지만 이번에 새 범용 편집 프레임워크를 채택하지 않는다.

migration은 현행 head `20261016_0006` 다음의 additive 변경으로 계획한다. CPU PK/명단/progress,
`game_sessions`의 seed·choices·actions·rules_snapshot·기존 presentation JSON과 W06 엔딩 payload를
재작성하지 않는다. legacy active는 원 snapshot으로 재생, completed는 원 결과를 읽는다.
새 콘텐츠 없는 기존 설치는 빈 등록으로 정상 대국 가능해야 하며 새 CG/대사/P/N seed를 만들지 않는다.
기존 `bootstrap.py`는 CPU slug가 있으면 건너뛰고 CPU/event 대사가 하나라도 있으면 해당 pool seed를
건너뛴다. 이를 새 공유 관계로 자동 변환/재삽입하는 것은 D10-b 승인 전 금지다.
B 이전안을 택하면 기존 행 ID→새 공유 ID의 명시 대응·한 번만 실행·재실행 중복 없음·실패 rollback을
설계하고 원본은 남긴다. 같은 문장이라는 이유만으로 다른 캐릭터의 대사를 무조건 병합하지 않는다.
기존 CPU CG API의 교체/삭제 의미는 legacy 경로에 보존하며 생성 파일 보존형 정책으로 몰래 바꾸지 않는다.
초기화는 새 등록/후보/생성 설정/파일을 보존하며 현재 표시/job의 이전 generation만 화면에서 격리한다.
웹 DB/미디어 자동 이전·다중 프로필·사용자 파일 작업은 범위 밖이다.

### 승인 뒤 필요한 검증 예제 — 아직 실행 결과 아님

| 검증 | 기대값/승인 의존 |
|---|---|
| stage 0→1, 2→3, 보충 stage 3/Tier 0, omake/Tier 2 | D05-a 대응만 적용, Tier로 Level 결정 금지. 오마케 신규 콘텐츠 출력 없음 |
| ron/tsumo, reach_accepted, 인간 actor, 결과/보충 승패 | 허용 event/상황 교집합·기존 policy 수치 유지. stage 증가와 보충 결과 구분 |
| 상황은 허용되나 대사 후보 교집합 없음 | D06-b+D10-b 승인 조합대로 생략/legacy fallback, 무관 상황 문장 금지 |
| 신규 항목·다른 Level ID·삭제/이동·후보 고갈 | D06의 포함/참조 정책, 파일 hash·과거 selection 불변 |
| 동일 event 중복·재렌더·현재 화면 재접속/재기동 | 새 추첨/중복 submit 없음, D08-b 복구 범위와 과거 replay 비발행 |
| 외모 P/N·LoRA 강도 변경, label만 변경, 같은 이름 모델 교체 | 최종 입력/정책별 식별 변화, label만으로 cache miss를 만들지 않음 |
| A job 뒤 B 표시, reset/새 대국 후 완료, 오래된 blob callback | ID/세대/화면으로 격리, 새 진행/대사/이미지를 덮지 않음 |
| ComfyUI 미연결·submit 응답 유실·출력 누락·저장 commit 실패 | D08-c 안내와 기본 대국 지속, 중복 submit/사용자 파일 삭제 없음 |
| 변수 이름에 괄호·HTML, 미지정 변수, 한국어 조사 | 승인 문법만 평문 치환·재귀 해석/HTML 실행/임의 조사 없음 |
| 0006 업그레이드/재부팅/반복 bootstrap·legacy active/completed | 원 데이터·CG·pending 엔딩 보존, policy 1/2 108행동 fixture 불변 |

기존 `test_dialogue_service.py` 10개(별도 pytest), `test_game_websocket.py`의 replay/commit 실패,
`test_local_play.py`의 reset/정산/omake, `test_result_assets.py`와 W06 사운드/browser 회귀를
후속 구현에서 보존한다. Windows CI·artifact와 사용자 PC/실제 ComfyUI 출력 증거는 따로 수집한다.
이번 문서 작업은 이 검사들의 통과를 새로 주장하지 않는다.

## 이미지 생성 경계와 Wayward 참고

참고 SHA `wayward-development@5d80f118c590319881be34faba8214a0c3765fc2`.

| 참고 파일 (`programs/wayward-anima-manager/` 아래) | 활용할 패턴 | 그대로 가져오지 않을 부분 |
|---|---|---|
| `src/config.ts`, `src/comfy/workflows/index.ts` | P/N·캐릭터 LoRA·모델/encoder/VAE graph 구성 | Wayward 인물명·game prompt strip·Best Girl 분기·자동 장면 힌트 |
| `src/comfy/client.ts` | object_info, prompt, queue/history, 오류 원인·자기 job 식별 | 게임 전용 식별 문자열 |
| `src/comfy/jobRunner.ts` | submit 중복 제거·완료 중복 저장 차단·늦은 요청 관리 | batch·전역 latestDesiredKey 정책의 무조건 이식 |
| `src/routes/image.ts`, `src/cache/cacheStore.ts`, `src/naming.ts` | 실제 생성 설정 hash·metadata+파일 분리·경로 관리 | Wayward imageType/talentName/cache cell·이미지팩 투영 |
| `src/history/generationJournal.ts`, `src/comfy/media.ts` | 생성 이력과 결과 파일 저장 참고 | 저장 수명/삭제 정책 자동 채택 |
| `mods/best-girl-add-mod/mod.js` | 캐릭터 설정/연결 흐름 참고 | WML API·세이브 후크·게임 상태 구조 |

참고 runner는 진행 job이 메모리에 있으며 재시작 복구가 보장되지 않는다. HTTP polling을
사용한다; 참고 코드를 WebSocket 진행 수신 구현이라고 기록하지 않는다.
ComfyUI 전역 interrupt는 다른 작업에 영향 가능하므로 자기 job 소유 범위를 확인한다.
게임 정산 transaction이나 UI 행동 대기는 ComfyUI 요청 완료를 기다리지 않는다.
실패/대기 이미지의 구체적인 표시와 재사용 정책은 D08 결정 전 구현하지 않는다.

참고 저장소 루트 LICENSE는 sintention 저작권의 MIT, NOTICE.md는 원본 wayward-imagegen
출처와 모델/ComfyUI/Wayward 미포함을 명시한다. package.json도 MIT다. 조사한 src 파일의
별도 라이선스 표기는 확인하지 못했다. 직접 복사 시 파일/유래·MIT 고지와 optional sharp,
Bun/Node 및 모델/LoRA/custom node의 개별 조건을 재확인한다. 이번 작업은 코드 복사 없음.
원본 Wayward ZIP은 이번 작업 입력으로 내려받지 않아 분석하지 않았다.

## 외부 근거 (2026-10-14 접속·내용 확인)

- [Electron process model](https://www.electronjs.org/docs/latest/tutorial/process-model):
  main/renderer 분리, 웹 UI 활용, host 수명 관리의 근거.
- [Tauri Windows installer](https://v2.tauri.app/distribute/windows-installer/):
  WebView2 offlineInstaller/fixedRuntime 대안. 이 프로젝트의 동작을 보장하는 자료는 아니다.
- [RiichiEnv 0.4.8 release files](https://pypi.org/project/riichienv/0.4.8/):
  `riichienv-0.4.8-cp312-cp312-win_amd64.whl` 존재, SHA256
  `50783478d424b0c6f9271bc153e01dc05eff64636be5e0ef4ea10f4e6fd60cd3`.
  Windows wheel 존재는 Python 번들 EXE 실행 검증과 구분한다.
