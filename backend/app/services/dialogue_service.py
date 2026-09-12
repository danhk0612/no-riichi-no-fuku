"""대사 선택 및 게임 이벤트 매핑 서비스"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

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
    events: Sequence[dict[str, object]],
    cpu_character_by_seat: dict[int, int],
    dialogue_selector: DialogueSelector,
    session: Session,
) -> list[DialogueEvent]:
    """
    RiichiEnv 이벤트 목록에서 대사를 생성할 게임 이벤트를 추출한다.
    
    Args:
        events: RiichiEnv observation의 events 필드
        cpu_character_by_seat: 좌석 번호 -> CPU 캐릭터 ID 매핑
        dialogue_selector: 대사 선택기
        session: DB 세션
    
    Returns:
        대사 이벤트 목록
    """
    dialogue_events: list[DialogueEvent] = []

    for event in events:
        if not isinstance(event, dict):
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

        text = dialogue_selector.select_dialogue(
            session, cpu_character_id, event_key
        )
        if text is not None:
            dialogue_events.append(
                DialogueEvent(
                    cpu_character_id=cpu_character_id,
                    seat=actor,
                    event_key=event_key,
                    text=text,
                )
            )

    return dialogue_events


def _map_event_type_to_key(
    event_type: object,
    event: dict[str, object],
) -> str | None:
    """
    RiichiEnv 이벤트 타입을 대사 이벤트 키로 매핑한다.
    
    초기 후보 이벤트:
    - riichi (리치 선언)
    - chi (치)
    - pon (퐁)
    - kan (깡: 대명깡/암깡/가깡 통합)
    - ron (론 화료)
    - tsumo (쯔모 화료)
    - deal_in (방총 - 타인의 ron 이벤트에서 방총한 사람)
    
    추가 후보:
    - game_start (게임 시작 - 외부에서 처리)
    - final_east (동4국 진입 - 외부에서 처리)
    - match_first, match_last (최종 순위 - 외부에서 처리)
    - large_win (만관 이상 화료 - 외부에서 처리)
    - defeat_stage_N (결과 화면 - 외부에서 처리)
    """
    if not isinstance(event_type, str):
        return None

    # RiichiEnv/MJAI 이벤트 타입을 대사 키로 매핑
    # 실제 RiichiEnv 이벤트 타입은 확인 필요하지만 일반적인 MJAI 형식을 따름
    event_type_lower = event_type.lower()

    if event_type_lower in ("reach", "riichi"):
        return "riichi"
    elif event_type_lower == "chi":
        return "chi"
    elif event_type_lower == "pon":
        return "pon"
    elif event_type_lower in ("daiminkan", "ankan", "kakan", "kan"):
        return "kan"
    elif event_type_lower in ("hora", "agari"):
        # hora 이벤트에서 ron/tsumo 구분
        target = event.get("target")
        if isinstance(target, int) and target != event.get("actor"):
            # target이 있고 actor와 다르면 ron
            return "ron"
        else:
            # 그 외는 tsumo
            return "tsumo"
    else:
        return None
