# Repository Agent Instructions

이 저장소에서 작업하는 개발 에이전트는 작업 전 반드시 다음 문서를 순서대로 확인한다.

1. `README.md`
2. `docs/PROJECT_PLAN.md`
3. `docs/WORK_INSTRUCTIONS.md`
4. `docs/DECISIONS.md`
5. `docs/WORK_START.md`

핵심 원칙:

- GitHub의 현재 코드를 source of truth로 사용한다.
- 요청된 범위만 수정한다.
- 4인 일본 리치마작 동풍전, 사람 1명 + CPU 3명 구조를 유지한다.
- 게임 상태와 규칙의 최종 판정은 서버가 담당한다.
- CPU 마작 판단에 외부 LLM/API를 사용하지 않는다.
- 캐릭터 성향과 CPU 난이도를 분리한다.
- CPU가 동풍전 최종 4위일 때만 해당 사용자 기준 `defeat_stage`를 1 올린다.
- 플레이어가 최종 4위일 때만 HP를 1 줄인다.
- `defeat_stage == 3`인 CPU는 이후 선택할 수 없다.
- CG 파일/더미 CG/성인 이미지는 Git 저장소에 생성하거나 커밋하지 않는다.
- 미디어는 런타임 persistent volume + DB metadata 방식으로 관리한다.
- 최고 관리자 초기 ID/암호는 환경변수로만 주입하고 최초 로그인 후 비밀번호 변경을 강제한다.
- 새 GPL/AGPL 의존성이 핵심 기능에 결합되면 라이선스 호환성을 검토하고 필요 시 프로젝트 라이선스도 전환한다.
- 완료 전 diff와 관련 테스트를 확인한다.

상세 규칙은 `docs/WORK_INSTRUCTIONS.md`가 우선한다.
