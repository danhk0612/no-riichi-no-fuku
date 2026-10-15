# 현재 상태

## 기준

- 확인일: 2026-10-15. W05 검토 기준 main `99dd432e09d9029c495a6817bae4e42aaebb28ab`.
- W04 제품 코드 검증 SHA는 `455d400c4a8ddf11eaa0e3d676317c80b9a553b2`이다.
  PR #61은 main에 병합됐다. W05 PR #63은 종료 경로 보완 전 병합하지 않는다.
- PR #56(W00)·#57(W01)·#58(인계)는 main에 병합됐다. 열린 #35는 기존 Docker 문서이며 건드리지 않는다.
- W01 baseline 이후 W04는 local runtime·DB 연결/권한 경계·관련 회귀만 추가/수정했다.
  CPU/규칙/정산 핵심·legacy fixture·기존 frontend는 보존했다.
- W02 PR #59를 병합했다. 검증 code SHA 이후 변경은 기준 문서 4개뿐이며,
  CI job/다운로드 artifact의 source SHA·내외 ZIP hash·browser/frozen/renderer 증거를 다시 대조했다.
  이번 검토는 기존 Windows 실행 증거 검토이며 Windows를 새로 실행한 결과가 아니다.
- 로컬 저장/runtime은 W04에 구현됐고 Windows 실행창·번들·로그인 없는 화면 진입은 아직 없다. W02 Windows Actions/PR #59 artifact·사용자 증거 첨부 경로와
  격리 후보 검증은 아래에 기록한다. 후보 통과를 제품 완료 또는 최종 기술 채택으로 해석하지 않는다.
- Wayward 참고는 W00의 `5d80f118c590319881be34faba8214a0c3765fc2` 조사뿐이다.
  W02는 참고 코드 복사·ZIP 분석·이미지 생성·사용자 데이터 연결을 하지 않는다.

## W05 PR #63 — 검토 결과, 종료 경로 보완 필요

검토 head `5d249962dd1aff9d943cc2f4fc0e62a0a6a4735f`; 제품·검사·workflow는 Windows 검증
code `c9cb8515a50c4a2387ca70a5be42b11cf9a7029e`와 같고 이후 변경은 CURRENT_STATE뿐이다.
Electron host/private pipe capability·frozen engine·same-origin React·로컬 이름 편집·active/최근
완료 결과 복귀가 PR에 구현됐다. 아직 main의 구현으로 간주하지 않는다.

Windows Server 2022 x64 run [38666626946](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38666626946)
job 116199947741은 source unittest 81/대사 pytest 10, React build, freeze/package, renderer smoke,
ZIP 생성이 success다. artifact 11942211016을 내려받아 source SHA, renderer checks 및 archive
SHA256 `edb5521f7d81428a66c790df1f78547bc4e9c01bfe7b9ed7adc14c31906efe74` 일치를 확인했다.
smoke에서 이름 저장, active 복구, 실제 대국 완료, 완료 재접속, 충돌/소유 child 회수는 통과했다.
이번 Linux 재검사도 unittest 81(36.818초)/pytest 10(0.08초), npm ci/build 통과다.

**병합 차단:** `desktop/main.cjs`의 일반 실행 창 종료는 engine 회수 완료 전에 app 종료를 허용한다.
`finishQuit()`가 quitting=true 후 window.destroy()를 호출하면 마지막 창의 window-all-closed
handler가 !smoke에서 app.quit()를 호출한다. before-quit는 quitting=true여서 차단하지 않는다.
그 뒤에야 100ms delay와 stopEngine()이 이어진다. 현재 함수·handler를 Node VM/EventEmitter로
실행해 `window.destroy → app.quit allowed=true → delay → stopEngine → app.quit allowed=true`
순서를 재현했다. 이는 Windows 실기 재현이 아니라 실제 소스의 제어 흐름 검사다.
엔진의 stdin EOF 종료 시도가 있더라도 host가 완료/timeout/회수를 기다린다는 계약은 보장되지 않는다.

기존 --smoke는 window-all-closed의 종료 분기를 건너뛰어 이 결함을 검사하지 못한다.
일반 실행의 X/Alt+F4/app.quit 경로를 공통 종료 orchestration으로 연결하고, 소유 engine의 close를
기다린 뒤에만 최종 app 종료를 허용해야 한다. 대기 중 재진입/중복 quit에도 동일하게 적용한다.
수정 전 실패하는 회귀 및 Windows packaged 일반 모드 종료 검사를 추가하고 정확한 수정 SHA의
CI/artifact를 재확인한다. renderer와 engine을 함께 종료·재실행한 저장 복구도 확인한다.

개인 Windows/물리 X 클릭·OS network-off·최소 client OS·clean-machine VC runtime·전원 차단과
장기 Python 보안 patch는 별도 미검증이다. 기존 smoke 성공 이력은 보존한다. PR #63은 열린 채로
보완하며 W06은 D04 결정 전 착수하지 않는다. 다음 Work 지시문은 TASKS를 따른다.

