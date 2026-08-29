# Initial Decisions

## 확정

- 게임명: No Riichi No Fuku
- 웹 기반
- 간단 회원가입/로그인
- 회원 프로필 이름/이미지는 계정 데이터로 유지
- 1인 플레이
- 플레이어 1 + CPU 3
- 4인 일본 리치마작
- 동풍전
- 매 대국 시작 전 CPU 3명 재선택
- 좌석별 프로필/이름/점수 등 표시
- CPU 프로필 클릭 시 상세 정보
- 주요 상황 말풍선/대사
- CPU 4위 시 해당 CPU `defeat_stage + 1`
- `defeat_stage` 증가에 따라 CPU 난이도 증가
- 3회 패배 CPU는 최종 완료 후 선택 불가
- 플레이어 4위 시 HP -1
- HP 0이면 게임 오버
- CPU 4위 종료 시 단계별 CG + 결과 대사
- 최고 관리자 1종
- 최고 관리자 최초 비밀번호 변경 강제
- 최고 관리자에서 회원/CPU/대사/CG/기본 설정 관리
- Docker 기반
- CG 파일은 Git 저장소에 만들거나 커밋하지 않음
- 기본 CPU seed 몇 명 포함
- 초기 CPU 판단에 외부 LLM/API 사용 안 함

## 초기 기술 결정

- React + TypeScript + Vite
- FastAPI + Python
- PostgreSQL
- WebSocket
- RiichiEnv 0.4.8 1차 엔진 후보
- 초기 프로젝트 라이선스 MIT
- GPL/AGPL 핵심 소스가 필요해지면 프로젝트 라이선스도 호환 계열로 전환

## 명시적 초기 가정

세부 룰이 아직 지정되지 않았으므로 첫 통합 기준은 다음을 후보로 둔다.

```text
RiichiEnv game_mode = 4p-red-east
Tenhou 계열 기본 규칙
```

**주의:** 정확한 생성자/Rule API는 RiichiEnv 0.4.8을 실제 설치한 첫 Work 스파이크 결과로 확정한다. 문서 예시를 코드보다 우선하지 않는다.

## 아직 결정하지 않음

- 최대 HP 실제 값
- 게임 오버 후 진행 초기화/재시작 정책
- 최종 전체 완료 후 엔딩 처리
- CG 실제 이미지/연출
- 캐릭터 최종 이름/설정/프로필 이미지
- Mortal 사용 여부
- 동풍전 세부 종료/연장/동점 순위 규칙
