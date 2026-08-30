# No Riichi No Fuku

`No Riichi No Fuku`는 웹 기반 1인용 4인 일본 리치마작 게임 프로젝트입니다.
플레이어 1명과 선택한 CPU 캐릭터 3명이 동풍전을 진행하며, 최종 4위 결과에 따라 캐릭터 진행도 또는 플레이어 HP가 변화합니다.

## 현재 단계

프로젝트 부트스트랩과 RiichiEnv 0.4.8 스파이크를 마쳤으며, 인증·회원 프로필과
최고 관리자용 회원/CPU/대사 관리 API, RiichiEnv adapter와 서버 권한형 게임 세션
기초, 최소 React 마작 테이블 UI와 production Tier 0 CPU를 구현한 단계입니다.

## 핵심 규칙

- 웹 기반 회원가입 및 로그인
- 회원 프로필: 플레이어 이름, 프로필 이미지, HP
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

## 초기 기술 스택

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Python
- Mahjong engine: RiichiEnv
- Database: PostgreSQL
- Realtime game communication: WebSocket
- Deployment: Docker Compose
- Runtime media: Docker persistent volume

## CPU 방향

외부 LLM/API를 사용하지 않습니다. CPU는 서버 내부의 공통 의사결정 엔진으로 구현하고, 캐릭터 패배 단계에 따라 난이도를 높입니다.

- Stage 0: 기본 패효율 중심
- Stage 1: 패효율 + 기본 수비/타점 판단
- Stage 2: 공수 판단 + 위험도 + 순위/점수 상황 판단
- Stage 3: 최종 완료 상태, 선택 불가

CPU 캐릭터의 플레이 성향과 난이도는 분리합니다.

## 문서

- [프로젝트 계획](docs/PROJECT_PLAN.md)
- [Work 개발 지침](docs/WORK_INSTRUCTIONS.md)
- [첫 Work 시작 절차](docs/WORK_START.md)
- [아키텍처](docs/ARCHITECTURE.md)
- [오픈소스/라이선스 검토](docs/OPEN_SOURCE_REVIEW.md)
- [초기 결정 및 미확정 사항](docs/DECISIONS.md)

## 개발 환경

초기 Docker 골격을 기준으로 다음 명령을 사용합니다.

```bash
cp .env.example .env
# .env의 DB/최고관리자 초기 암호를 변경
docker compose up --build
```

현재 API는 health check, 인증·회원 이름 프로필, 최고 관리자용 회원/CPU/대사 관리를
제공합니다. 마작 게임 기능과 프론트엔드 화면은 계획서의 단계 순서에 따라 구현합니다.

## 라이선스

현재 프로젝트 자체 코드는 MIT License로 시작합니다.

RiichiEnv는 Apache-2.0 의존성으로 사용합니다. 추후 Mortal 등 AGPL/GPL 코드를 프로젝트에 결합해야 하는 경우, 결합 방식과 라이선스 조건을 확인하고 해당 변경과 동시에 프로젝트 라이선스를 호환되는 GPL/AGPL 계열로 변경합니다.
