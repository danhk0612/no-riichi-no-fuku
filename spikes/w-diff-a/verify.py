"""Executable spike checks and bounded metrics, without production monkeypatches."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

from riichienv import ActionType, calculate_shanten

from app.mahjong.riichienv_adapter import RiichiEnvAdapter
from app.mahjong.tier2 import Tier2Agent
from app.services.game_setup import CpuChoice, create_game_session_from_choices
from profiles import PROFILES, ProfileAgent


FIELDS = ("aggression", "defense", "call_preference", "riichi_preference",
          "hand_value_preference", "speed_preference")
ROOT = Path(__file__).resolve().parents[2]


def corpus():
    adapter = RiichiEnvAdapter(seed=117)
    adapter.start()
    agents = [Tier2Agent(seed=1170 + seat) for seat in range(4)]
    observations = []
    while not adapter.done:
        pending = adapter.pending_observations
        observations.extend(pending[seat] for seat in sorted(pending))
        adapter.step({seat: agents[seat].choose_action(pending[seat]) for seat in sorted(pending)})
    # Deterministic spread over early/late rounds and response/discard turns.
    return observations[::max(1, len(observations) // 160)][:160]


def choices():
    return tuple(CpuChoice(id=i, slug=f"spike-{i}", name=f"Spike {i}", age_adult=True,
                          style="balanced", short_description="test", long_description=None,
                          profile_image_key=None, defeat_stage=(i - 1), policy_version=2,
                          effective_tier=i - 1, **dict.fromkeys(FIELDS, 1.0))
                 for i in range(1, 4))


def new_game(snapshot, *, current_setting=None, restoring=True):
    # This envelope is an isolated proof, NOT the product policy-3 loader.
    profile = snapshot["profile"] if restoring else asdict(current_setting)
    if profile not in [asdict(p) for p in PROFILES]:
        raise ValueError("unknown immutable profile")
    selected = PROFILES[profile["level"] - 1]
    def factory(choice, *, seed):
        return ProfileAgent(selected, seed=seed,
                            **{key: getattr(choice, key) for key in FIELDS})
    return create_game_session_from_choices(
        1, tuple(CpuChoice(**c) for c in snapshot["choices"]),
        seed=snapshot["seed"], agent_factory=factory)


def turn_digest(game):
    return hashlib.sha256(json.dumps(asdict(game.human_turn()), sort_keys=True).encode()).hexdigest()


def verify():
    observations = corpus()
    seed_personalities = json.loads((ROOT / "backend/app/seeds/cpu_characters.json").read_text())
    personalities = [{key: p[key] for key in FIELDS} for p in seed_personalities]
    personalities += [dict.fromkeys(FIELDS, .1), dict.fromkeys(FIELDS, 2.0)]
    results = []
    balanced_sequences = []
    for index, personality in enumerate(personalities):
        for profile in PROFILES:
            left = ProfileAgent(profile, seed=9001, **personality)
            right = ProfileAgent(profile, seed=9001, **personality)
            expert = Tier2Agent(seed=9001, policy_version=2, **personality)
            sequence = []
            discard_count = shanten_excess_sum = worse_than_min_shanten = 0
            for obs in observations:
                action = left.choose_action(obs).to_dict()
                assert action == right.choose_action(obs).to_dict()
                assert action in [a.to_dict() for a in obs.legal_actions()]
                baseline = expert.choose_action(obs).to_dict()
                if profile.level == 10:
                    assert action == baseline
                if action["type"] == int(ActionType.DISCARD):
                    discard_count += 1
                    by_tile = {}
                    for candidate in obs.legal_actions():
                        if candidate.action_type == ActionType.DISCARD:
                            hand = list(obs.hand)
                            hand.remove(candidate.tile)
                            by_tile[candidate.tile] = calculate_shanten(hand)
                    excess = by_tile[action["tile"]] - min(by_tile.values())
                    shanten_excess_sum += excess
                    worse_than_min_shanten += excess > 0
                sequence.append(action)
            for key in FIELDS:
                assert getattr(left.expert, "_" + key) == personality[key]
            if index == 0:
                balanced_sequences.append(sequence)
            results.append(dict(personality=index, level=profile.level,
                                decisions=left.decisions, lapses=left.lapses, changed=left.changed,
                                discard_count=discard_count, shanten_excess_sum=shanten_excess_sum,
                                worse_than_min_shanten=worse_than_min_shanten,
                                sequence_sha256=hashlib.sha256(json.dumps(sequence, sort_keys=True).encode()).hexdigest()))
    adjacent = [sum(a != b for a, b in zip(left, right))
                for left, right in zip(balanced_sequences, balanced_sequences[1:])]
    assert all(adjacent), adjacent
    replay = []
    for profile in PROFILES:
        snapshot = dict(seed=211, choices=[asdict(c) for c in choices()], profile=asdict(profile))
        game = new_game(snapshot, current_setting=profile, restoring=False)
        history = []
        for _ in range(12):
            assert not game.done
            history.append(0)
            game.submit_human_action(0)
        saved = json.loads(json.dumps(dict(snapshot=snapshot, human_action_indices=history)))
        # A later setting deliberately differs. Restoring uses only saved data.
        current_setting = PROFILES[10 - profile.level]
        restored = new_game(saved["snapshot"], current_setting=current_setting, restoring=True)
        assert all(agent.profile == profile for agent in restored._cpu_agents.values())
        fresh = new_game(saved["snapshot"], current_setting=current_setting, restoring=False)
        assert all(agent.profile == current_setting for agent in fresh._cpu_agents.values())
        for action_index in saved["human_action_indices"]:
            restored.submit_human_action(action_index)
        compared = 0
        while not game.done:
            assert turn_digest(game) == turn_digest(restored)
            game.submit_human_action(0)
            restored.submit_human_action(0)
            compared += 1
        assert restored.done and game.result() == restored.result()
        replay.append(dict(level=profile.level, continuation_turns=compared,
                           result=asdict(game.result()), ignored_setting_level=current_setting.level,
                           saved_profile_wins=True, fresh_uses_changed_setting=True))
    invalid = dict(snapshot["profile"], version="future-profile")
    try:
        new_game(dict(snapshot, profile=invalid), current_setting=PROFILES[0], restoring=True)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown profile accepted")
    return dict(corpus_seed=117, corpus_size=len(observations), agent_seed=9001,
                personalities=personalities, common_input=results,
                balanced_adjacent_different_actions=adjacent,
                replay_seed=211, replay=replay, unknown_profile_rejected=True)


if __name__ == "__main__":
    output = verify()
    Path(sys.argv[1]).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k: v for k, v in output.items() if k not in ("common_input", "personalities")}))
