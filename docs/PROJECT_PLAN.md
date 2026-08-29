# No Riichi No Fuku - 프로젝트 계획서

## 1. 목표

웹 브라우저에서 회원이 자신의 고정 프로필로 접속하여 CPU 캐릭터 3명을 선택하고, 4인 일본 리치마작 동풍전을 반복 플레이하는 싱글플레이 게임을 구현한다.

게임의 진행 목표는 각 CPU 캐릭터를 동풍전 최종 4위로 총 3회 만들어 최종 진행 단계까지 완료하는 것이다. 패배가 누적된 CPU는 다음 대국에서 더 강한 난이도로 플레이한다.

## 2. 확정 게임 흐름

1. 회원가입 또는 로그인
2. 회원 프로필 로드
   - 플레이어 이름
   - 프로필 이미지
   - 현재 HP / 최대 HP
3. 사용 가능한 CPU 캐릭터 목록 표시
4. CPU 3명 선택
5. 4인 동풍전 시작
6. 대국 중 좌석마다 이름/프로필/점수/필수 상태 표시
7. CPU 프로필 클릭 시 상세 정보 표시
8. 리치, 화료, 방총 등 주요 이벤트에서 상황별 말풍선 대사 표시
9. 동풍전 종료 후 최종 순위 판정
10. 최종 4위 처리
    - CPU 4위: 해당 캐릭터 `defeat_stage + 1`
    - 플레이어 4위: 플레이어 HP -1
11. CPU가 4위인 경우 해당 단계 결과 CG + 결과 대사 표시
12. `defeat_stage == 3`인 CPU는 이후 선택 불가
13. 플레이어 HP == 0이면 게임 오버
14. 다음 대국에서 CPU 3명을 다시 선택
15. 모든 CPU의 `defeat_stage == 3` 달성이 장기 게임 목표

## 3. 진행 단계와 CPU 난이도

| 현재 defeat_stage | 대국 가능 | CPU 난이도 | 다음 4위 결과 |
|---|---|---|---|
| 0 | 가능 | Tier 0 | stage 1 |
| 1 | 가능 | Tier 1 | stage 2 |
| 2 | 가능 | Tier 2 | stage 3 / 완료 |
| 3 | 불가 | 없음 | 없음 |

### Tier 0

- 합법 행동만 선택
- 샹텐 감소 우선
- 기본 유효패 폭 고려
- 리치/화료 등 명확한 행동 우선
- 수비 판단 약함
- 최상위 후보만 고정 선택하지 않고 상위 합리적 후보 사이에서 가중 선택

### Tier 1

- 샹텐 + 유효패 + 예상 타점
- 도라 및 형태 가치 반영
- 상대 리치 시 현물 등 기본 안전도 반영
- 치/퐁/깡의 손 진행 효과 평가
- 기본적인 push/fold

### Tier 2

- 패효율 + 타점 + 안전도 종합 평가
- 현물/스지/벽 기반 위험도
- 상대 리치 및 공격 신호 반영
- 남은 순목과 점수 상황 반영
- 동4국에서 최종 순위 조건 반영
- 후보 행동에 기대값에 가까운 점수 부여

### CPU 성향

난이도와 별개로 CPU마다 다음 성향 파라미터를 가진다.

- aggression
- defense
- call_preference
- riichi_preference
- hand_value_preference
- speed_preference

같은 Tier라도 캐릭터별 플레이 느낌이 달라져야 한다.

## 4. 마작 엔진

### 1차 채택 후보

RiichiEnv 0.4.8

선정 이유:

- 4인 일본 리치마작 환경 제공
- 동풍전 등 게임 모드 지원
- legal action 기반 행동 검증
- 샹텐/관측 환경 제공
- MJAI/Mortal 호환 구조
- Python에서 사용 가능
- Apache-2.0
- 2026년에도 릴리스가 존재하는 유지보수 중 프로젝트

초기 문서에서는 다음을 가정하지만, 첫 Work에서 실제 0.4.8 API로 반드시 검증한다.

```python
RiichiEnv(game_mode="4p-red-east", rule=GameRule.default_tenhou())
```

문서 예시보다 설치된 라이브러리의 실제 API를 우선한다.

## 5. CPU AI 방향

초기 버전에서는 외부 AI API/LLM을 사용하지 않는다.

CPU는 `MahjongAgent` 인터페이스 아래에서 자체 휴리스틱 평가기로 구현한다.

```text
RiichiEnv Observation
        |
        v
legal_actions
        |
        v
CPU Evaluator
- hand efficiency
- shanten
- ukeire approximation
- value
- defense
- placement
        |
        v
Character Style Modifier
        |
        v
Difficulty Policy
        |
        v
Action
```

