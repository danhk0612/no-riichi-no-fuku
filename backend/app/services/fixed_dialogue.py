from fastapi import HTTPException
from sqlalchemy import select
from app.db.models import CharacterFixedDialogue, CpuCharacter, CpuDialogue

SLOTS = ('win', 'defeat_stage_1', 'defeat_stage_2', 'defeat_stage_3', 'match_first')
TOKEN = '{{character_name}}'


def validate_text(text):
    remainder = text.replace(TOKEN, '')
    if '{' in remainder or '}' in remainder or '{%' in remainder or '%}' in remainder:
        raise HTTPException(422, detail={'code': 'invalid_dialogue', 'message': '허용되지 않은 변수 문법입니다.'})
    return text


def render_text(text, name):
    return text.replace(TOKEN, name)


def require_cpu(session, cpu_id):
    if session.get(CpuCharacter, cpu_id) is None:
        raise HTTPException(404, detail={'code': 'not_found', 'message': '캐릭터를 찾을 수 없습니다.'})


def read_fixed(session, cpu_id):
    require_cpu(session, cpu_id)
    row = session.get(CharacterFixedDialogue, cpu_id)
    return {'schema_version': 1, 'cpu_id': cpu_id, 'revision': row.revision if row else 0, 'slots': row.slots if row else {}}


def candidates(session, cpu_id):
    require_cpu(session, cpu_id)
    rows = session.scalars(select(CpuDialogue).where(CpuDialogue.cpu_character_id == cpu_id, CpuDialogue.event_key.in_(SLOTS)).order_by(CpuDialogue.id)).all()
    return {'items': [{'id': r.id, 'event_key': r.event_key, 'text': r.text, 'active': r.active} for r in rows]}


def conflict(code):
    raise HTTPException(409, detail={'code': code, 'message': '자료가 변경되었습니다. 다시 조회해 주세요.'})


def patch_fixed(session, cpu_id, change):
    try:
        require_cpu(session, cpu_id)
        row = session.get(CharacterFixedDialogue, cpu_id)
        rev = row.revision if row else 0
        if rev != change.expected_revision:
            conflict('revision_conflict')
        slots = dict(row.slots) if row else {}
        for key, edit in change.edits.items():
            if hasattr(edit, 'text'):
                slots[key] = {'text': validate_text(edit.text), 'origin': slots.get(key, {}).get('origin')}
                continue
            source = session.get(CpuDialogue, edit.legacy_dialogue_id)
            if source is None:
                conflict('legacy_dialogue_conflict')
            if source.cpu_character_id != cpu_id or source.event_key != key:
                raise HTTPException(422, detail={'code': 'invalid_source', 'message': '캐릭터 또는 대사 종류가 다릅니다.'})
            if not source.active or source.text != edit.expected_source_text:
                conflict('legacy_dialogue_conflict')
            validate_text(source.text)
            origin = {'legacy_dialogue_id': source.id, 'event_key': source.event_key, 'text': source.text}
            if key in slots:
                if slots[key].get('origin') != origin:
                    conflict('legacy_dialogue_conflict')
            else:
                slots[key] = {'text': source.text, 'origin': origin}
        if row is None:
            row = CharacterFixedDialogue(cpu_id=cpu_id, revision=1, slots=slots)
            session.add(row)
        else:
            row.revision = rev + 1
            row.slots = slots
        session.flush()
        session.commit()
        return read_fixed(session, cpu_id)
    except Exception:
        session.rollback()
        raise
