from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CpuCharacter, User, UserCpuProgress
from app.mahjong.agent import MahjongAgent
from app.mahjong.session import AuthoritativeGameSession, CPU_SEATS
from app.mahjong.tier0 import Tier0Agent


class GameSetupError(RuntimeError):
    pass


class InvalidCpuSelectionError(GameSetupError):
    pass


class CpuTierUnavailableError(GameSetupError):
    pass


@dataclass(frozen=True)
class CpuChoice:
    id: int
    slug: str
    name: str
    age_adult: bool
    style: str
    short_description: str
    long_description: str | None
    profile_image_key: str | None
    defeat_stage: int


class CpuAgentFactory(Protocol):
    def __call__(
        self,
        choice: CpuChoice,
        *,
        seed: int | None,
    ) -> MahjongAgent: ...


def list_selectable_cpus(db_session: Session, user_id: int) -> list[CpuChoice]:
    rows = db_session.execute(
        select(CpuCharacter, UserCpuProgress.defeat_stage)
        .join(
            UserCpuProgress,
            UserCpuProgress.cpu_character_id == CpuCharacter.id,
        )
        .where(
            UserCpuProgress.user_id == user_id,
            CpuCharacter.active.is_(True),
            UserCpuProgress.defeat_stage < 3,
        )
        .order_by(CpuCharacter.id)
    ).all()
    return [
        CpuChoice(
            id=cpu.id,
            slug=cpu.slug,
            name=cpu.name,
            age_adult=cpu.age_adult,
            style=cpu.style,
            short_description=cpu.short_description,
            long_description=cpu.long_description,
            profile_image_key=cpu.profile_image_key,
            defeat_stage=defeat_stage,
        )
        for cpu, defeat_stage in rows
    ]


def create_production_cpu_agent(
    choice: CpuChoice,
    *,
    seed: int | None,
) -> MahjongAgent:
    if choice.defeat_stage != 0:
        raise CpuTierUnavailableError(
            f"CPU tier {choice.defeat_stage} is not implemented"
        )
    return Tier0Agent(seed=seed)


def create_game_session(
    db_session: Session,
    user: User,
    cpu_character_ids: tuple[int, int, int],
    *,
    seed: int | None = None,
    agent_factory: CpuAgentFactory = create_production_cpu_agent,
) -> AuthoritativeGameSession:
    if user.role != "member" or user.current_hp is None or user.max_hp is None:
        raise GameSetupError("member game profile is not initialized")
    if user.current_hp <= 0:
        raise GameSetupError("member has no remaining HP")
    if len(set(cpu_character_ids)) != 3:
        raise InvalidCpuSelectionError("three distinct CPU characters are required")

    choices_by_id = {
        choice.id: choice for choice in list_selectable_cpus(db_session, user.id)
    }
    if any(cpu_id not in choices_by_id for cpu_id in cpu_character_ids):
        raise InvalidCpuSelectionError("selection contains an unavailable CPU")

    return create_game_session_from_choices(
        user.id,
        tuple(choices_by_id[cpu_id] for cpu_id in cpu_character_ids),
        seed=seed,
        agent_factory=agent_factory,
    )


def create_game_session_from_choices(
    user_id: int,
    choices: tuple[CpuChoice, CpuChoice, CpuChoice],
    *,
    seed: int | None = None,
    agent_factory: CpuAgentFactory = create_production_cpu_agent,
) -> AuthoritativeGameSession:
    cpu_character_ids = tuple(choice.id for choice in choices)
    if len(set(cpu_character_ids)) != 3:
        raise InvalidCpuSelectionError("three distinct CPU characters are required")
    cpu_agents = {
        seat: agent_factory(
            choice,
            seed=None if seed is None else seed * 10 + seat,
        )
        for seat, choice in zip(CPU_SEATS, choices)
    }
    game = AuthoritativeGameSession(
        user_id=user_id,
        cpu_character_ids=cpu_character_ids,
        cpu_agents=cpu_agents,
        seed=seed,
    )
    game.start()
    return game
