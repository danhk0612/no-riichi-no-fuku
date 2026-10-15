"""Run the reproducible RiichiEnv 0.4.8 East-only match spike."""

from __future__ import annotations

import json
import random
from collections import Counter
from importlib.metadata import version

import riichienv.convert as convert
from riichienv import Action, ActionType, GameRule, RiichiEnv, calculate_shanten


EXPECTED_VERSION = "0.4.8"
GAME_MODE = "4p-red-east"
SEED = 5


def choose_action(observation, rng: random.Random) -> Action:
    legal_actions = observation.legal_actions()

    for action_type in (ActionType.TSUMO, ActionType.RON, ActionType.RIICHI):
        for action in legal_actions:
            if action.action_type == action_type:
                return action

    for action in legal_actions:
        if action.action_type == ActionType.PASS:
            return action

    discards = [
        action for action in legal_actions if action.action_type == ActionType.DISCARD
    ]
    if discards:
        scored_discards = []
        for action in discards:
            hand_after_discard = list(observation.hand)
            hand_after_discard.remove(action.tile)
            scored_discards.append(
                (calculate_shanten(hand_after_discard), rng.random(), action)
            )
        return min(scored_discards, key=lambda candidate: candidate[:2])[2]

    return rng.choice(legal_actions)


def main() -> None:
    installed_version = version("riichienv")
    if installed_version != EXPECTED_VERSION:
        raise RuntimeError(
            f"expected RiichiEnv {EXPECTED_VERSION}, got {installed_version}"
        )

    rule = GameRule.default_tenhou()
    env = RiichiEnv(game_mode=GAME_MODE, seed=SEED, rule=rule)
    observations = env.reset()

    all_tiles = [tile for hand in env.hands for tile in hand] + list(env.wall)
    red_tiles = Counter(
        convert.tid_to_mjai(tile)
        for tile in all_tiles
        if convert.tid_to_mjai(tile).endswith("r")
    )

    rng_by_seat = {seat: random.Random(SEED * 10 + seat) for seat in range(4)}
    controller_by_seat = {
        0: "human-seat-adapter (automated for this spike)",
        1: "cpu-agent",
        2: "cpu-agent",
        3: "cpu-agent",
    }
    controlled_seats: set[int] = set()
    action_types: set[str] = set()
    first_observation = None
    steps = 0

    while not env.done():
        if not observations:
            raise RuntimeError("match is unfinished but no seat can act")

        actions = {}
        for seat, observation in observations.items():
            if observation.player_id != seat:
                raise RuntimeError("observation was returned for the wrong seat")
            controlled_seats.add(seat)
            if first_observation is None:
                first_observation = observation.to_dict()
            action = choose_action(observation, rng_by_seat[seat])
            action_types.add(str(action.action_type))
            actions[seat] = action

        observations = env.step(actions)
        steps += 1
        if steps > 5_000:
            raise RuntimeError("match exceeded the spike step limit")

    if controlled_seats != {0, 1, 2, 3}:
        raise RuntimeError(f"not every seat was controlled: {controlled_seats}")
    if first_observation is None:
        raise RuntimeError("no observation was returned")

    event_counts = Counter(event["type"] for event in env.mjai_log)
    rounds = [event for event in env.mjai_log if event["type"] == "start_kyoku"]
    result = {
        "riichienv_version": installed_version,
        "initialization": (
            'RiichiEnv(game_mode="4p-red-east", '
            "rule=GameRule.default_tenhou())"
        ),
        "game_mode_value": env.game_mode,
        "controllers": controller_by_seat,
        "controlled_seats": sorted(controlled_seats),
        "steps": steps,
        "round_count": len(rounds),
        "last_round": {
            key: rounds[-1][key]
            for key in ("bakaze", "kyoku", "honba", "oya", "scores")
        },
        "scores": env.scores(),
        "ranks": env.ranks(),
        "event_counts": dict(sorted(event_counts.items())),
        "selected_action_types": sorted(action_types),
        "red_tiles": dict(sorted(red_tiles.items())),
        "observation_keys": sorted(first_observation),
        "legal_action_keys": sorted(first_observation["legal_actions"][0]),
        "tenhou_rule": {
            name: getattr(rule, name)
            for name in (
                "allows_ron_on_ankan_for_kokushi_musou",
                "is_kokushi_musou_13machi_double",
                "is_suuankou_tanki_double",
                "is_junsei_chuurenpoutou_double",
                "is_daisuushii_double",
                "yakuman_pao_is_liability_only",
                "sanchaho_is_draw",
                "kuikae_forbidden",
            )
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
