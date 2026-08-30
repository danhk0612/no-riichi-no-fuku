from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, UserCpuProgress
from app.mahjong.session import AuthoritativeGameSession, HUMAN_SEAT


class MatchSettlementError(RuntimeError):
    pass


class MatchAlreadySettledError(MatchSettlementError):
    pass


class MatchSettlementStateError(MatchSettlementError):
    pass


@dataclass(frozen=True)
class MatchSettlement:
    last_place_seat: int
    current_hp: int
    cpu_character_id: int | None
    defeat_stage: int | None
    game_over: bool
    cpu_completed: bool


def settle_completed_match(
    db_session: Session,
    game: AuthoritativeGameSession,
) -> MatchSettlement:
    if game.result_settled:
        raise MatchAlreadySettledError("match result is already settled")

    result = game.result()
    if sorted(result.ranks) != [1, 2, 3, 4]:
        raise MatchSettlementStateError("match ranks must be a permutation of 1..4")
    last_place_seat = result.ranks.index(4)

    user = db_session.scalar(
        select(User)
        .where(User.id == game.user_id, User.role == "member")
        .with_for_update()
    )
    if user is None:
        raise MatchSettlementStateError("member not found")
    if user.current_hp is None or user.max_hp is None:
        raise MatchSettlementStateError("member HP is not initialized")
    if user.current_hp <= 0:
        raise MatchSettlementStateError("member has no remaining HP")

    cpu_character_id: int | None = None
    defeat_stage: int | None = None
    if last_place_seat == HUMAN_SEAT:
        user.current_hp -= 1
    else:
        cpu_character_id = game.cpu_character_by_seat.get(last_place_seat)
        if cpu_character_id is None:
            raise MatchSettlementStateError("last-place CPU seat is not mapped")
        progress = db_session.scalar(
            select(UserCpuProgress)
            .where(
                UserCpuProgress.user_id == user.id,
                UserCpuProgress.cpu_character_id == cpu_character_id,
            )
            .with_for_update()
        )
        if progress is None:
            raise MatchSettlementStateError("CPU progress not found")
        if progress.defeat_stage >= 3:
            raise MatchSettlementStateError("CPU progress is already complete")
        progress.defeat_stage += 1
        defeat_stage = progress.defeat_stage

    db_session.flush()
    game.mark_result_settled()
    return MatchSettlement(
        last_place_seat=last_place_seat,
        current_hp=user.current_hp,
        cpu_character_id=cpu_character_id,
        defeat_stage=defeat_stage,
        game_over=user.current_hp == 0,
        cpu_completed=defeat_stage == 3,
    )
