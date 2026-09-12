"""대사 선택 서비스 테스트"""
import random

from sqlalchemy.orm import Session

from app.db.models import CpuCharacter, CpuDialogue, User, UserCpuProgress
from app.services.dialogue_service import (
    DialogueSelector,
    extract_game_events,
)


def test_dialogue_selector_selects_active_dialogue(session: Session) -> None:
    """DialogueSelector가 활성 대사 중 하나를 선택한다"""
    cpu = CpuCharacter(
        slug="test-cpu",
        name="테스트 CPU",
        age_adult=True,
        style="테스트",
        short_description="테스트 캐릭터",
        active=True,
        aggression=0.5,
        defense=0.5,
        call_preference=0.5,
        riichi_preference=0.5,
        hand_value_preference=0.5,
        speed_preference=0.5,
    )
    session.add(cpu)
    session.flush()

    dialogues = [
        CpuDialogue(
            cpu_character_id=cpu.id,
            event_key="riichi",
            text=f"리치 대사 {i + 1}",
            active=True,
        )
        for i in range(3)
    ]
    session.add_all(dialogues)
    session.flush()

    selector = DialogueSelector(rng=random.Random(42))
    selected_text = selector.select_dialogue(session, cpu.id, "riichi")

    assert selected_text in {"리치 대사 1", "리치 대사 2", "리치 대사 3"}


def test_dialogue_selector_ignores_inactive_dialogue(session: Session) -> None:
    """DialogueSelector가 비활성 대사는 무시한다"""
    cpu = CpuCharacter(
        slug="test-cpu",
        name="테스트 CPU",
        age_adult=True,
        style="테스트",
        short_description="테스트 캐릭터",
        active=True,
        aggression=0.5,
        defense=0.5,
        call_preference=0.5,
        riichi_preference=0.5,
        hand_value_preference=0.5,
        speed_preference=0.5,
    )
    session.add(cpu)
    session.flush()

    active_dialogue = CpuDialogue(
        cpu_character_id=cpu.id,
        event_key="pon",
        text="활성 퐁 대사",
        active=True,
    )
    inactive_dialogue = CpuDialogue(
        cpu_character_id=cpu.id,
        event_key="pon",
        text="비활성 퐁 대사",
        active=False,
    )
    session.add_all([active_dialogue, inactive_dialogue])
    session.flush()

    selector = DialogueSelector(rng=random.Random(42))
    selected_text = selector.select_dialogue(session, cpu.id, "pon")

    assert selected_text == "활성 퐁 대사"


def test_dialogue_selector_returns_none_when_no_dialogue(session: Session) -> None:
    """DialogueSelector가 대사가 없을 때 None을 반환한다"""
    cpu = CpuCharacter(
        slug="test-cpu",
        name="테스트 CPU",
        age_adult=True,
        style="테스트",
        short_description="테스트 캐릭터",
        active=True,
        aggression=0.5,
        defense=0.5,
        call_preference=0.5,
        riichi_preference=0.5,
        hand_value_preference=0.5,
        speed_preference=0.5,
    )
    session.add(cpu)
    session.flush()

    selector = DialogueSelector()
    selected_text = selector.select_dialogue(session, cpu.id, "riichi")

    assert selected_text is None


