# 현재 상태

## 기준

- 확인일: 2026-10-14. 조사한 main: `ba4fc43a89a39a328c7c308d6c90e145ab489d58` (#55).
- 초기 문서 작업 branch: `task/windows-offline-foundation`. 문서 commit/PR 상태는 Git에서 확인한다.
- 제품 코드·의존성·테스트는 이번 초기 작업에서 변경하지 않았다. Windows 전환 구현은 없다.
- Wayward 참고 main: `5d80f118c590319881be34faba8214a0c3765fc2` (Manager package 0.4.28).
  원본 Wayward ZIP은 이번 입력에서 분석하지 않았다. 참고 저장소도 변경하지 않았다.

## 코드로 확인한 구현

| 영역 | 상태/근거 |
|---|---|
| 기본 대국 | RiichiEnv 0.4.8, 사람 1 + CPU 3, `4p-red-east`/Tenhou 기본 규칙 |
| CPU | Tier 0/1/2, 6개 성인 seed, 성향 6개, 선택·stage 난이도 연결 |
| 진행/정산 | 최종 4위만 HP 또는 해당 CPU stage 변경, stage 3 제외, HP 0 게임 오버 |
| 복구 | seed/사람 행동 log/CPU·좌석 snapshot, 각 승인 행동 commit, 재생·중복 정산 방지 |
| 정책 호환 | 새 CPU snapshot policy 2, 기존 누락 policy 1, 108행동 legacy replay fixture |
| 대사/CG | CPU별 이벤트 대사·노출 정책, 결과 stage 대사, 단계 CG 관리자 API 및 회원 해금 표시 |
| 프런트 | 인증·CPU 선택·합법행동·meld/국번호·말풍선·결과·다음 선택·재로그인 복구 |
| 저장/실행 | PostgreSQL/Compose 기본, SQLAlchemy/Alembic 4개 migration; SQLite 테스트 경로 존재 |

6개 행동 이벤트 `riichi/chi/pon/kan/ron/tsumo` 및 defeat-stage 결과가 연결되어 있다.
`game_start`, `match_first/last` seed 문장은 있으나 그 시작/순위 이벤트 표시 연결은 없다.
프로필 key가 없으면 문자 avatar를 표시한다. 프로필 이미지 업로드 및 관리자 웹 UI는 없다.
기본 대국 기능을 재사용할 수 있는 상태이지만 최종 진행 루프/완성 콘텐츠/Windows판 완료가 아니다.

## 이번 실행 검증

- Python 3.12.14 / RiichiEnv 0.4.8: backend `unittest discover -s tests -v` **72개 통과**.
  임시 venv에 `uv pip install -r pyproject.toml --extra test`로 선언 의존성을 설치했다.
- Node 24.19.0, frontend `npm ci` 및 `npm run build` 통과 (TypeScript/Vite).
- `uv pip install -e '.[test]'`는 setuptools의 app/alembic flat-layout package 자동 탐색
  오류로 실패했다. 제품을 수정하지 않고 의존성만 설치해 test했다. W02 빌드 검증에 인계한다.
- 문서 링크·Task 의존성·legacy 본문 보존 및 `git diff --check` 검사 대상은 문서 변경이다.
- Chromium 실행 파일을 이 환경에서 확보하지 않아 브라우저 회귀/실제 서버 재시작을 이번에
  재실행하지 않았다. 기존 검증 기록과 이번 직접 실행 결과를 혼합하지 않는다.
- 이번 작업에서 Windows, ComfyUI/StabilityMatrix 실기, Docker/nginx/PostgreSQL,
  실제 미디어, 전원 차단, 복수 worker, EXE 패키징/CI는 검증하지 않았다.
  저장소에는 `.github/workflows`가 없다; CI 통과 결과를 주장하지 않는다.

## 기존 검증 증거 (재실행 아님)

- `docs/DECISIONS.md`, `docs/WORK_HANDOFF.md`: 2026-10-14 실제 React/FastAPI/Vite/SQLite
  대국 108행동 및 12행동 후 API SIGTERM 재시작, 전체 턴 동일 복구, 완료 재접속/정산 보존 기록.
- `docs/WORK_HANDOFF.md`의 2026-09-12 Docker 최종 통합: nginx·PostgreSQL·media volume
  및 migration/재시작 보존 기록. 최근 제품 전체의 Windows/전원 차단 보장을 의미하지 않는다.
- `frontend/tests/README.md`: 3개 routed browser 회귀와 `live-game.browser.mjs` 재현 절차.
  `backend/tests/fixtures/README.md`: legacy replay 원본·계산 기준.

## 중요한 차단/불일치

1. **진행:** 선택 가능 CPU 3명이 필요하고 stage 3은 제외된다. 6명 중 4명을 완료하면
   2명만 남아 이후 시작 불가능. 모든 CPU 완료라는 기존 목표와 실제 진행 경로가 충돌한다.
   D04 사용자 결정 전 filler/재선택/인원 변경·HP reset을 구현하지 않는다.
2. **실행:** Windows shell, 번들 Python, localhost static/API 제공, 기동/종료 관리가 없다.
   RiichiEnv cp312 Windows x64 wheel은 확인했지만 배포 EXE 실행은 미검증이다.
3. **저장:** SQLite 시험 성공과 제품 전환은 다르다. PostgreSQL 행 잠금/환경·웹 인증·
   `/data/media` 경로와 bootstrap을 Windows 실행 조건에 맞춰 검증해야 한다.
4. **콘텐츠:** 공유 Level별 프롬프트·후보·상황/대사 관계·변수·ComfyUI 연결·생성 캐시 미구현.
5. **문서:** 기존 docs에는 초기 목표 트리, Tier 1/2 미구현 등 시점별 서술과 Docker 완료/보류
   서술이 함께 있다. 루트 기준 문서가 현재 인계점이다. 과거 증거 본문은 보존한다.
   CPU 난이도 순서가 확실히 검증됐다는 결론도 금지: 최신 정책의 고정 표본은 작다.

## 다음

초기 기준 문서 준비 W00 완료. 다음 허용 범위는 [TASKS.md](TASKS.md)의
**W01 기존 기능·회귀 기준 확정**이며 저성능 Work에 적합하다.
W02 격리 Windows 검증은 W01 결과를 기준으로 시작한다. 기술 최종 채택/로컬 프로필 정책은
W03, 진행 규칙은 D04, 콘텐츠 세부 정책은 W07 전에 각각 결정한다.
