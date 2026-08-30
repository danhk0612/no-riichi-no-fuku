from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_member, get_session
from app.db.models import User
from app.schemas.game import CpuChoiceResponse
from app.services.game_setup import CpuChoice, list_selectable_cpus


router = APIRouter(prefix="/api/game", tags=["game"])


@router.get("/cpus", response_model=list[CpuChoiceResponse])
def get_selectable_cpu_characters(
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[CpuChoice]:
    return list_selectable_cpus(session, user.id)
