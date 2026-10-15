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
D01~D03/관리 UI는 이후 W03에서 사용자 승인됐다. D04 진행 정책은 여전히 미확정이다.

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

## 콘텐츠 데이터 구조 권고 — 스키마 미확정

| 개념 | 소유/관계 | 제안 책임 |
|---|---|---|
| CharacterAppearance / Outfit | character ID | 각 Positive/Negative, 규칙·진행도와 분리 |
| SharedClothingState / Situation / Pose | 공통 ID, Level, label | 원본 하나, P/N, 편집 식별 |
| SharedDialogue | situation ID, label, text | 상황별 여러 문장과 변수 |
| CharacterLevelCandidates | character ID + Level + 항목 종류 + 항목 ID | 후보/제외 참조; 공유 원문 복제 금지 |
| PresentationSelection | 표시 이벤트 ID + character/Level + 선택 ID/버전 | 재렌더링/늦은 생성 응답의 재선택·오염 방지 |
| GenerationRequest / Artifact | 표시 선택 + 최종 P/N + 생성 설정 + 파일 key | ComfyUI job와 결과 파일 연결 |

이름은 설명용이며 새 table/class 채택이 아니다. allow-list와 deny-list를 동시에 저장할지,
자동 포함·빈 후보·삭제 참조·상황 변경·Level 이동 정책은 W07에서 결정한다.
상황에서 허용된 대사와 캐릭터/Level 대사 후보의 교집합을 사용하도록 설계한다.
마작 event→허용 상황 매핑과 노출 정책을 거친 뒤 콘텐츠 선택을 생성한다.
CPU/규칙 RNG와 독립된 콘텐츠 선택을 유지한다. 재접속 시 표시를 재현할 범위,
텍스트/항목 수정 후 기존 이미지 식별, 저장 snapshot 범위는 D08 결정 대상이다.

캐시 키 권고는 선택 항목/버전, 최종 P/N, 실제 모델·LoRA/강도, workflow, 크기·steps·CFG·
sampler·seed 정책을 반영하는 것이다. 라벨/파일명만으로 동일성을 판단하지 않는다.
구체적인 key/seed/삭제 정책은 아직 미확정이다. 갤러리·일괄 생성 기능은 추가하지 않는다.

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
