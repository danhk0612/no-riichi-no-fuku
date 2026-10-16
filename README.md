# No Riichi No Fuku

`No Riichi No Fuku`는 1인용 4인 일본 리치마작 게임 프로젝트입니다.
웹 서비스와 별도로 Windows x64용 Electron·로컬 SQLite 실행 경로를 구현 중이며,
최신 packaged renderer와 미디어 설정 검증 결과는 저장소 `CURRENT_STATE.md`에 기록합니다.
정식 Windows Release와 최소 client OS는 아직 확정되지 않았습니다. 로컬 ComfyUI 이미지
생성 확장은 아직 구현되지 않았습니다.
Windows 목표에서는 플레이어 1명과 확정 명단의 CPU 캐릭터들이 동풍전을 진행합니다.
미완료 CPU가 최종 4위일 때 진행도가 오르며, 전체 완료 뒤에는 추가 이벤트 없는 오마케를 제공합니다.
자세한 진행 정책은 [REQUIREMENTS.md의 D04](REQUIREMENTS.md)를 따릅니다.

## Windows 로컬 진행 정책

2026-10-15 사용자 결정: Windows 목표에서 플레이어 HP를 없애며, CPU 부족 시 완료 CPU 참여,
고정 참가 명단, 엔딩 후 최고 난이도 오마케(추가 이벤트 없음), 자료를 보존하는 초기화와
효과음/배경음 목록 관리·상시 설정 변경을 지원한다. CPU HP는 별도 시스템이 아닌 기존 완료 단계의 표현이다. 세부는
[REQUIREMENTS.md의 D04](REQUIREMENTS.md)를 따른다. W06에서 로컬 경로에 구현했으며 실제 CG·오디오 출력은
리소스 제공 후 확인이 필요하다. 아래 웹판 기능/HP 설명은 기존 웹 경로의 동작이다.

## 현재 웹판 기능

브라우저에서 회원가입·로그인, CPU 3명 선택, 동풍전 진행, 결과 확인과 다음 대국
선택을 할 수 있습니다. Tier 0/1/2 CPU, 대국 중 말풍선, 좌석별 치·퐁·깡 조합과
현재 국 번호, 결과 대사와 등록된 단계 CG 표시가 연결되어 있습니다.

진행 중인 대국은 서버에 저장됩니다. 연결이 끊기거나 서버가 재시작되어도 다시
로그인하면 저장된 대국에 복귀합니다. 관리자 기능은 현재 API로 제공하며 별도의
관리자 웹 화면과 프로필 이미지 업로드는 아직 제공하지 않습니다.

## Windows validation package

