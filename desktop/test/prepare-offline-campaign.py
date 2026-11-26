"""Play a fresh offline campaign through eight settlements; leave match nine's last move for the EXE."""
import json
import sys
from pathlib import Path

# Use the same isolated backend/test import paths as the packaged ending fixture.
backend = Path(__file__).resolve().parents[2] / "backend"
sys.path[:0] = [str(backend), str(backend / "tests")]

from fastapi.testclient import TestClient
from app.db.models import LocalPlayState
from app.local_runtime import create_local_runtime
from app.services.game_registry import GameRegistry, get_game_registry
from app.services.game_setup import create_game_session_from_choices
from app.services.local_play import effective_choices
from test_hand_results import _ack_all_results


def choose_match(member_id, choices, unfinished):
    # Choose a reproducible deal that exercises progression. All actions and ranks
    # are produced by the normal engine; the stored match replays this same deal.
    for seed in range(128):
        game = create_game_session_from_choices(member_id, choices, seed=seed)
        turns = 0
        while not game.done and turns < 800:
            game.submit_human_action(0)
            turns += 1
        if game.done and turns and game.result().ranks.index(4) in unfinished:
            return seed, turns, game.result().ranks.index(4)
    raise AssertionError("no seed with an unfinished CPU in fourth place")


def prepare(root):
    root.mkdir(parents=True, exist_ok=False)
    runtime = create_local_runtime(root)
    matches = []
    try:
        with TestClient(runtime.app, headers={"X-Local-Capability": runtime.capability}) as api:
            def play():
                response = api.get("/api/local/play")
                response.raise_for_status()
                return response.json()

            fresh = play()
            assert fresh["phase"] == "roster_required"
            body = {"generation": fresh["generation"], "cpu_character_ids": [1, 2, 3]}
            api.post("/api/local/play/roster", json=body).raise_for_status()
            seed = 0
            runtime.registry = GameRegistry(seed_factory=lambda: seed)
            runtime.app.dependency_overrides[get_game_registry] = lambda: runtime.registry
            for number in range(1, 10):
                with runtime.session_factory() as db:
                    choices = effective_choices(db, runtime.member_id, (1, 2, 3), db.get(LocalPlayState, runtime.member_id))
                before = [c.defeat_stage for c in choices]
                assert sum(before) == number - 1
                unfinished = {seat for seat, stage in enumerate(before, 1) if stage < 3}
                seed, turns, fourth = choose_match(choices, unfinished)
                started = api.post("/api/game/sessions", json=body)
                started.raise_for_status()
                sid = started.json()["session_id"]
                with runtime.session_factory() as db:
                    match = runtime.registry.get_owned(db, sid, runtime.member_id)
                for _ in range(turns if number < 9 else turns - 1):
                    with runtime.session_factory.begin() as db:
                        _ack_all_results(db, sid)
                        runtime.registry.submit_action(db, match, 0, match.action_version)
                with runtime.session_factory.begin() as db:
                    _ack_all_results(db, sid)
                if number == 9:
                    turn = match.game.human_turn()
                    action = turn.legal_actions[0]
                    discard = action["type"] == 0
                    return {"session": sid, "generation": fresh["generation"], "seed": seed,
                            "prior_actions": turns - 1, "no_media": True, "previous_matches": matches,
                            "selector": ".hand > *" if discard else ".action-bar button",
                            "index": turn.observation["hands"][0].index(action["tile"]) if discard else 0}
                assert match.game.done and match.game.result().ranks[fourth] == 4
                with runtime.session_factory.begin() as db:
                    runtime.registry.settle(db, match)
                with runtime.session_factory.begin() as db:
                    _ack_all_results(db, sid)
                after = {row["cpu_character_id"]: row["defeat_stage"] for row in play()["roster"]}
                expected = before.copy()
                expected[fourth - 1] += 1
                assert [after[cpu] for cpu in (1, 2, 3)] == expected
                matches.append({"session": sid, "seed": seed, "turns": turns, "stages": expected})
    finally:
        runtime.close()


if __name__ == "__main__":
    plan = prepare(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(plan), encoding="utf-8")