def test_extract_game_events_extracts_riichi(session: Session) -> None:
    """extract_game_events가 리치 이벤트를 추출한다"""
    cpu = CpuCharacter(
        slug="test-cpu",
        name="테스트 CPU",
        age_adult=True,
        style="테스트",
        short_description="테스트 캐릭터",
        active=True,
        aggression=0.5,
        defense=0.5,
        call_preference=0.5,
        riichi_preference=0.5,
        hand_value_preference=0.5,
        speed_preference=0.5,
    )
    session.add(cpu)
    session.flush()

    dialogue = CpuDialogue(
        cpu_character_id=cpu.id,
        event_key="riichi",
        text="리치!",
        active=True,
    )
    session.add(dialogue)
    session.flush()

    events = [
        {"type": "riichi", "actor": 1},
        {"type": "dahai", "actor": 0},  # 사람 좌석, 무시됨
    ]
    cpu_character_by_seat = {1: cpu.id}
    selector = DialogueSelector(rng=random.Random(42))

    dialogue_events = extract_game_events(
        events=events,
        cpu_character_by_seat=cpu_character_by_seat,
        dialogue_selector=selector,
        session=session,
    )

    assert len(dialogue_events) == 1
    assert dialogue_events[0].seat == 1
    assert dialogue_events[0].event_key == "riichi"
    assert dialogue_events[0].text == "리치!"
    assert dialogue_events[0].cpu_character_id == cpu.id


def test_extract_game_events_ignores_human_seat(session: Session) -> None:
    """extract_game_events가 사람 좌석 이벤트는 무시한다"""
    cpu = CpuCharacter(
        slug="test-cpu",
        name="테스트 CPU",
        age_adult=True,
        style="테스트",
        short_description="테스트 캐릭터",
        active=True,
        aggression=0.5,
        defense=0.5,
        call_preference=0.5,
        riichi_preference=0.5,
        hand_value_preference=0.5,
        speed_preference=0.5,
    )
    session.add(cpu)
    session.flush()

    events = [
        {"type": "riichi", "actor": 0},  # 사람 좌석
    ]
    cpu_character_by_seat = {1: cpu.id}
    selector = DialogueSelector()

    dialogue_events = extract_game_events(
        events=events,
        cpu_character_by_seat=cpu_character_by_seat,
        dialogue_selector=selector,
        session=session,
    )

    assert len(dialogue_events) == 0


def test_extract_game_events_handles_multiple_events(session: Session) -> None:
    """extract_game_events가 여러 이벤트를 처리한다"""
    cpu1 = CpuCharacter(
        slug="test-cpu-1",
        name="테스트 CPU 1",
        age_adult=True,
        style="테스트",
        short_description="테스트 캐릭터 1",
        active=True,
        aggression=0.5,
        defense=0.5,
        call_preference=0.5,
        riichi_preference=0.5,
        hand_value_preference=0.5,
        speed_preference=0.5,
    )
    cpu2 = CpuCharacter(
        slug="test-cpu-2",
        name="테스트 CPU 2",
        age_adult=True,
        style="테스트",
        short_description="테스트 캐릭터 2",
        active=True,
        aggression=0.5,
        defense=0.5,
        call_preference=0.5,
        riichi_preference=0.5,
        hand_value_preference=0.5,
        speed_preference=0.5,
    )
    session.add_all([cpu1, cpu2])
    session.flush()

    dialogue1 = CpuDialogue(
        cpu_character_id=cpu1.id,
        event_key="riichi",
        text="리치!",
        active=True,
    )
    dialogue2 = CpuDialogue(
        cpu_character_id=cpu2.id,
        event_key="pon",
        text="퐁!",
        active=True,
    )
    session.add_all([dialogue1, dialogue2])
    session.flush()

    events = [
        {"type": "riichi", "actor": 1},
        {"type": "pon", "actor": 2},
    ]
    cpu_character_by_seat = {1: cpu1.id, 2: cpu2.id}
    selector = DialogueSelector(rng=random.Random(42))

    dialogue_events = extract_game_events(
        events=events,
        cpu_character_by_seat=cpu_character_by_seat,
        dialogue_selector=selector,
        session=session,
    )

    assert len(dialogue_events) == 2
    assert dialogue_events[0].seat == 1
    assert dialogue_events[0].event_key == "riichi"
    assert dialogue_events[0].text == "리치!"
    assert dialogue_events[1].seat == 2
    assert dialogue_events[1].event_key == "pon"
    assert dialogue_events[1].text == "퐁!"
