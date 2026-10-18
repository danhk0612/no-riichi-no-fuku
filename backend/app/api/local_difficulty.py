from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_member, get_session
from app.db.models import GameSetting, User
from app.services.difficulty import DifficultyError, KEY, read_setting

router = APIRouter(prefix="/api/local/difficulty", tags=["local-difficulty"])


class DifficultyWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    setting: Annotated[int, Field(strict=True, ge=1, le=10)]
    expected_revision: Annotated[int, Field(strict=True, ge=0)]


@router.get("")
def get_difficulty(user: User = Depends(get_current_member), session: Session = Depends(get_session)):
    try:
        return {**read_setting(session), "applies_to": "next_match"}
    except DifficultyError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.put("")
def put_difficulty(request: DifficultyWrite, user: User = Depends(get_current_member),
                   session: Session = Depends(get_session)):
    # Local session dependency reserves the same writer as match start before reading.
    try:
        current = read_setting(session)
        if request.expected_revision != current["revision"]:
            raise DifficultyError("difficulty setting changed; reload before saving")
        value = {"version": 1, "revision": current["revision"] + 1, "setting": request.setting}
        row = session.get(GameSetting, KEY)
        if row is None:
            session.add(GameSetting(key=KEY, value=value))
        else:
            row.value = value
        session.commit()
        return {**value, "applies_to": "next_match"}
    except DifficultyError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from None
    except Exception:
        session.rollback()
        raise
