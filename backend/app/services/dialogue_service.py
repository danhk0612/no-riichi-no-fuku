"""대사 선택 및 게임 이벤트 매핑 서비스"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models import CpuDialogue

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class DialogueEvent:
    """대사 이벤트: CPU가 말풍선으로 표시할 대사"""

    cpu_character_id: int
    seat: int
    event_key: str
    text: str


@dataclass(frozen=True)
class DialogueEventRule:
    """이벤트별 대사 노출 규칙."""

    probability: float
    cpu_cooldown_turns: int
    event_cooldown_turns: int
    priority: int


DEFAULT_DIALOGUE_EVENT_RULES: Mapping[str, DialogueEventRule] = {
    "ron": DialogueEventRule(1.0, 0, 0, 60),
    "tsumo": DialogueEventRule(1.0, 0, 0, 60),
    "riichi": DialogueEventRule(0.9, 0, 0, 50),
    "kan": DialogueEventRule(0.75, 2, 2, 40),
    "pon": DialogueEventRule(0.45, 2, 3, 30),
    "chi": DialogueEventRule(0.35, 2, 3, 20),
}


class DialogueEventPolicy:
    """게임 세션별 대사 확률, cooldown, rapid-event 제한 정책."""

    def __init__(
        self,
        *,
        rng: random.Random | None = None,
        rules: Mapping[str, DialogueEventRule] = DEFAULT_DIALOGUE_EVENT_RULES,
    ) -> None:
        self._rng = rng or random.Random()
        self._rules = rules
        self._last_cpu_turn: dict[int, int] = {}
        self._last_event_turn: dict[tuple[int, str], int] = {}
        self._last_emission_turn: int | None = None

    def ordered_candidates(
        self,
        candidates: Sequence[tuple[int, int, str]],
    ) -> list[tuple[int, int, str]]:
        """같은 전송에 묶인 이벤트를 중요도 순으로 정렬한다."""
        return sorted(
            candidates,
            key=lambda candidate: self._rules[candidate[2]].priority,
            reverse=True,
        )

    def allows(self, cpu_character_id: int, event_key: str, turn: int) -> bool:
        rule = self._rules.get(event_key)
        if rule is None or self._last_emission_turn == turn:
            return False

        last_cpu_turn = self._last_cpu_turn.get(cpu_character_id)
        if (
            last_cpu_turn is not None
            and turn - last_cpu_turn < rule.cpu_cooldown_turns
        ):
            return False

        last_event_turn = self._last_event_turn.get(
            (cpu_character_id, event_key)
        )
        if (
            last_event_turn is not None
            and turn - last_event_turn < rule.event_cooldown_turns
        ):
            return False

        return self._rng.random() < rule.probability

    def record_emission(
        self,
        cpu_character_id: int,
        event_key: str,
        turn: int,
    ) -> None:
        self._last_cpu_turn[cpu_character_id] = turn
        self._last_event_turn[(cpu_character_id, event_key)] = turn
        self._last_emission_turn = turn


class DialogueSelector:
    """CPU 대사 선택기"""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def select_dialogue(
        self,
        session: Session,
        cpu_character_id: int,
        event_key: str,
    ) -> str | None:
        """
        주어진 CPU와 이벤트 키에 해당하는 활성 대사 중 하나를 랜덤으로 선택한다.
        
        Args:
            session: DB 세션
            cpu_character_id: CPU 캐릭터 ID
            event_key: 이벤트 키 (예: "riichi", "pon", "ron", "tsumo" 등)
        
        Returns:
            선택된 대사 텍스트, 없으면 None
        """
        candidates = session.scalars(
            select(CpuDialogue)
            .where(
                and_(
                    CpuDialogue.cpu_character_id == cpu_character_id,
                    CpuDialogue.event_key == event_key,
                    CpuDialogue.active == True,  # noqa: E712
                )
            )
            .limit(100)  # 성능을 위해 최대 100개로 제한
        ).all()

        if not candidates:
            return None

        chosen = self._rng.choice(candidates)
        return chosen.text


def extract_game_events(
    *,
    events: Sequence[dict[str, object] | str],
    cpu_character_by_seat: dict[int, int],
    dialogue_selector: DialogueSelector,
    dialogue_policy: DialogueEventPolicy,
    event_turn: int,
    session: Session,
) -> list[DialogueEvent]:
    """
    RiichiEnv 이벤트 목록에서 대사를 생성할 게임 이벤트를 추출한다.
    
    RiichiEnv 0.4.8의 events는 JSON 문자열 리스트로 반환된다.
    
    Args:
        events: RiichiEnv observation의 events 필드 (JSON 문자열 또는 dict)
        cpu_character_by_seat: 좌석 번호 -> CPU 캐릭터 ID 매핑
        dialogue_selector: 대사 선택기
        session: DB 세션
    
    Returns:
        대사 이벤트 목록
    """
    import json
    
    candidates: list[tuple[int, int, str]] = []

    for event_raw in events:
        # RiichiEnv 0.4.8은 이벤트를 JSON 문자열로 반환
        if isinstance(event_raw, str):
            try:
                event = json.loads(event_raw)
            except json.JSONDecodeError:
                continue
        elif isinstance(event_raw, dict):
            event = event_raw
        else:
            continue

        event_type = event.get("type")
        actor = event.get("actor")

        # actor가 CPU 좌석이 아니면 무시
        if not isinstance(actor, int) or actor not in cpu_character_by_seat:
            continue

        cpu_character_id = cpu_character_by_seat[actor]
        event_key = _map_event_type_to_key(event_type, event)

        if event_key is None:
            continue

        candidates.append((cpu_character_id, actor, event_key))

    dialogue_events: list[DialogueEvent] = []
    for cpu_character_id, actor, event_key in dialogue_policy.ordered_candidates(
        candidates
    ):
        if not dialogue_policy.allows(
            cpu_character_id,
            event_key,
            event_turn,
        ):
            continue

        text = dialogue_selector.select_dialogue(
            session,
            cpu_character_id,
            event_key,
        )
        if text is not None:
            dialogue_policy.record_emission(
                cpu_character_id,
                event_key,
                event_turn,
            )
            dialogue_events.append(
                DialogueEvent(
                    cpu_character_id=cpu_character_id,
                    seat=actor,
                    event_key=event_key,
                    text=text,
                )
            )
            break

    return dialogue_events


def _map_event_type_to_key(
    event_type: object,
    event: dict[str, object],
) -> str | None:
    """
    RiichiEnv 0.4.8 이벤트 타입을 대사 이벤트 키로 매핑한다.
    
    검증된 RiichiEnv 0.4.8 이벤트 타입:
    - reach: 리치 선언 → riichi
    - reach_accepted: 리치 수리 (현재 대사 없음)
    - chi: 치 → chi
    - pon: 퐁 → pon
    - ankan: 암깡 → kan
    - kakan: 가깡 → kan
    - daiminkan: 대명깡 → kan
    - hora: 화료 (target 필드로 ron/tsumo 구분)
      - target이 있고 actor와 다름 → ron
      - 그 외 → tsumo
    
    참고: 이벤트는 JSON 문자열로 반환되므로 파싱 필요
    """
    if not isinstance(event_type, str):
        return None

    event_type_lower = event_type.lower()

    # 리치 선언
    if event_type_lower == "reach":
        return "riichi"
    # 치
    elif event_type_lower == "chi":
        return "chi"
    # 퐁
    elif event_type_lower == "pon":
        return "pon"
    # 깡 (모든 타입 통합)
    elif event_type_lower in ("ankan", "kakan", "daiminkan"):
        return "kan"
    # 화료 (ron/tsumo 구분)
    elif event_type_lower == "hora":
        target = event.get("target")
        actor = event.get("actor")
        # target이 있고 actor와 다르면 ron (타인의 버린 패로 화료)
        if isinstance(target, int) and isinstance(actor, int) and target != actor:
            return "ron"
        else:
            # 그 외는 tsumo (자신이 뽑은 패로 화료)
            return "tsumo"
    else:
        return None
