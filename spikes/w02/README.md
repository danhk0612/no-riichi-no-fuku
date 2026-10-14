# W02 Windows runtime spike — 제품 아님

기준 제품 `7523d4177140d303c5f4681c5ff94d92610db227`을 변경하지 않고 실행 후보를 검증한다.
Python 3.12.10 x64 / RiichiEnv 0.4.8 / PyInstaller 6.22.3 onedir / Electron 44.7.2 후보다.
W01 Linux 3.12.14와 patch가 다르다. Windows Actions가 3.12.14를 제공하지 않아
3.12 계열의 공식 Windows binary가 있는 3.12.10을 격리 시험 후보로 사용한다.
지원 OS·저장·프로필·인증·배포 방식은 W03 미확정이다. 이 폴더를 제품 entry point로 쓰지 않는다.

## Windows 실측·결과 수집 경로

[W02 Actions](https://github.com/danhk0612/no-riichi-no-fuku/actions/workflows/w02-spike.yml)의
정확한 head SHA 실행에서 `w02-windows-<SHA>` artifact를 받는다(14일 보존, Release/tag 없음).
실행이 차단되면 runner/권한/다운로드 오류를 기록하고 아래 사용자 경로로 재개한다.
artifact 안의 `W02-Spike.zip`은 한글·공백 경로에 압축을 풀어 시험한다.
Python/Node/Docker/PostgreSQL/ComfyUI 설치는 런타임에 사용하지 않는다.
Actions runner에는 Python/Node가 설치되어 있으므로 PATH 제거만으로 깨끗한 PC를 증명하지 않는다.

Windows PowerShell에서 압축 해제 폴더로 이동한 후:

```powershell
# 먼저 인터넷 연결을 끊은 상태에서 실행하고 그 여부를 결과와 함께 적는다.
$env:W02_EVIDENCE = Join-Path (Get-Location) 'w02-user-evidence.json'
$p = Start-Process '.\W02-Spike.exe' -ArgumentList '--smoke' -PassThru -Wait
$p.ExitCode
Get-Content $env:W02_EVIDENCE -Raw
# 눈으로 화면을 확인할 때는 --smoke 없이 실행. 새 임시 폴더에만 저장한다.
$p = Start-Process '.\W02-Spike.exe' -PassThru -Wait
```

`--smoke`는 숨긴 Electron renderer에서 실제 REST/WS 회원가입·Tier2 동풍전 108행동,
12행동 후 엔진 종료/재기동 턴 동등성, 완료 재접속과 DB 정산 불변을 검사한다.
seed 5·stage 2 주입은 marker가 있는 시험 DB에만 한다. DOM 버튼 플레이 검사는 별도다.
포트 충돌을 먼저 주입하고 외부 listener 생존, ready identity/health, owned child의 stdin EOF
종료를 검사한다. 실행 실패도 evidence에 남긴다. 화면은 기존 React production build다.

결과 제출은 **이 작업의 PR에 `w02-user-evidence.json` 첨부** 또는 이 Work 채팅에 첨부한다.
OS 버전/CPU/RAM, Python 미설치 여부, 인터넷 차단 방식, 실행·화면 종료 여부를 함께 적는다.
DB·`w02-state.json`·미디어는 제출하지 않는다(시험 암호/JWT 포함). 임시 폴더는 자동 삭제하지 않는다.
수집 JSON에는 경로·PID·버전·엔진 로그가 있으며 제출 전 개인 경로를 검토한다.

## 재현 build

Windows x64에서 workflow가 정확한 Python/Node 버전을 설치한 뒤 실행하는 명령:

1. `backend/pyproject.toml` 의존성 + test extra + pytest/PyInstaller/setuptools를 별도 환경에 설치.
2. resolved freeze/pip 설치 report/Windows wheel SHA256을 artifact로 보존하고 wheelhouse에서
   `--no-index --force-reinstall`로 다시 설치. 제품 pyproject/lock은 변경하지 않는다.
3. backend에서 `python -m unittest discover -s tests -v`,
   `python -m pytest tests/test_dialogue_service.py -v`.
4. frontend에서 `npm ci`, `npm run build`. 별도 Playwright 1.62.1/Chromium 설치 후
   `python spikes/w02/browser.py`로 기존 browser 4개 재현.
5. `npm ci --prefix spikes/w02`, `python spikes/w02/build.py`.
6. ZIP 압축·한글/공백 경로 해제 후 engine `regression`, shell `--smoke` 실행.

Windows용 build는 Windows에서 한다. Linux build 성공을 Windows 실행으로 바꾸지 않는다.
dependency ranges를 매 build 재해석하므로 **서로 다른 날짜의 build는 byte 재현을 보장하지 않는다**.
이번 run의 freeze/wheel hash와 npm lock으로 해석 결과를 식별한다. 장기 완전 lock·고지·서명·
설치형 패키징은 W12 범위다. 네트워크는 build/download에 필요하다.

## 포함과 경계

- setuptools editable 설치는 app/alembic flat-layout 발견 오류를 재현·기록한다. 제품 수정 없음.
  PyInstaller `--paths backend`/`--collect-all app`으로 소스 import를 명시한다.
- seed JSON은 `app/seeds`, Alembic 설정과 0001~0004는 원래 상대 구조에 포함한다.
  frontend build는 `/`에, 기존 API/WS는 `/api`에 두어 같은 origin을 유지한다.
- Windows 기본 cp1252에서 legacy fixture의 encoding 미지정 `read_text()`가 실패했다.
  원본 fixture/검사는 보존하고 source 시험은 `PYTHONUTF8=1`, frozen interpreter는
  PyInstaller `--python-option 'X utf8'`로 UTF-8 모드를 명시한다.
- RiichiEnv/argon2/psycopg/SQLite/Python native DLL·pyd와 migration/seed 목록을 기록한다.
  frozen unittest/pytest는 native engine·legacy fixture·policy 1/2를 원본 그대로 검사한다.
- 임시 W02 marker 폴더만 DB/미디어 경로로 사용한다. 기존 `.env`나 사용자 폴더를 읽지 않도록
  엔진 cwd를 시험 폴더로 지정하고 환경값을 직접 만든다. 기존 웹 관리자/JWT API를 유지한다.
- renderer Node 비활성/contextIsolation/sandbox, 새 창·외부 navigation 제한,
  non-loopback 요청 차단은 시험 경계다. OS 수준 인터넷 차단 증거와 다르다.
- 임의 포트를 먼저 점유하고 identity/health로 자신의 엔진 준비를 확인한다. ready 파일만으로
  서버 준비 완료를 판단하지 않는다. stdin EOF 종료 + timeout 후 그 child만 kill한다.
- host 강제 종료/전원 차단·중복 instance·악성 loopback client·SQLite writer/FK/durability는
  미검증이다. W03 보안/수명 계약과 W04/W05에서 해결해야 한다.
- WebView2/Tauri/.NET은 비교 대상이며 여기서 빌드하지 않는다. 기술 최종 선택은 W03이다.

소스 LICENSE/THIRD_PARTY_NOTICES와 Electron 배포 폴더의 라이선스는 시험 ZIP에 보존한다.
모든 전이 의존성 고지·재배포 조건의 완전 검토는 아직 아니므로 공개 제품 배포에 쓰지 않는다.