`task/w05-windows-shell` 브랜치의 [W05 Windows workflow](https://github.com/danhk0612/no-riichi-no-fuku/actions/workflows/w05-windows-shell.yml)는
Windows x64 Electron·Python engine package, packaged renderer smoke, 별도의 일반 모드
종료·재기동 검사를 실행하고 시험 ZIP을 Actions artifact로 보관합니다. 성공한 실행의 `w05-windows-<source SHA>` artifact에서 ZIP을
받아 압축을 풀고 `No-Riichi-No-Fuku.exe`를 실행할 수 있습니다. 이 artifact는 검증용이며
정식 Release/tag가 아닙니다.

Windows 실행 경로는 Python, Node.js, Docker, PostgreSQL 서버, 인터넷 게임 서비스,
ComfyUI가 없는 기본 대국을 목표로 합니다. 사용자 데이터는 실행 폴더와 분리해
`%LOCALAPPDATA%/NoRiichiNoFuku/` 아래에 저장하며 기존 웹 DB/미디어를 가져오지 않습니다.
현재 CI 증거는 Windows Server 2022 x64 hosted runner 기준입니다. 일반 모드 programmatic
창 닫기와 반복 종료 요청은 engine PID 종료 후 창 파괴 및 host 종료 순서까지 검사합니다.
물리 창 X/Alt+F4, 개인 Windows 버전별 실행, OS 수준 인터넷 차단은 별도 실측으로 구분합니다.

현재 Windows 로컬 기능에는 한 프로필의 자동 저장·대국 복구, 첫 플레이 CPU 참가 명단 확정,
진행 초기화와 자료 보존, 효과음 세트·배경음 등록 및 사용 선택, 엔딩 이미지·음악·평문 대사
설정이 포함됩니다. 효과음/BGM 선택은 CPU 명단·진행도와 독립적으로 저장됩니다.
게임 내 **사운드·자료 설정**에서 MP3·WAV·Ogg 오디오와 JPEG·PNG·WebP 이미지를 등록할 수 있습니다.
등록 파일은 설정 교체·비활성화·진행 초기화로 삭제되지 않습니다. 새 설치는 효과음 세트 미선택,
배경음 빈 목록, 엔딩 자료 미등록 상태로 시작합니다. 실제 CG·음악은 제공 리소스가 없어
CI에서는 mock/미등록 경로만 검사합니다.

### 캐릭터 프롬프트·팩 설정

Windows 실행창 상단의 **캐릭터 프롬프트·팩 설정**에서 기존 캐릭터의 외모·상의 속옷·하의 속옷
긍정/부정 프롬프트와 단계별 프로필·전신·CG 구도 프롬프트를 편집할 수 있습니다. 변경한 필드만
저장하며 비워서 저장한 값도 편집값으로 유지됩니다. 저장 중에는 입력이 잠시 잠깁니다.
편집 내용은 게임 재시작·진행 초기화 후에도 보존됩니다. **팩 목록·진단** 탭에서 등록 상태를
확인하고 폴더를 다시 검색할 수 있습니다.

캐릭터와 등록된 캐릭터팩을 각각 선택한 뒤 **선택한 팩 연결·적용**으로 처음 연결할 수 있습니다.
캐릭터의 이름·성향·참가 명단·진행도는 바뀌지 않습니다. 연결 후에는 적용 revision과 등록 revision을
구분해 표시하며 **같은 팩의 등록 revision 적용**으로 갱신합니다. 재검색만으로 자동 적용하지 않습니다.
직접 편집한 P/N은 빈 문자열과 원본과 같은 값도 유지하고 미편집 문자열만 새 원본에서 가져옵니다.
편집 기록과 **적용한 팩 원본 P/N**을 비교할 수 있으며 단계별 이미지의 보관 참조도 표시합니다.
미저장 편집 내용은 먼저 저장해야 적용할 수 있습니다. 적용 실패/충돌 시 기존 적용값은 유지됩니다.
다른 팩으로 교체·연결 해제와 이미지 생성은 이번 기능에 포함되지 않습니다.

### 오디오 팩·캐릭터 음성

**사운드·자료 설정**에서 효과음(SFX)과 배경음(BGM)은 각각 기존 선택 또는 단일 오디오팩 중 하나를
사용하도록 설정할 수 있습니다. 팩 모드에서는 슬롯별 선택팩, 지정 기본팩, 무음 순으로 찾습니다.
기존 자료와 재생은 보존되며, 팩 모드로 전환한 영역은 기존 재생과 중복되지 않습니다. 캐릭터별 음성은
기본팩·선택팩·끔을 독립 설정합니다. 새 캐릭터팩 적용은 기본 음성팩만 갱신하고 선택/끔 설정을 보존합니다.
유효한 음성팩에 특정 슬롯이 없으면 무음 처리합니다. 대국의 기본 선언 텍스트는 캐릭터 음성과 독립이고,
각 국 화료에는 별도 `win` 음성을 재생합니다. 최종 4위 음성은 정산 후 변경된 단계의 패배 슬롯을 사용합니다.
오마케에서도 기본 선언·화료·최종 4위 대사는 유지하며 stage/Tier와 추가 진행/CG 이벤트는 바뀌지 않습니다.
실제 오디오 파일은 사용자가 제공·등록해야 하며, 이번 변경에서 새 오디오를 만들거나 저장소에 넣지 않습니다.

## 현재 웹판 실행하기

Docker와 Docker Compose가 설치된 환경에서 저장소 루트에서 실행합니다.

```sh
cp .env.example .env
```

실행 전에 `.env`의 다음 값을 설정합니다.

| 항목 | 용도 |
|---|---|
| `POSTGRES_PASSWORD` | DB 암호 |
| `SUPERADMIN_LOGIN_ID` | 최초 최고 관리자 ID |
| `SUPERADMIN_INITIAL_PASSWORD` | 최초 최고 관리자 암호 |
| `JWT_SECRET` | 인증 서명용 임의 문자열. 최소 32바이트 |
| `WEB_PORT` | 접속 포트. 기본값 `8080` |

예시 암호와 JWT 값은 자신의 값으로 바꾼 뒤 실행합니다.

```sh
docker compose up --build -d
```

처음 실행할 때 DB migration, 최고 관리자 생성과 기본 CPU·대사 등록이 자동으로
진행됩니다. 준비가 끝나면 [http://localhost:8080](http://localhost:8080)에 접속합니다.
`WEB_PORT`를 바꿨다면 해당 포트를 사용합니다.

```sh
docker compose ps
docker compose logs api
```

중지는 `docker compose down`, 다시 시작은 `docker compose up -d`로 합니다.
회원·진행 데이터는 `postgres_data`, 업로드 미디어는 `media_data` 볼륨에 저장되므로
데이터를 유지하려면 이 볼륨을 보존해야 합니다.

## 웹판 대국 진행하기

1. **새 회원으로 시작**에서 ID·비밀번호·플레이어 이름을 등록하거나 기존 계정으로 로그인합니다.
2. CPU 3명을 선택합니다. 선택 순서대로 좌석 1·2·3에 배치됩니다.
3. **동풍전 시작**을 누릅니다. 버릴 손패 또는 표시된 합법 행동 버튼을 선택합니다.
4. 종료 후 최종 순위와 HP 또는 CPU 패배 단계 변화를 확인합니다.
5. 게임 오버가 아니라면 **다음 대국 선택**으로 돌아갑니다.

새 회원의 HP는 기본 3입니다. 점수·순위·HP·CPU 진행도는 서버가 판정합니다.
CPU가 최종 4위가 되면 해당 단계의 결과 대사와 등록된 CG를 표시합니다. CG가
없으면 미등록 안내를 표시하며, 불러오기에 실패해도 순위와 다음 대국 선택은 유지됩니다.

### 연결이 끊겼을 때

새로고침 후 같은 계정으로 다시 로그인합니다. 서버에 진행 중인 대국이 있으면
자동으로 해당 대국으로 돌아갑니다. 연결 종료 후 행동 버튼은 잠기며, 자동 재접속은
제공하지 않습니다. 로그인 정보는 현재 탭 메모리에만 보관하므로 새로고침하면 재로그인이
필요합니다. 복구 범위는 서버에 저장이 완료된 행동까지입니다.

## 핵심 규칙

- 웹 기반 회원가입 및 로그인
- 계정별 플레이어 이름·HP·CPU 진행도 유지
- 게임 시작마다 사용 가능한 CPU 캐릭터 3명 선택
- 4인 일본 리치마작 동풍전
- CPU가 최종 4위: 해당 CPU 캐릭터 패배 단계 +1
- 패배 단계가 오를수록 해당 CPU 난이도 상승
- CPU가 3회 최종 4위를 기록하면 최종 단계 완료 후 이후 선택 불가
- 플레이어가 최종 4위: HP -1
- 플레이어 HP가 0: 게임 오버
- 주요 상황에서 캐릭터 말풍선/대사 출력
- 게임 종료 시 CPU가 4위라면 해당 단계 CG와 결과 대사 출력
- CG 파일은 저장소에 커밋하지 않고 관리자 업로드를 통해 런타임 저장소에 보관

## 기술 스택

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Python
- Mahjong engine: RiichiEnv
- Database: PostgreSQL
- Realtime game communication: WebSocket
- Deployment: Docker Compose
- Runtime media: Docker persistent volume

## CPU와 패배 단계

외부 LLM/API를 사용하지 않습니다. CPU는 서버 내부의 공통 의사결정 엔진으로 구현하고, 캐릭터 패배 단계에 따라 난이도를 높입니다.

| 패배 단계 | 다음 대국 CPU | 상태 |
|---|---|---|
| 0 | Tier 0: 기본 패효율 | 선택 가능 |
| 1 | Tier 1: 패효율·기본 수비·타점 | 선택 가능 |
| 2 | Tier 2: 공수·위험도·순위 상황 | 선택 가능 |
| 3 | 없음 | 최종 완료·선택 불가 |

CPU 캐릭터의 플레이 성향과 난이도는 분리합니다.

## 관리자와 이미지 등록

최고 관리자는 `.env`의 초기 계정으로 인증한 뒤 최초 비밀번호를 변경해야 관리자
API를 사용할 수 있습니다. 변경 후 초기 환경변수 암호로 다시 덮어쓰지 않습니다.

| 작업 | API |
|---|---|
| 로그인·비밀번호 변경 | `POST /api/auth/login`, `POST /api/auth/change-password` |
| 회원 조회·활성 상태 관리 | `/api/admin/users` |
| CPU 정보·성향·사용 상태 관리 | `/api/admin/cpus` |
| CPU 대사 관리 | `/api/admin/cpus/{cpu_id}/dialogues`, `/api/admin/dialogues/{dialogue_id}` |
| 단계 CG 조회·업로드·교체·삭제 | `/api/admin/cpus/{cpu_id}/result-assets` 및 `/{defeat_stage}` |

관리자 요청에는 로그인 시 받은 access token을 `Authorization: Bearer ...`로 전달합니다.
요청 형식은 [인증 스키마](backend/app/schemas/auth.py)와
[관리자 API](backend/app/api/admin.py)를 참고합니다. 일반 게임 로그인 화면은 회원용입니다.

결과 CG는 JPEG·PNG·WebP, 파일당 최대 5 MiB이며 단계 1·2·3에 등록합니다.
회원은 자신이 해금한 단계만 열람할 수 있습니다. 이미지 파일은 관리자 API로 런타임
볼륨에 올리며 Git 저장소에는 CG·더미 이미지가 포함되지 않습니다.

## 현재 제한과 미확정 사항

- 프로필 이미지 업로드와 관리자 웹 화면은 제공하지 않습니다.
- 시작에는 HP가 남아 있고 선택 가능한 CPU가 3명 필요합니다.
- HP 0이면 게임 오버 안내를 표시하고 다음 대국 버튼을 숨깁니다. 이후 HP 회복·진행 초기화·재시작 정책은 미확정입니다.
- 모든 CPU 완료 후 엔딩 및 선택 가능한 CPU가 3명 미만일 때의 후속 진행 규칙은 정해지지 않았습니다.
- 서버 저장은 seed와 행동 로그의 재생 방식입니다. CPU 정책 변경 시 기존 대국의 정책을 보존해야 합니다.
- 여러 API worker를 동시에 사용하는 운영 구성은 검증하지 않았습니다.

## 개발 기준 문서

- [프로젝트 목적](PROJECT.md)
- [확정 요구사항·결정 대기](REQUIREMENTS.md)
- [현재 구조·전환 권고](ARCHITECTURE.md)
- [현재 구현·검증·차단](CURRENT_STATE.md)
- [Task·선행 조건·다음 지시문](TASKS.md)
- [Chat/Work 작업·인계 규칙](AI_WORKFLOW.md)
- [브라우저 회귀·실제 서버 재시작 실행법](frontend/tests/README.md)

Windows 개발은 위 루트 문서를 기준으로 시작합니다. 기존 웹판의
[계획](docs/PROJECT_PLAN.md), [구조](docs/ARCHITECTURE.md),
[결정](docs/DECISIONS.md), [검증 인계](docs/WORK_HANDOFF.md),
[라이선스 검토](docs/OPEN_SOURCE_REVIEW.md)는 참고·검증 증거로 보존합니다.
기존 Docker 통합·직접 FastAPI/Vite/SQLite 재시작과 Windows 실기 검증은 서로 다릅니다.

## 라이선스

현재 프로젝트 자체 코드는 MIT License로 시작합니다.

RiichiEnv는 Apache-2.0 의존성으로 사용합니다. 추후 Mortal 등 AGPL/GPL 코드를 프로젝트에 결합해야 하는 경우, 결합 방식과 라이선스 조건을 확인하고 해당 변경과 동시에 프로젝트 라이선스를 호환되는 GPL/AGPL 계열로 변경합니다.