## W04 PR #61 — 최종 검토·보완 결과

2026-10-15 W04 보완과 재검토를 수행했다. 사용자 프로필 수정은 요청 Session과 공유하고,
local 읽기/쓰기 경계를 분리하며 파일 DB 정산 commit 실패 복구를 검사한다.
최종 재검토에서 기본 SQLite engine에 남은 조회 잠금과 고립 surrogate 토큰 예외를 추가 재현했다.
해당 두 회귀 검사는 수정 전 각각 database is locked/UnicodeEncodeError로 실패했다.
`455d400`은 SQLite 설정을 local opt-in에만 설치하고 모든 비ASCII 토큰을 정상 거절한다.
기본 engine의 원본 main 동시 읽기·FK 의미, local의 FK/쓰기 직렬화·이름/정산 복구를 함께 검증했다.
최종 Linux Python 3.12.14/RiichiEnv 0.4.8 unittest 81개(35.752초), 대사 pytest 10개(0.10초) 통과.
Windows 최종 검증: code `455d400c4a8ddf11eaa0e3d676317c80b9a553b2`의 push
[CI 38660753146](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38660753146) 전체 success.
Windows Server 2022 x64(build 20348)/Python 3.12.10/Node 24.19.0에서 unittest 81개
(48.885초), 대사 pytest 10개(0.10초), frontend build를 통과했다. artifact `11937654546`
`w04-windows-455d400c4a8ddf11eaa0e3d676317c80b9a553b2`의 다운로드 ZIP SHA256
`3c628bcf53b70c10538b43732277400a790cc253a5805afae13a2cdb407b0631`이 Actions digest와
일치하고 source-sha 및 로그의 81/10 통과를 대조했다. 이후 인계 commit은 문서만 바꾸며
이 code SHA와 동일한 제품/검사/workflow에 한해 위 결과를 이어받는다.
기존 성공 이력은 아래에 보존한다. W05 shell/사용자 Windows/전원 차단 성공으로 해석하지 않는다.

이전 W04 검증 이력: code SHA `3081dc56a2be95dd30ce0fa78a413da9b4bfeb29`에서 Linux backend
unittest 78/대사 pytest 10/frontend build를 통과했다. Windows Server 2022 Datacenter x64
(build 20348), Python 3.12.10, Node 24.19.0의 run 38572718064에서 unittest 78(54.438초),
pytest 10(0.13초), frontend build가 통과했다. artifact `w04-windows-3081dc56a2be95dd30ce0fa78a413da9b4bfeb29`
(ID `11897978928`, SHA256 `a4bb5b49a4a4886c415c0883e4b20b7601371d139abda261f3edba8c4e5bdca8`,
2026-10-28 만료)의 source SHA와 test 로그를 확인한 기록을 보존한다. 기존 결과는 새 수정 SHA 검증이 아니다.

이번 보완 코드는 local auth dependency가 요청 transaction의 User를 그대로 반환하도록 바꾸고,
capability의 ASCII 형식을 확인해 비교한다. local session에 쓰기 의도를 명시해 해당 연결을 조회 전에
`BEGIN IMMEDIATE`로 시작하며 일반 읽기는 writer reservation을 얻지 않는다. 기본 engine의 기존
SQLite transaction 기본값은 유지한다. profile PATCH→GET→재시작, member/admin/REST 및 WS의
malformed·비ASCII·누락·이전 실행 capability 거절, 동시 읽기·writer·stale action, admin write,
파일 DB 최종 행동 commit 후 정산 commit 실패/rollback·cache eviction·재기동 후 반복 재접속
검사를 추가했다. 아래 결과는 이번 로컬 실행 결과이며 정확한 GitHub Windows CI/artifact 검증은
push 후 별도로 확인한다.

| 발견 | 보완 결과 |
|---|---|
| 이름 편집 비영속 | 보완 완료: local auth와 endpoint가 같은 요청 Session의 User를 공유하고 PATCH→GET→별도 DB/runtime 재시작 후 이름을 확인 |
| 잘못된 토큰의 비정상 예외 | 보완 완료: ASCII 확인과 상수 시간 비교로 REST/member/admin 및 WS에서 비ASCII·잘못됨·누락·이전 실행 토큰을 거절하고 WS 4401 close 확인. 응답에 secret을 내보내지 않음 |
| 조회 transaction의 배타 잠금 | 보완 완료: 로컬 read는 deferred transaction, local HTTP write/WS action·settlement는 첫 DB 조회 전 BEGIN IMMEDIATE. 별도 writer 예약 중 read 성공, 동시 active writer 및 stale action 검사 |

