"""Prepare a disposable, replayable last turn. No result, ending, or acknowledgement is forged."""
import json
import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[2] / "backend"
sys.path[:0] = [str(backend), str(backend / "tests")]
from fastapi.testclient import TestClient
from app.local_runtime import create_local_runtime
from app.db.models import LocalPlayState, UserCpuProgress
from app.services.game_registry import GameRegistry, get_game_registry
from app.services.game_setup import create_game_session_from_choices
from app.services.local_play import effective_choices
from test_content_packs import character
from test_hand_results import _ack_all_results
from test_hand_cg_cache import PNG


def prepare(root):
    root.mkdir(parents=True, exist_ok=False)
    runtime = create_local_runtime(root)
    try:
        with TestClient(runtime.app, headers={"X-Local-Capability": runtime.capability}) as client:
            play = client.get("/api/local/play").json()
            body = {"generation": play["generation"], "cpu_character_ids": [1, 2, 3]}
            with runtime.session_factory.begin() as db:
                for cpu, stage in ((1, 2), (2, 3), (3, 3)):
                    db.get(UserCpuProgress, (runtime.member_id, cpu)).defeat_stage = stage
            pack = character()
            for stage in ("2", "3"):
                pack["levels"][stage]["images"] = dict.fromkeys(("cg", "profile", "full_body"), "test.png")
            folder = root / "packs" / "characters" / pack["id"]
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "test.png").write_bytes(PNG)
            (folder / "manifest.json").write_text(json.dumps(pack), encoding="utf-8")
            saved = client.post("/api/local/packs/rescan").json()["registry"]["packs"][0]
            client.post("/api/local/characters/1/pack-application",json={"expected_revision":0,
                "pack_id":saved["id"], "registered_revision_id":saved["registered_revision"]["id"]}).raise_for_status()
            client.patch("/api/local/characters/1/fixed-dialogues",json={"expected_revision":0,
                "edits":{"defeat_stage_3":{"text":"W11 fixture line"}}}).raise_for_status()
            client.post("/api/local/play/roster",json=body).raise_for_status()
            with runtime.session_factory() as db:
                choices = effective_choices(db,runtime.member_id,(1,2,3),db.get(LocalPlayState,runtime.member_id))
            for seed in range(64):
                game = create_game_session_from_choices(runtime.member_id,choices,seed=seed)
                steps = []
                while not game.done and len(steps)<800:
                    turn=game.human_turn()
                    steps.append(0)
                    game.submit_human_action(0)
                if steps and game.done and game.result().ranks[1]==4:
                    break
            else:
                raise RuntimeError("no suitable deterministic last turn")
            runtime.registry = GameRegistry(seed_factory=lambda:seed)
            runtime.app.dependency_overrides[get_game_registry] = lambda: runtime.registry
            started=client.post("/api/game/sessions",json=body)
            started.raise_for_status()
            sid=started.json()["session_id"]
            with runtime.session_factory() as db:
                registered=runtime.registry.get_owned(db,sid,runtime.member_id)
            for index in steps[:-1]:
                with runtime.session_factory() as db:
                    _ack_all_results(db,sid)
                    runtime.registry.submit_action(db,registered,index,registered.action_version)
                    db.commit()
            with runtime.session_factory.begin() as db:
                _ack_all_results(db,sid)
            turn=registered.game.human_turn()
            first=turn.legal_actions[0]
            selector=".action-bar button" if first["type"] else ".hand > *"
            n=0 if first["type"] else turn.observation["hands"][0].index(first["tile"])
            return {"session":sid,"generation":play["generation"],"seed":seed,"prior_actions":len(steps)-1,
                    "selector":selector,"index":n}
    finally:
        runtime.close()


if __name__=="__main__":
    Path(sys.argv[2]).write_text(json.dumps(prepare(Path(sys.argv[1]))),encoding="utf-8")
