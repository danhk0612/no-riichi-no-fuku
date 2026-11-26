from dataclasses import asdict
from hashlib import sha256
from secrets import choice
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_superadmin, get_session
from app.db.models import LocalMediaAsset
from app.db.models.character_content import StageImage
from app.services.character_content import get_character_content
from app.services.generation_settings import match_inputs
from app.services.hand_cg_cache import HandCG, replace
from app.services.local_media import media_path
from app.services.shared_prompts import get_candidates

router = APIRouter(prefix="/api/local/characters/{cpu}/stage-images/{level}/{kind}",
                   dependencies=[Depends(get_current_superadmin)])
Kind = Literal["profile", "full_body", "cg"]


def parts(db, cpu, level, kind, content):
    prompts = content["prompts"]
    selected = [prompts["appearance"]]
    if level in (1, 2):
        selected.append(prompts["upper_underwear"])
    if level == 2:
        selected.append(prompts["lower_underwear"])
    for group in ("clothing_state", "situation", "pose"):
        if group == "situation" and (kind != "cg" or level == 0):
            continue  # no hand/defeat event for a neutral portrait
        event = f"defeat_stage_{level}" if group == "situation" else None
        items = get_candidates(db, cpu, level, group, event)["effective_items"]
        if not items:
            label = {"clothing_state":"복장 상태", "pose":"포즈", "situation":"패배 상황"}[group]
            raise HTTPException(422, f"{level}단계 {label} 후보를 먼저 등록해 주세요.")
        selected.append(choice(items))
    selected.append(content["levels"][str(level)][kind])
    return {k: "\n".join(p[k] for p in selected if p[k]) for k in ("positive", "negative")}


@router.post("")
def prepare(cpu: int, kind: Kind, expected_revision: int, level: int = Path(ge=0, le=3),
            db: Session = Depends(get_session)):
    content = get_character_content(db, cpu)
    if content["revision"] != expected_revision:
        raise HTTPException(409, "캐릭터 설정이 변경됐습니다. 다시 불러와 주세요.")
    cfg = match_inputs(db)
    if not cfg:
        raise HTTPException(422, "이미지 생성 설정을 확인해 주세요.")
    common, char = cfg.inputs_for(cpu)
    settings = {**asdict(common), "model": char["character_model"] or common.model,
                "loras": [*common.loras, *char["character_loras"]]}
    if not all(settings[k] for k in ("model", "encoder", "vae")):
        raise HTTPException(422, "먼저 모델·텍스트 인코더·VAE를 설정해 주세요.")
    ticket = str(uuid4())
    frozen = {**parts(db, cpu, level, kind, content), "workflow":"anima-txt2img-v1", "kind":kind,
              "stage":level, "settings":settings}
    slot = db.get(StageImage,(cpu,level,kind))
    if slot is None:
        slot = StageImage(cpu_id=cpu, level=level, kind=kind)
        db.add(slot)
    slot.ticket, slot.inputs, slot.endpoint = ticket, frozen, cfg.endpoint
    slot.content_revision = expected_revision
    db.flush()
    ticket = slot.ticket
    db.commit()
    return {"ticket":ticket}


def current(db,cpu,level,kind,ticket):
    slot = db.get(StageImage,(cpu,level,kind))
    if not slot or slot.ticket != ticket:
        raise HTTPException(409,"다른 생성 요청이 선택됐습니다. 캐릭터를 다시 불러와 주세요.")
    return slot


def cache(request):
    return HandCG(request.app.state.local_runtime.paths.root / "generated" / "stage")


@router.post("/{ticket}/advance")
def advance(cpu:int, level:int, kind:Kind, ticket:str, request:Request, retry:str|None=None, db:Session=Depends(get_session)):
    slot = current(db,cpu,level,kind,ticket)
    frozen, endpoint = slot.inputs, slot.endpoint
    db.rollback()
    return cache(request).advance(frozen,endpoint,retry)


@router.get("/{ticket}/{attempt}")
def preview(cpu:int,level:int,kind:Kind,ticket:str,attempt:str,request:Request,db:Session=Depends(get_session)):
    frozen = current(db,cpu,level,kind,ticket).inputs
    db.rollback()
    data = cache(request).image(frozen,attempt)
    if data is None:
        raise HTTPException(404,"미리보기 이미지가 없습니다.")
    return Response(data,media_type="image/png",headers={"Cache-Control":"no-store"})


@router.post("/{ticket}/{attempt}/save")
def apply(cpu:int,level:int,kind:Kind,ticket:str,attempt:str,request:Request,db:Session=Depends(get_session)):
    slot = current(db,cpu,level,kind,ticket)
    if get_character_content(db,cpu)["revision"] != slot.content_revision:
        raise HTTPException(409,"생성 후 캐릭터 설정이 변경됐습니다. 다시 생성해 주세요.")
    data = cache(request).image(slot.inputs,attempt)
    if data is None:
        raise HTTPException(409,"저장 가능한 생성 결과가 없습니다.")
    digest = sha256(data).hexdigest()
    previous = db.get(LocalMediaAsset,slot.media_id) if slot.media_id else None
    existing = media_path(request.app.state.local_runtime.paths.media,previous.storage_key) if previous else None
    if slot.digest != digest or not existing or not existing.is_file() or existing.read_bytes() != data:
        ident = str(uuid4())
        key = f"stage/{ident}.png"
        dest = media_path(request.app.state.local_runtime.paths.media,key)
        dest.parent.mkdir(parents=True,exist_ok=True)
        replace(dest,data)
        try:
            db.add(LocalMediaAsset(id=ident,kind="image",storage_key=key,mime_type="image/png",byte_size=len(data)))
            db.flush()
            slot.media_id, slot.digest = ident, digest
            db.commit()
        except Exception:
            db.rollback()
            dest.unlink(missing_ok=True)
            raise
    return get_character_content(db,cpu)
