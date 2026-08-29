# 첫 Work 시작 절차

이 문서는 새 ChatGPT Work에서 이 저장소를 연결한 직후 수행할 첫 개발 순서를 정의한다.

## 0. 시작 조건

대상 저장소:

```text
danhk0612/no-riichi-no-fuku
```

새 Work에서는 GitHub 저장소를 연결한 뒤 다음 문서를 먼저 읽는다.

1. `AGENTS.md`
2. `README.md`
3. `docs/PROJECT_PLAN.md`
4. `docs/WORK_INSTRUCTIONS.md`
5. `docs/DECISIONS.md`
6. `docs/OPEN_SOURCE_REVIEW.md`

## 1. 첫 작업 목표

첫 Work의 목표는 기능을 많이 만드는 것이 아니라 **현재 부트스트랩이 실제 Docker 환경에서 재현 가능하게 실행되는지 검증하고, 이후 마작 엔진 구현을 시작할 수 있는 기준 상태를 만드는 것**이다.

다음 순서로 진행한다.

### A. 부트스트랩 검증

- `.env.example` 검토
- `docker compose config` 검증
- `docker compose build` 실행
- `docker compose up` 후 다음 확인
  - 웹 루트 접근 가능
  - `/api/health`가 nginx를 거쳐 정상 응답
  - PostgreSQL health 정상
- 실패 시 해당 실패 원인만 최소 수정

### B. 백엔드 기반 정리

Docker 검증이 끝난 뒤 필요한 최소 범위만 구현한다.

- 설정 로딩
- DB 연결
- Alembic 초기화
- 최소 모델 설계
  - users
  - cpu_characters
  - user_cpu_progress
  - cpu_dialogues
  - cpu_result_assets metadata
  - game_settings
- 최고 관리자 bootstrap 서비스
- 초기 CPU seed 입력 경로

아직 실제 CG 파일/CG 디렉터리는 만들지 않는다.

### C. RiichiEnv 통합 스파이크

본 기능 구현 전 작은 테스트 코드/테스트로 다음을 확인한다.

- 설치된 RiichiEnv 정확한 버전 출력
- 4인 동풍전 모드 생성 가능 여부
- 사용할 세부 rule API 확인
- 인간 좌석 1 + agent 좌석 3 형태의 제어 가능 여부
- observation / legal action 구조 확인
- 동풍전 한 게임을 CPU-only 테스트로 끝까지 진행 가능 여부
- 최종 scores/ranks 취득 가능 여부

문서에 적힌 API 예시는 가정일 수 있으므로 실제 0.4.8 API를 우선한다.

### D. 결과 기록

검증 결과를 `docs/DECISIONS.md`에 반영한다.

특히 다음을 확정해서 기록한다.

- 실제 사용 RiichiEnv 초기화 코드
- 동풍전 종료 조건
- 적도라 포함 여부
- 연장/서든데스 규칙
- 동일 점수 순위 처리
- CPU agent가 받는 observation 구조

## 2. 첫 Work에서 하지 않는 것

첫 검증 작업에서 아래 기능을 한꺼번에 만들지 않는다.

- 완성형 마작 UI
- 모든 회원/관리자 화면
- CG 업로드 UI
- Mortal 통합
- 캐릭터별 대사 대량 입력
- Tier 1/2 고급 CPU 완성
- 멀티플레이
- 랭킹/과금

## 3. 첫 기능 구현 순서

부트스트랩 및 RiichiEnv 스파이크가 통과하면 이후 작업은 다음 순서를 기본으로 한다.

1. 인증 / 회원 프로필
2. 최고 관리자 + CPU/대사 관리 기초
3. RiichiEnv adapter와 서버 authoritative game session
4. 최소 Mahjong UI
5. Tier 0 CPU 3명 동작
6. 동풍전 완주 및 최종 4위 판정
7. HP / user_cpu_progress 반영
8. CPU 재선택 루프
9. 말풍선/대사
10. 결과 CG metadata 및 관리자 업로드
11. Tier 1 CPU
12. Tier 2 CPU
13. 자동 시뮬레이션 기반 난이도 튜닝

## 4. 새 Work에 처음 전달할 요청문

새 Work를 만든 뒤 저장소를 연결하고 아래와 같이 시작하면 된다.

```text
이 저장소의 AGENTS.md와 docs 문서를 먼저 읽고 프로젝트 기준을 파악해.
docs/WORK_START.md의 첫 Work 시작 절차대로 진행해.
우선 부트스트랩 Docker 실행 검증과 RiichiEnv 0.4.8 통합 스파이크까지 진행하고,
실제 확인된 API/룰 차이는 docs/DECISIONS.md에 반영해.
CG 파일은 생성하지 말고, 요청 범위를 넘어선 기능은 추가하지 마.
```
