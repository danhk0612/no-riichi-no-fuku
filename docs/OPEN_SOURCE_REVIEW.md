# Open Source Review

검토일: 2026-08-29

## RiichiEnv

- Repository: https://github.com/smly/RiichiEnv
- PyPI: https://pypi.org/project/riichienv/
- 검토 버전: 0.4.8
- License: Apache License 2.0
- 용도: 4인 일본 리치마작 게임 상태/규칙/합법 행동/관측 환경

확인된 특징:

- Rust 기반 고성능 코어
- Gym-style API
- Mortal/MJAI 호환
- 다양한 룰셋 지원
- 2026-04-27에 0.4.8 릴리스

프로젝트 코드는 MIT로 유지하면서 Apache-2.0 의존성으로 사용할 수 있다. 실제 배포 시 정확한 의존성 트리와 NOTICE/라이선스 포함 요건을 다시 확인한다.

첫 Work에서는 문서에 적은 가정 API를 그대로 믿지 말고 설치된 0.4.8의 실제 API와 동풍전 동작을 스파이크로 확인한다.

## MahjongRepository/mahjong

- Repository: https://github.com/MahjongRepository/mahjong
- License: MIT
- 용도 후보: 점수/샹텐/화료 계산 보조

RiichiEnv가 초기 요구를 충분히 충족하면 중복 도입하지 않는다. 실제로 필요한 기능이 확인될 때만 추가한다.

## Mortal

- Repository: https://github.com/Equim-chan/Mortal
- License: AGPL-3.0-or-later
- 용도 후보: 고난도 리치마작 AI

초기 버전에는 포함하지 않는다.

Tier 2 자체 CPU가 목표 품질에 미달하여 Mortal 코드/런타임을 실제 프로젝트에 결합할 필요가 생기면:

1. 실제 결합 형태 확인
2. AGPL 의무 검토
3. 프로젝트 라이선스를 호환되는 AGPL 계열로 전환
4. 필요한 소스 제공/고지 경로를 배포 문서에 명시
5. 그 뒤 Mortal adapter를 병합

비상업 프로젝트라는 이유만으로 라이선스 의무가 사라지지는 않으므로 조건을 그대로 준수한다.

## 초기 채택 결론

```text
No Riichi No Fuku: MIT
RiichiEnv 0.4.8: Apache-2.0 dependency
CPU: 자체 heuristic agent
External LLM: 사용하지 않음
Mortal: 초기 미사용 / 후속 후보
```
