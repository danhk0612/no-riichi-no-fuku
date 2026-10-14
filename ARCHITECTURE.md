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

## 권장 목표 구조 — 사용자 채택 전

첫 검증 후보는 **Electron + 기존 React + 번들 Python/FastAPI/RiichiEnv + SQLite**다.
저장/실행 기술 확정은 W02의 Windows 증거와 W03 사용자 결정을 거친다.

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
하드코딩된 관리자/JWT로 대체하지 않는다. 인증은 D02 결정 사항이다.

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