Mortal은 Tier 2 자체 CPU의 품질이 부족할 때만 후속 대안으로 검토한다. AI 구현은 교체 가능한 adapter 뒤에 둔다.

## 6. 회원 시스템

회원 데이터 최소 항목:

- id
- login_id
- password_hash
- player_name
- profile_image_key
- current_hp
- max_hp
- role
- must_change_password
- is_active
- created_at
- updated_at

회원가입은 login_id + password + player_name + profile image 중심의 단순 구조로 한다.
프로필 이름과 이미지는 대국마다 다시 지정하지 않는다.

## 7. 최고 관리자

초기 최고 관리자 계정은 배포 환경변수로 지정한다.

- `SUPERADMIN_LOGIN_ID`
- `SUPERADMIN_INITIAL_PASSWORD`

원칙:

1. 최초 구동 시 최고 관리자가 없을 때만 생성
2. 평문 암호를 DB에 저장하지 않음
3. 최초 로그인 후 비밀번호 변경 전까지 관리자 기능 사용 제한
4. 변경 후 환경변수의 초기 비밀번호로 계정을 덮어쓰지 않음
5. 초기 계정 정보는 저장소에 하드코딩하지 않음

### 관리자 기능 범위

- 회원 조회/수정/활성 상태 관리
- CPU 캐릭터 생성/수정/사용 상태 관리
- CPU 기본 성향 파라미터 관리
- 대사 이벤트 및 문장 관리
- 단계별 CG 메타데이터 및 파일 업로드/교체/삭제
- 게임 기본 설정 관리(플레이어 HP 최대치 포함)

초기 버전은 최고 관리자 1종만 구현한다.

## 8. 캐릭터/진행 데이터

CPU 자체 데이터와 사용자별 진행 상태를 분리한다.

### cpu_characters

- id
- slug
- name
- age_adult
- short_description
- long_description
- profile_image_key
- active
- AI 성향 파라미터

### user_cpu_progress

- user_id
- cpu_character_id
- defeat_stage (0..3)
- updated_at

캐릭터 진행 단계는 사용자마다 독립적이다.

## 9. 대사 시스템

대사는 생성형 AI 대신 관리자 입력 데이터 풀을 사용한다.

초기 이벤트 후보:

- game_start
- riichi
- chi
- pon
- kan
- ron
- tsumo
- deal_in
- large_win
- rank_up
- rank_down
- final_east
- match_first
- match_last
- defeat_stage_1
- defeat_stage_2
- defeat_stage_3

일반 이벤트 대사의 확률/cooldown 정책은 UI 구현 단계에서 결정한다.

## 10. CG 관리

중요 원칙:

- CG 바이너리 파일을 Git 저장소에 넣지 않는다.
- 초기 저장소에 CG 폴더나 더미 CG 파일을 생성하지 않는다.
- CG는 추후 최고 관리자 페이지에서 업로드한다.
- 업로드된 CG는 Docker persistent volume에 저장한다.
- DB에는 파일 키/경로와 캐릭터/단계 연결 정보만 저장한다.

런타임 경로 예:

```text
/cpu/{cpu_id}/profile/...
/cpu/{cpu_id}/result/stage-1/...
/cpu/{cpu_id}/result/stage-2/...
/cpu/{cpu_id}/result/stage-3/...
/users/{user_id}/profile/...
```

위 경로는 런타임 저장소 규칙이며 Git 디렉터리 구조가 아니다.

## 11. Docker 목표 구조

초기 서비스는 다음 3개만 사용한다.

```text
web
api
db
```

영속 데이터:

```text
postgres_data
media_data
```

요구가 생기기 전 Redis, Kafka, MinIO 등 별도 인프라는 추가하지 않는다.

## 12. 구현 순서

1. Docker 부트스트랩 실제 실행 검증
2. RiichiEnv 0.4.8 API/동풍전 스파이크
3. 인증 / 회원 프로필
4. DB 모델 / migration / 최고 관리자 bootstrap
5. CPU/대사 관리자 기초
6. RiichiEnv adapter + 서버 authoritative game session
7. 최소 마작 UI
8. Tier 0 CPU 3명으로 동풍전 완주
9. 4위 판정 / HP / `user_cpu_progress`
10. CPU 재선택 게임 루프
11. 말풍선 / 대사
12. CG metadata + 관리자 업로드
13. Tier 1 CPU
14. Tier 2 CPU
15. 자동 시뮬레이션 기반 난이도 튜닝

## 13. 아직 미확정

다음은 임의로 확정하지 않는다.

- 플레이어 최대 HP 실제 값
- 게임 오버 이후 진행 데이터 처리
- 모든 CPU 최종 완료 후 엔딩 처리
- 세부 리치마작 룰 차이
- 최종 캐릭터 이름/설정/이미지
- Mortal 실제 사용 여부
