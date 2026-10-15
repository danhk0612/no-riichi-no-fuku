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
| W04 | 로컬 저장·복구 기반 전환 | P0 / 보완 코드·Linux/Windows CI 통과, PR #61 병합 대기 | W03 | 저성능 Work (구조 설계 필요 시 고성능 Work) |
| W05 | Windows shell·오프라인 게임 통합 | P0 / 대기 | W04 | 저성능 Work |
| W06 | 진행 규칙 결정·게임 회귀 | P0 / 결정 대기 | W05, D04 | 고성능 Chat → 저성능 Work |
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

### W06 — 진행 규칙 결정·게임 회귀

- 목적: CPU 부족으로 전체 완료 불가능한 진행 경로 및 HP 0 이후를 사용자 결정대로 처리.
- 범위: 먼저 D04 결정; 결정된 최소 진행 코드/화면/검사, Windows 대국·Tier·성향·정산·복구 회귀.
- 선행: W05 및 D04. 결정 전 기존 선택 제외/인원/HP 정책 유지.
- 완료: 합의한 전체 완료/부족 CPU/게임 오버 경로와 일반 대국 회귀 통과, 기존 세션 호환.
- 금지: 미승인 filler/완료 CPU 재선택/인원 변경/HP 회복, 이미지 Level 자동 대응, CPU 튜닝.
- 환경: 정책은 고성능 Chat, 확정 구현은 저성능 Work.

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

## W04 PR #61 보완 지시문 — 현재 우선 작업

검토 head: `70c6d8bdc031803a713a324889e2f241c95750ac`. 기존 Windows CI와 78 unittest/10 pytest
성공 이력은 유효한 수행 결과지만, 아래 재현 결함을 보장하지 않는다. 이 절이 W05 인계보다 우선한다.

1. **이름 저장:** local authenticate/local_user가 expunge한 detached User를 반환해 PATCH는
   성공처럼 보이나 DB에 저장되지 않는다. 요청에서 사용하는 같은 session의 User를 반환하도록
   local dependency 경계를 최소 수정한다. 웹 profile endpoint/웹 인증 동작은 유지한다.
   PATCH→다음 HTTP GET→별도 DB 조회→runtime 재시작 후 이름 동일성을 검증한다.
2. **인증 거절:** hmac.compare_digest에 non-ASCII str을 전달하면 TypeError다. 로컬 capability
   검증을 REST/member/admin 및 WS에서 일관되게 처리해 malformed/비ASCII/누락/이전 실행
   토큰은 정상 거절되게 한다. REST 오류 상태와 WS 오류/close code까지 검사하며 secret을 노출하지 않는다.
3. **읽기/쓰기 transaction 경계:** 공통 engine begin event가 조회에도 BEGIN IMMEDIATE를
   발행한다. local runtime에서만 쓰기 의도를 명시해 쓰기 transaction을 읽기 전에 직렬화하고,
   단순 조회는 writer 예약 잠금을 점유하지 않게 한다. 웹용 기본 engine의 기존 transaction
   의미를 바꾸지 않는다. SQLite FK·active index·소유 잠금과 rollback/cache eviction은 보존한다.
   로컬 REST의 인증 조회/이름 수정이 별도 session으로 서로 잠금을 걸지 않게 한다.
   WS의 실제 행동/정산과 admin 쓰기도 같은 local 쓰기 규칙에 포함한다.
   기본 engine 및 local의 동시 읽기, local 동시 active-session 쓰기/stale action을 검증한다.
4. **정산 실패 검증:** 파일 SQLite local runtime에서 정산 commit에만 실패를 주입한다.
   최종 행동 commit은 남고 HP/stage/완료 결과가 rollback되며 cache가 제거되는지 확인한다.
   새 runtime/재접속 후 정확히 한 번 정산하고, 반복 재접속에서도 같은 결과가 보존돼야 한다.
   실패 주입을 마지막 행동 전 실패나 기존 in-memory 검사로 대체하지 않는다.

변경 범위는 W04의 local runtime/dependency·transaction 경계와 필요한 회귀 검사다.
새 프레임워크/저장 기능·W05 UI/host·CPU/룰/진행 정책·이미지·기존 자료 변경은 포함하지 않는다.
현재 main의 검토 문서를 반영할 때 기존 PR/기능·검증 이력을 덮어쓰지 않는다.
수정 후 기존 전체 unittest/대사 pytest·영향 build 및 정확한 수정 SHA의 Windows CI를 검증하고
artifact의 source SHA/실행 결과를 대조한다. CURRENT_STATE/ARCHITECTURE/TASKS는 실제 결과로
최소 갱신하되 미검증을 완료로 바꾸지 않는다. 기존 PR #61에 보완 commit을 올린다.

## 다음 Work에 입력할 지시문

```text
https://github.com/danhk0612/no-riichi-no-fuku 의 최신 main과 기준 문서를 확인하고,
TASKS.md의 “W04 PR #61 보완 지시문 — 현재 우선 작업”을 수행해.

기존 task/w04-local-storage 브랜치와 PR #61을 유지해.
이름 편집의 DB/재시작 보존, malformed capability 정상 거절,
local 전용 쓰기 transaction과 동시 읽기 경계, 파일 DB 정산 commit 실패 복구를 보완해.
기존 78 unittest/10 pytest·Windows CI 성공 이력과 W03 계약을 보존해.
정확한 수정 SHA의 Windows CI·artifact를 확인하고 기존 PR과 기준 문서를 갱신해.
branch push·PR 갱신·필요한 CI는 허용한다.
직접 병합·Release/tag·W05 착수·범위 밖 제품/게임 규칙 변경은 하지 마.
```

권장 환경: **저성능 Work**. 검토에서 확정한 W04 결함·transaction 경계 보완과 회귀 검증이다.
계약 자체의 변경이 필요하면 해당 부분만 고성능 Work/Chat으로 분리한다.