정산 검사는 local runtime의 파일 DB에서 마지막 행동 commit 이후 정산 commit 실패만 주입했다.
실패 시 행동 log/status/HP/stage 원자성과 cache eviction을 확인하고, 새 runtime의 재접속/반복
재접속에서 같은 결과 및 한 번의 진행도 변경만 남는지 검사한다. 기존 마지막 행동 후 미정산 복구
검사와 별도다. 기존 78+10/Windows 성공 이력은 보존하며 이번 Linux 검사에서 Windows/browser를
실행했다고 기록하지 않는다.

이번 Linux/Python 3.12.14 임시 venv: backend unittest 81개(35.058초), 대사 pytest 10개(0.11초),
frontend `npm ci && npm run build` 통과. 정확한 보완 code SHA `d46782bef4947ff448b2d40555ac4b387b2bc25a`의
Windows Server 2022 Datacenter x64(build 20348), Python 3.12.10, Node 24.19.0 push CI
[run 38659727577](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38659727577)도
unittest 81(68.606초), pytest 10(0.14초), frontend production build와 artifact 수집이 통과했다.
artifact `w04-windows-d46782bef4947ff448b2d40555ac4b387b2bc25a` (ID `11938706685`, SHA256
`c4f778a5cb4fcf51bc73ac59404dd2043c14968c6b77ca2956cb508d0e335bff`, 2026-10-29 만료)의
`source-sha.txt`는 정확히 `d46782bef4947ff448b2d40555ac4b387b2bc25a`이며, 다운로드 ZIP hash와
Actions artifact digest가 일치하고 unittest/pytest 로그를 확인했다. PR-triggered run
38659729790도 전체 성공이나 artifact의 source SHA는 pull_request merge ref이므로 exact branch
검증 근거로는 위 push run을 기록한다. 이는 이전 code SHA의 검증 이력이다. 전원 차단
durability 및 사용자 Windows UI/LocalAppData는 여전히 미검증이다.

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

## W02 Windows runtime spike — 기술 검증 완료, 사용자 실기 미검증

기준 main `7523d4177140d303c5f4681c5ff94d92610db227`; W01 제품 baseline과
backend/frontend tree가 동일하다. 격리 코드: `spikes/w02/`, 전용 workflow:
`.github/workflows/w02-spike.yml`. PR #59가 Windows artifact·사용자 결과 첨부 경로다.
제품·CPU/진행·migration/fixture·사용자 자료 변경 없음; D01~D03/D09 기술/프로필 채택은 W03,
CPU 3명 미만·HP 0 이후(D04)는 W06 미확정 유지.

### 실측 환경과 명령

Linux: Ubuntu 24.04.3 x64 / Linux 6.18.44, Python 3.12.14, uv 0.12.23,
Node 24.19.0 / npm 11.9.0. 코드 검증 대상 `ec6123616aa389ebba0e5eb3c0aaee6667dd9fab`.
backend 선언 의존성 + test extra/pytest 9.1.1/PyInstaller 6.22.3/setuptools 80.9.0을
`/tmp/nrnf-w02`에 설치했다. W01 의존성 해석 결과와 주요 버전이 같으며 uvloop 0.23.0 등
OS별 의존성은 Windows 환경과 같다고 가정하지 않는다.

```sh
uv venv /tmp/nrnf-w02
uv pip install --python /tmp/nrnf-w02/bin/python -r backend/pyproject.toml --extra test \
  pytest==9.1.1 pyinstaller==6.22.3 setuptools==80.9.0
# backend에서
/tmp/nrnf-w02/bin/python -m unittest discover -s tests -v
/tmp/nrnf-w02/bin/python -m pytest tests/test_dialogue_service.py -v
uv pip install --python /tmp/nrnf-w02/bin/python --no-build-isolation -e .
# 마지막 명령은 알려진 flat-layout 발견 오류 재현용이며 설치 실패가 예상 결과
# frontend에서
npm ci
npm run build
# 루트: Linux에서는 build.py의 engine 수집 단계까지만 별도 실행(Windows shell 아님)
# 생성된 native Linux 엔진 검사
spikes/w02/out/engine/w02-engine/w02-engine regression
```

| Linux 검사 | 실측 결과 | 범위 |
|---|---|---|
| source unittest / 대사 pytest | 72개/32.018초, 10개/0.09초 통과 | 원본 검사 그대로 |
| frontend ci/build | exit 0, Vite 8.3.0 build | 원본 lock/build 그대로 |
| editable 설치 | exit 1, `Multiple top-level packages ... ['app', 'alembic']` | 제품 pyproject 수정 없이 명시 소스 import로 우회 |
| frozen engine regression | 72개/37.861초, 10개/0.08초 통과, exit 0 | namespace/source import 수집 보완 후 결과. 기존 policy 1/2/legacy 검사 포함 |
| frozen 외부 process health/static/재기동 | 2회 health/identity/static HTTP 200, stdin EOF exit 0 | marker-owned 시험 SQLite, head `20260912_0004`, CPU 6/대사 144/CG metadata 슬롯 18; media 이미지 없음 |
| Chromium 확보 | exit 1, ZIP central-directory 오류 재현 | Linux browser 4개 미재실행. Windows 결과와 별개 |

