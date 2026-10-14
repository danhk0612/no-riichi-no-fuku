# Legacy Tier2 replay fixture

`tier2_legacy_replay.json` was captured from main `e357c01` before the final-round policy
change. It uses match seed 5, the first three seeded CPU characters at stage 2 and production
CPU seeds `match_seed * 10 + seat`. The human policy is
`test_game_websocket.choose_human_action_index`.

CPU snapshots deliberately omit `policy_version`, as existing database rows do. Each turn hash
is SHA-256 of `json.dumps(asdict(game.human_turn()), sort_keys=True).encode()` before applying
that human action. There are 108 turns; final scores are `[17000, 27700, 24700, 30600]` and
ranks are `[4, 2, 3, 1]`.

Do not regenerate this fixture with the current policy. It preserves the pre-change replay
contract, including a mid-match registry replacement and final replay in the integration test.
