# AI 작업·인계 규칙

## 시작

1. 대상 `danhk0612/no-riichi-no-fuku`, remote/branch/worktree 변경과 최신 main SHA를 확인한다.
2. AGENTS, README, PROJECT, REQUIREMENTS, ARCHITECTURE, CURRENT_STATE, TASKS, 이 문서를 읽는다.
3. Task의 선행 조건·승인된 범위·변경 금지·검증 기준을 확인하고 실제 코드/관련 테스트를 읽는다.
4. 문서/코드가 다르면 구현 사실과 목표를 구분해 보고한다. 기존 docs는 필요한 근거만 확인한다.
5. 정책 미확정 부분은 보류하고 독립적인 승인 범위만 진행한다. 과거 채팅을 상태 기준으로 삼지 않는다.

## 작업 환경

| 환경 | 맡길 작업 |
|---|---|
| 고성능 Work | 초기 분석, 복합 구조/데이터 migration, 여러 Task 경계·의존성, 복합 오류 |
| 저성능 Work | 설계가 끝난 명확한 구현·UI/API·회귀 수정·빌드/CI·Git·상태 문서 갱신 |
| 고성능 Chat | 사용자 정책 조율, 좁은 복잡한 판단, 설계 검토, 완성된 작업 지시문 |

높은 성능 자체가 모든 구현을 직접 할 이유는 아니다. 설계 종료 후 반복 구현은
저성능 Work로 인계한다. 같은 기준 문서로 시작하며 환경 전환 시 완료/보류/다음 Task를 남긴다.

## Git 및 범위

- `task/<task-id>-<scope>` 브랜치에서 수행하고 최신 main과 열린 PR/동일 파일 작업을 확인한다.
- 기존 사용자 변경/다른 작업을 덮어쓰지 않는다. 관련 없는 리팩터링·UI·의존성 교체는 포함하지 않는다.
- 사용자 요청과 저장소 정책의 허용 범위에서 commit/push/PR한다. 직접 main 병합·tag·Release는
  그 작업의 명시적 허용 없이 수행하지 않는다. 이번 초기 작업은 문서 branch/PR까지, 병합·배포 제외다.
- 참조 저장소는 조사만 한다. 파일 복사나 새 의존성은 라이선스·유래/고지를 확인한다.
- CG/더미 이미지/사용자 DB/생성물/비밀값은 Git에 넣지 않는다. 합성 테스트 자료도 최소화한다.

## 검증

변경 영향에 맞춰 기존 backend unittest, TypeScript/Vite build와 관련 browser test를 활용한다.
seed/action replay 및 CPU policy 1/2 snapshot을 보존한다. 규칙·CPU·진행·저장 변경은
관련 회귀를 실행한다. 이미지 생성은 별도 mock 계약/실제 로컬 ComfyUI로 나눠 검증한다.
게임이 ComfyUI 없는 상태에서 실행되는 검사를 유지한다.
Linux 개발 성공, CI 성공, 실제 Windows 압축 해제 실행, 전원 차단 보존은 각각 구분한다.
환경 부족 시 미검증으로 남기며 실패를 숨기거나 제품 범위 밖 수정으로 해결하지 않는다.
새 CI 추가는 해당 Task 범위에서 수행한다. W02 전용 `w02-spike.yml`은 격리 Windows
시험/14일 artifact 수집 경로이며 제품 CI·정식 배포가 아니다. 실행 결과는 CURRENT_STATE에 둔다.

현재 검증 시작점(backend 패키지 build 오류가 있으므로 선언 의존성 설치 경로):

```sh
# 저장소 밖 임시 환경 사용; uv가 있는 개발 환경 예시
uv venv /tmp/nrnf-verify
cd backend
uv pip install --python /tmp/nrnf-verify/bin/python -r pyproject.toml --extra test
/tmp/nrnf-verify/bin/python -m unittest discover -s tests -v
# frontend에서 npm ci 및 npm run build
```

브라우저/실제 서버 재시작 검사는 `frontend/tests/README.md`의 명령과 환경 요구를 따른다.
시험 데이터와 프로세스는 소유한 임시 자료만 사용한다.

## 문서와 완료

- 요구/확정 여부: REQUIREMENTS, 구조/채택 판단: ARCHITECTURE, 실측: CURRENT_STATE,
  순서/완료: TASKS, 목적: PROJECT, 운영: 이 문서만 갱신한다.
- CURRENT_STATE에는 코드 기준 SHA, 이번 증거·미검증, 현재 차단/다음 조건만 남긴다.
  자신의 commit SHA를 자기 파일에 쓰기 위해 순환 commit하지 않는다. 문서 commit은 PR/Git으로 찾는다.
- 기존 docs 검증 증거는 보존하며 새 작업 일지를 계속 누적하지 않는다. tasks/decisions 디렉터리는
  긴 독립 명세 필요가 생겼을 때만 만든다. 동일 정책을 여러 문서에 복제하지 않는다.
- 종료 보고: 실제 변경/파일·검증/미검증·branch/SHA/PR·차단/다음 Task·갱신 문서.
  후속 지시문은 최신 main/기준 문서 확인·범위/금지·완료 조건·권장 환경을 포함한다.
