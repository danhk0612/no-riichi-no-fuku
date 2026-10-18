# Legacy Tier2 replay fixture

`tier2_legacy_replay.json` was captured from main `e357c01` before the final-round policy
change. It uses match seed 5, the first three seeded CPU characters at stage 2 and production
CPU seeds `match_seed * 10 + seat`. The human policy is
`test_game_websocket.choose_human_action_index`.

CPU snapshots deliberately omit `policy_version`, as existing database rows do. Each turn hash
is SHA-256 of `json.dumps(asdict(game.human_turn()), sort_keys=True).encode()` before applying
that human action. There are 108 turns; final scores are `[17000, 27700, 24700, 30600]` and
ranks are `[4, 2, 3, 1]`.

This file remains an unchanged historical record. On 2026-10-18 the user waived old
behavior compatibility for the numbered-suit evaluation fix. It is no longer the active
replay expectation: the corrected evaluator diverges at zero-based human turn 55.

## Current corrected-suit replay fixture

`tier2_suit_corrected_replay.json` uses the same seed, CPU snapshots and deterministic human
policy with the corrected Tier1/2 evaluator, based on main `d04a178`. It deliberately retains
the snapshot format without `policy_version`; format loading and current-code replay remain
tested, while the old evaluator's choices are not preserved by a compatibility branch.

Capture each turn using the SHA-256 recipe above and choose each action with
`test_game_websocket.choose_human_action_index` until the corrected game finishes. The new
fixture has 82 actions, scores `[17000, 25700, 27000, 30300]`, and ranks `[4, 3, 2, 1]`.
`test_tier2_snapshot_replays_every_suit_corrected_turn` verifies every hash, replaces the
registry after 12 actions, and replays the completed result through a fresh registry.
The expected suit bonus itself is checked independently in `test_cpu_suit_evaluation.py`;
the golden replay checks determinism/persistence, not the correctness of a yaku scorer.