Windows: GitHub hosted Windows Server 2022 Datacenter x64, build 20348.
Python 3.12.10 / Node 24.19.0. W01 Linux 3.12.14와 patch가 다르다. setup-python이
Windows 3.12.14를 제공하지 않아 공식 Windows binary가 있는 3.12.10으로 격리 시험했다.
security-only patch를 어떤 Windows binary 공급 경로로 유지할지는 W03/W12 결정 조건이다.
명령 전문은 workflow와 [spike 실행법](spikes/w02/README.md)에 있다. build 전용 venv의
pip install report, resolved freeze, Windows wheel SHA256, browser/source/frozen 로그 및
ZIP/hash/native data inventory/renderer evidence를 Actions artifact에 수집한다(14일 보존).
Python 범위 의존성은 미래 build 해석/byte 일치까지 보장하지 않는다.

### Windows 정확한 SHA·artifact·결과

실행 code SHA `a9268d4b3b5eed3b55b8b40e2f06bbf28a549cb5`,
[push CI 38567208066](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38567208066) **전체 success**.
[artifact 11896177779](https://github.com/danhk0612/no-riichi-no-fuku/actions/runs/38567208066/artifacts/11896177779)
`w02-windows-a9268d4b3b5eed3b55b8b40e2f06bbf28a549cb5`, 2026-10-28 만료.
다운로드한 evidence/source-sha·로그·내부 ZIP·metadata와 대조했다. 문서 후속 commit은 Git/PR로
찾으며, 이 code SHA의 spike/workflow/backend/frontend tree가 같을 때만 위 결과를 이어받는다.

| Windows 검사 | 실측 결과 | 범위/제한 |
|---|---|---|
| 선언 의존성·wheelhouse | pip report/freeze/hash 확보, `--no-index --force-reinstall` exit 0 | 격리 venv. 장기 완전 lock/byte 재현과 별개 |
| source unittest / 대사 pytest | 72개/50.665초, 10개/0.13초, exit 0 | UTF-8 모드. policy 1/2/legacy 및 기존 정산/복구 포함 |
| frontend npm ci/build | 각 exit 0 | 원본 product lock/build |
| 기존 browser 4개 | 모두 exit 0 | routed 대사/연결/CG 3개 + 실제 Vite/FastAPI/SQLite 108행동·12행동 후 API 재시작·완료 재접속. W01 Linux 차단이 해결됐다는 뜻은 아님 |
| Windows ZIP 압축 해제 | 한글/공백 `W02 압축 해제` 경로 통과 | 테스트 전용 unsigned ZIP, ASAR 밖의 native engine |
| frozen regression | 72개/51.046초, 10개/0.14초, exit 0 | 추출한 w02-engine.exe, PATH=System32 / PYTHONHOME·PYTHONPATH 비움. 설치된 Python/Node가 없는 clean PC 실기와 별개 |
| Electron same-origin 대국 | `passed=true`, 실제 renderer REST/WS 108행동 | Electron 44.7.2 / Chromium 152.0.7977.149 / 내부 Node 24.21.0. 외부 build Node 24.19.0과 구분 |
| 저장/복구 | 12행동 후 전체 authoritative turn 동일; 완료 재기동 응답·DB 불변 | seed 5/stage 2 시험 주입, policy 2, 점수 `[17000,27700,24700,30600]`, 순위 `[4,2,3,1]`, HP 3→2/stage 유지 |
| ready·포트·소유 종료 | 충돌 WinError 10048/exit 1 거절, unrelated listener 유지; 정상 3회 exit 0/forced=false | 초기 ready 1804ms, 재기동 1163/1156ms; stdin EOF 종료 419/374/303ms. 단일 hosted runner 표본, Windows 사용자 X 클릭 실기/host crash와 별개 |
| 인터넷 | OS 인터넷 차단하지 않음 | renderer non-loopback 차단만 시험. 물리적 오프라인은 사용자 결과 필요 |

`W02-Spike.zip` 205,983,766 bytes(약 196.44 MiB), 압축 해제 478,215,857 bytes,
시험 engine subtree 93,506,175 bytes. pytest/test helper와 넓은 dependency 수집을 포함하므로
제품 최소 용량·성능 추정치로 쓰지 않는다. CPU/RAM 사용량·사용자 PC 속도는 미측정이다.
ZIP SHA256 `313fbd046c006057ea0589b7b4bcb72be4cbd8487eb0426c561d7319f37d4990`;
Actions 바깥 artifact ZIP SHA256 `3dd93a9e455db12e57dcc57253fb0fbd40aa1d35fd4951fea268c50a35b66427`.
내부 ZIP의 Python312/VCRUNTIME140/VCRUNTIME140_1 DLL·RiichiEnv pyd·seed 두 JSON·migration
0001~0004를 확인했다. bootstrap 첫 실행 CPU 6/대사 144/슬롯 18, 재기동 추가 0.
사용자 DB/state 파일은 ZIP에 없고 CG 이미지 생성도 없다.

Git legacy fixture 원본 hash는 보존됐다. Windows checkout의 CRLF 변환으로 ZIP 내 fixture raw
SHA256은 `a6bac607e43bb379abc200a0091cb5ca7c0fc5819bf542647a2fe43b6ae3964c`이다.
313개 CRLF를 LF로 돌리면 원본 blob과 byte 전체가 동일하며 hash `b5144742...`가 일치한다.
기존 108-turn legacy replay 검사도 통과했다. fixture를 현재 정책으로 재생성한 것이 아니며,
Windows artifact의 raw byte hash를 Linux/Git LF hash와 직접 동일하다고 주장하지 않는다.

### 번들·native 조건

- PyInstaller onedir 후보는 `app` import path를 빌드 process의 PYTHONPATH로 지정하고
  testclient/namespace test helper를 명시 수집한다. frozen 런타임은 외부 Python/PYTHONPATH를
  사용하지 않는다. 첫 Linux frozen 시험에서 dynamic import 누락 3개가 있었으며 수집 보완 후
  위 72+10 통과를 확인했다. 오류를 제품 결함 또는 통과 결과로 숨기지 않는다.
- Windows 기본 cp1252에서는 legacy fixture의 encoding 없는 read_text가 실패했다:
  source 72개 중 71개 통과/1 UnicodeDecodeError. 원본 fixture·검사를 그대로 보존하고
  source `PYTHONUTF8=1`, frozen `--python-option 'X utf8'`를 spike에서 지정한다.
- RiichiEnv Windows wheel `riichienv-0.4.8-cp312-cp312-win_amd64.whl` SHA256은
  `50783478d424b0c6f9271bc153e01dc05eff64636be5e0ef4ea10f4e6fd60cd3`.
  Windows wheelhouse hash 및 Linux에서 cross-target 설치한 wheel tag/PE x64를 대조했다.
  `_riichienv.cp312-win_amd64.pyd`의 objdump import: `python312.dll`, `VCRUNTIME140.dll`,
  `bcryptprimitives.dll`, `KERNEL32.dll`, `ntdll.dll`, synch/UCRT math/runtime/heap API sets.
  wheel은 별도 DLL 없이 pyd를 포함하고 PyYAML/IPython을 선언한다. wheel 존재/PE 분석과
  clean Windows의 DLL 로딩 성공은 다르다. Python/C runtime bundle 및 OS 제공 DLL 경계를
  inventory와 실제 실행으로 확인하고 임의 시스템 DLL 복사는 하지 않는다.
- seed JSON·Alembic ini/env/version 0001~0004·원본 legacy fixture·React build를 같은 bundle에
  넣는다. REST/WS와 health는 기존 코드, static mount/port/identity/stdin 수명은 spike만 추가.
  pytest/test helper를 포함한 **시험 번들 크기는 제품 최소 번들 크기가 아니다**.

### 미검증과 재개 조건

실행·지원 OS·저장/인증·배포 방식은 미채택이다. Windows 10/11의 Python 미설치 PC,
OS 수준 인터넷 차단, 사용자 눈으로 UI 종료/재실행, 외부 VC runtime 부재, host 강제 종료/
전원 차단, 동시 writer/FK/durability, WebView2/Tauri/.NET 실행은 미검증이다.
renderer 외부 요청 차단과 PATH 제거는 각각 OS 인터넷 차단/깨끗한 PC와 구분한다.
기존 Windows 사용자 DB·미디어를 시험에 연결하지 않는다. W04 저장 보장·W05 host 통합·
W12 권리/고지/서명·설치형 준비는 본 spike의 통과로 완료하지 않는다.
사용자 결과는 PR #59 또는 Work에 `w02-user-evidence.json`과 OS/하드웨어/Python 미설치/
인터넷 차단 방식·화면 종료 여부를 첨부한다. DB/state 파일은 비밀값이 있어 첨부하지 않는다.

## W01 실행 검증 및 재현

모든 아래 검사는 baseline `5762267e2366fa5bdbdd69bc6f38672d141dcbc8`에서 실행했다.
환경은 Ubuntu 24.04.3 / Linux 6.18.44 x86_64, Python 3.12.14, uv 0.12.23,
Node 24.19.0 / npm 11.9.0이다. 프로젝트 자체 패키지를 설치하지 않고 선언 의존성만 임시 venv에
설치하고 backend 작업 디렉터리에서 app을 import했다. editable 설치는 W00에서 실패한
app/alembic flat-layout 자동 탐색 문제를 그대로 인계하며 W01에서 재시도/수정하지 않았다.

주요 실제 설치 버전: RiichiEnv 0.4.8, FastAPI 0.143.0, Starlette 1.8.0,
SQLAlchemy 2.1.4, Alembic 1.20.0, Uvicorn 0.54.0, psycopg/binary 3.3.6,
Pydantic 2.14.1 / settings 2.15.0, httpx 0.28.1, PyJWT 2.15.1,
argon2-cffi 25.1.0, python-multipart 0.0.32, websockets 17.2.
pytest 9.1.1은 기존 함수 검사 실행용으로 임시 venv에만 추가했다.
frontend lockfile 기준 React/ReactDOM 19.3.0, TypeScript 7.0.2, Vite 8.3.0,
plugin-react 6.1.1, React/ReactDOM types 19.3.0이다.
Python 범위 의존성은 lock되지 않았으므로 동일 명령의 미래 해석 결과까지 고정된 것은 아니다.

```sh
# 저장소 루트에서 시작; 전용 임시 환경이며 사용자 DB/미디어 사용 없음
uv venv /tmp/nrnf-w01-verify
cd backend
uv pip install --python /tmp/nrnf-w01-verify/bin/python -r pyproject.toml --extra test
/tmp/nrnf-w01-verify/bin/python -m unittest discover -s tests -v
uv pip install --python /tmp/nrnf-w01-verify/bin/python pytest
/tmp/nrnf-w01-verify/bin/python -m pytest tests/test_dialogue_service.py -v
cd ../frontend
npm ci
npm run build
```

| 검사 | 이번 결과 | 보장 범위/제한 |
|---|---|---|
| backend unittest | **72개 통과**, 32.760초, exit 0 | 실제 엔진·SQLite 메모리 DB·TestClient/ASGI 및 stub/mock. pytest 함수는 수집하지 않음 |
| 대사 pytest | **10개 통과**, 0.09초, exit 0 | 기존 선택/추출/확률/cooldown 검사. 실제 브라우저 표시와 별개 |
| npm ci / build | **각 exit 0** | TypeScript 및 Vite production build; 실행 배포/Windows 증거는 아님 |
| routed browser 3개 | **각 exit 1 / 환경 차단** | Chromium launch 실패, DOM assertion 미실행 |
| live-game browser | **exit 1 / 환경 차단** | 임시 SQLite Alembic head/bootstrap, API health·Vite 준비까지 진행. Chromium launch에서 중단; 회원가입·대국·12행동 후 재시작·정산 비교 미실행 |

브라우저 재현에 사용한 명령(Playwright는 저장소 밖 runtime의 1.62.1):

```sh
# frontend에서 별도 터미널; live-game은 자체 서버를 사용
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
export PLAYWRIGHT_MODULE_PATH=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright
node tests/dialogue.browser.mjs
node tests/connection.browser.mjs
node tests/result-asset.browser.mjs
TEST_PYTHON=/tmp/nrnf-w01-verify/bin/python node tests/live-game.browser.mjs
# Chromium 확보 시 위 명령에 TEST_CHROMIUM_EXECUTABLE=/실제/실행파일 사용 가능
```

네 검사 모두 `chromium_headless_shell-1234/.../chrome-headless-shell` 실행 파일 부재다.
`node "$PLAYWRIGHT_MODULE_PATH/cli.js" install chromium`도 시도했지만 Chrome for Testing
151.0.7922.34 ZIP의 `End of central directory record signature not found` 이후 다운로드 실패
(exit 1)했다. 원격 응답 오류의 원인은 확정하지 않는다. 정상 Chromium을 제공한 환경에서
[기존 실행법](frontend/tests/README.md)대로 4개를 다시 실행해야 한다. live-game은 포트 8000/5193을
독점 사용하고 자신의 임시 DB·프로세스를 정리했다. 별도 Vite도 종료했다.

Windows EXE/번들, 인터넷 차단 실행, ComfyUI/StabilityMatrix, Docker/nginx/PostgreSQL,
실제 CG 디코딩, 전원 차단/SIGKILL, 복수 worker·동시 요청은 이번에 미검증이다.
W01 당시 Actions workflow가 없었으므로 위 W01 결과에 CI 통과를 주장하지 않는다.

## 보존 불변조건과 코드 → 검사 대응

경로는 backend의 경우 `backend/app/`, 검사는 `backend/tests/` 기준이다.
아래 통과는 unittest/대사 pytest에 한정한다. browser는 코드 대조만 했고 이번 미검증이다.

| 보존 영역 | 실제 코드 | 기존 대응 검사와 보장 한계 |
|---|---|---|
| 규칙·합법행동 | [adapter](backend/app/mahjong/riichienv_adapter.py), [session](backend/app/mahjong/session.py) | [test_riichienv_session](backend/tests/test_riichienv_session.py): pending 좌석 전체 행동 요구, 불법 행동/index 거절·상태 불변, 4좌석 동풍전 완료. RiichiEnv 0.4.8 / `4p-red-east` / Tenhou 기본값 유지; 역·부·동점·유국 전체를 독립 대조한 검사는 아님 |
| stage→Tier·CPU 성향 | [game_setup](backend/app/services/game_setup.py), [Tier0](backend/app/mahjong/tier0.py) / [Tier1](backend/app/mahjong/tier1.py) / [Tier2](backend/app/mahjong/tier2.py) | [setup](backend/tests/test_game_setup.py), [Tier0](backend/tests/test_tier0_agent.py) / [Tier1](backend/tests/test_tier1_agent.py) / [Tier2](backend/tests/test_tier2_agent.py), [personality](backend/tests/test_personality_integration.py), [tournament](backend/tests/test_tournament_simulation.py): stage 0/1/2, seed 결정성·합법 선택·대국 완료·성향 일부 평가. 모든 성향이 선택을 변화시킴 또는 Tier 강도 단조 증가를 증명하지 않음 |
| HP/stage·진행 경계 | [game_result](backend/app/services/game_result.py), game_setup, [결과 UI](frontend/src/game/MahjongTable.tsx) | [test_game_result](backend/tests/test_game_result.py): 사람 4위만 HP -1, CPU 4위만 매핑된 progress +1, 미완료/HP 0/완료 CPU 거절. setup: stage 2→3 완료 제외, 서로 다른 활성 CPU 3명·HP 필요. [dialogue.browser](frontend/tests/dialogue.browser.mjs): 결과 loop/game over UI fixtures(이번 미실행). CPU 부족 이후/HP 회복 정책은 D04 미확정 |
| 정산 exactly-once | [registry](backend/app/services/game_registry.py), [game API](backend/app/api/game.py), game_result | [test_game_websocket](backend/tests/test_game_websocket.py)의 `test_restart_after_final_action_before_settlement_settles_once`, `test_fixed_seed_match_completes_and_persists_server_settlement` 및 result 중복 검사: 최종 행동 commit 후 미정산 복구, 완료 재접속·HP/stage 중복 방지. 행동 commit과 완료·진행 정산 commit은 **별도 transaction**이며 결과/HP 또는 stage는 정산 transaction에 함께 저장됨 |
| 저장·복구·접속 | registry, game API, [record](backend/app/db/models/game_session_record.py), [프런트 연결](frontend/src/main.tsx) | websocket의 `test_persisted_action_restores_same_turn_with_fresh_registry`, `test_stale_action_is_rejected_and_latest_turn_is_resent`, `test_failed_action_commit_recovers_only_persisted_turn`: DB 행동까지 동등 복구, 과거 이벤트 비전송, stale/commit 실패 rollback 후 cache 제거. 단일 active/소유자 검사도 통과. [connection.browser](frontend/tests/connection.browser.mjs), [live-game](frontend/tests/live-game.browser.mjs)은 각각 routed 복귀/실제 process 재시작용(이번 미검증) |
| 대사 독립성 | [dialogue_service](backend/app/services/dialogue_service.py), game API/session | [test_dialogue_service](backend/tests/test_dialogue_service.py) 10 pytest: 활성/누락·CPU 이벤트·깡/론/쯔모·확률/cooldown. 별도 대사 RNG를 CPU RNG에 합치지 않음. chi 단독 매핑 assertion/모든 실제 이벤트 end-to-end는 별도 보강 조건 |
| CG 실패와 정산 분리 | [result_assets](backend/app/services/result_assets.py), game API, main.tsx/MahjongTable.tsx | [test_result_assets](backend/tests/test_result_assets.py): 권한/해금·교체/삭제·형식/크기, 임시 metadata byte fixture 사용(실제 이미지 생성 없음). websocket: 결과 metadata/대사. [result-asset.browser](frontend/tests/result-asset.browser.mjs): HTTP 503에도 순위/다음 선택 유지, 늦은 실패 차단(이번 미실행). 성공 응답 후 이미지 디코딩 실패·ComfyUI 실패 검사는 아님 |

### policy 1/2 및 legacy replay 보존

- 새 선택/snapshot은 `policy_version=2`; `CpuChoice` 기본값 1이 버전 없는 기존 DB snapshot을
  복원한다. 새 기본값으로 오래된 snapshot을 다시 저장하거나 현재 CPU DB 값으로 치환하지 않는다.
- Tier2 policy 1은 기존 `round_wind == 0` 분기를 그대로 재현하고, policy 2는 동4 및 남장 연장
  (`round_wind > 0 or kyoku_index >= 3`)을 종반으로 판단한다.
  `test_endgame_round_boundary_and_legacy_policy` / `test_real_engine_east_and_sudden_death_rounds` 통과.
- 저장된 match seed, CPU 선택 순서/좌석 1·2·3, stage와 여섯 성향 snapshot, policy,
  CPU seed `match_seed * 10 + seat`, 사람 합법행동 index/순서를 유지한다.
  RiichiEnv 버전·합법행동 순서·agent RNG 소비 변경은 replay 호환 변경으로 취급한다.
- [legacy fixture](backend/tests/fixtures/tier2_legacy_replay.json)는 원본 `e357c01`, seed 5,
  stage 2 CPU 3명, policy 필드 누락, 108행동이다. 파일 SHA256:
  `b51447422f5522d4c16e0bab0aa27cfabe90c5923018cf583411d39e478ce64e`.
  `test_legacy_tier2_snapshot_replays_every_original_turn`이 매 턴 hash와 12행동 후 registry 교체,
  최종 재생을 확인했다. 점수 `[17000,27700,24700,30600]`, 순위 `[4,2,3,1]` 일치.
  [원본 계약](backend/tests/fixtures/README.md)대로 현재 policy로 fixture를 재생성하지 않는다.
- policy 2는 `test_new_tier2_policy_survives_registry_restart`에서 1행동 복구를 검사했다.
  전체 대국·12행동 후 실제 API 재시작·완료 재접속은 live-game 검사 영역이며 이번 미검증이다.
- UI/이미지·대사 RNG와 생성 요청은 엔진 행동 log/CPU RNG/정산에 끼워 넣지 않는다.
  완료 record의 결과/정산과 replay에서 소비한 과거 이벤트 비전송도 보존한다.

## 새로 확인한 검증 누락과 후속 조건

제품 결함을 새로 확정하거나 수정하지 않았다. 다음은 현재 검사의 한계이며 해당 후속 Task에서 다룬다.

- **검사 수집:** 기존 unittest 72개는 pytest 대사 함수 10개를 포함하지 않는다.
  `pyproject.toml` test extra에도 pytest가 없다. 후속 검증 환경은 두 명령과 pytest 설치를 명시해야 한다.
  의존성/CI 변경은 이번 범위 밖이며 별도 허용 범위에서 처리한다.
- **복구/정산:** 행동 commit 실패 회귀는 있으나 정산 commit 자체의 실패 주입/재시도,
  실제 동시 socket/writer·중복 프로세스, SQLite FK 적용·잠금/전원 차단 durability는 보장되지 않는다.
  W04는 저장 계약 결정 후 이를 검증해야 한다. 메모리 DB `create_all` 통과와 migration/Windows 저장을 혼동하지 않는다.
- **CPU/규칙:** 일부 성향 검사는 파라미터 저장/선택 non-null만 확인한다. 소규모 tournament는
  Tier 강도 순서 보장이 아니다. 엔진 교체·CPU 튜닝 시 독립 규칙/행동·통계 증거가 추가로 필요하다.
- **CG:** HTTP 503/늦은 실패 fixture와 실제 이미지 디코딩 실패는 다르다. 현재 `<img>`에는
  onError 대응이 없으므로 성공 HTTP 뒤 디코딩 실패 표시는 별도 확인/수정 Task가 필요하다.
  W10/W11의 생성 실패 독립성은 아직 구현·검증하지 않았다.
- **실기:** Chromium 확보 후 기존 browser 4개 재실행; Windows 런타임/번들 증거는 W02에서
  별도 확보한다. W01 환경 차단을 제품 오류나 Windows 성공으로 해석하지 않는다.

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
2. **실행:** 제품 Windows shell·기동/종료 관리는 없다. W02 격리 후보와 Windows 실행 증거는
   위 별도 기록이며 W03 채택·W05 통합·W12 정식 배포를 완료한 것이 아니다.
3. **저장:** SQLite 시험 성공과 제품 전환은 다르다. PostgreSQL 행 잠금/환경·웹 인증·
   `/data/media` 경로와 bootstrap을 Windows 실행 조건에 맞춰 검증해야 한다.
4. **콘텐츠:** 공유 Level별 프롬프트·후보·상황/대사 관계·변수·ComfyUI 연결·생성 캐시 미구현.
5. **문서:** 기존 docs에는 초기 목표 트리, Tier 1/2 미구현 등 시점별 서술과 Docker 완료/보류
   서술이 함께 있다. 루트 기준 문서가 현재 인계점이다. 과거 증거 본문은 보존한다.
   CPU 난이도 순서가 확실히 검증됐다는 결론도 금지: 최신 정책의 고정 표본은 작다.

## 다음

W04의 이름 저장·capability 정상 거절·local 전용 쓰기/기본 engine 읽기·파일 DB 정산 실패
복구 보완은 완료했다. 다음 Task는 W05 Windows shell·로컬 runtime·같은 origin UI 통합이다.
TASKS의 다음 Work 지시문으로 최신 main에 PR #61이 반영됐는지 확인하고 저성능 Work에서 진행한다.
지원 OS/Python 공급·실제 clean PC/OS 오프라인·전원 차단은 남은 검증이며 완료로 올리지 않는다.
