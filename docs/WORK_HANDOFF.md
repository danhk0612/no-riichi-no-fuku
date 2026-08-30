# Work Handoff

## Current status

GitHub bootstrap and the RiichiEnv 0.4.8 spike are complete. Backend settings, initial
database models, Alembic migrations, superadmin bootstrap, CPU seed path, authentication and
member name profile APIs are implemented. Superadmin authorization and member/CPU/dialogue
management foundation APIs are also implemented. The RiichiEnv adapter, MahjongAgent boundary
and process-local authoritative game session foundation are implemented. A minimal React Mahjong
table renders HumanTurn data, legal actions and match results without image assets. The production
Tier 0 CPU uses shanten, approximate ukeire, a weak riichi-genbutsu bias and seeded weighted
selection. Completed authoritative sessions settle exactly one fourth-place outcome: player HP
or the mapped user's CPU progress. New members start with current/max HP 3 and stage 0 progress
for every seeded CPU. Docker/Compose runtime validation is intentionally deferred to the final
integration stage.

Repository:

```text
danhk0612/no-riichi-no-fuku
```

## Verified before handoff

- GitHub root/docs/backend/frontend files are present on `main`.
- Python `backend/app/main.py` syntax check passed.
- `backend/app/seeds/cpu_characters.json` parses correctly.
- Initial CPU seed count: 6.
- All initial CPU seed entries explicitly mark the character as adult.
- A local metadata-only `pip install . --no-deps --no-build-isolation` check for the backend project succeeded.
- RiichiEnv 0.4.8 current PyPI release and Apache-2.0 license were rechecked on 2026-08-29.
- Mortal code license was rechecked as AGPL-3.0-or-later.

## Verified in the first Work

- Backend dependency installation and direct `/api/health` response.
- Frontend production build.
- RiichiEnv 0.4.8 four-seat East-only match completion.
- Actual initialization, observation/action structure, red fives, termination and rank behavior
  are recorded in `docs/DECISIONS.md`.
- Initial migration upgrade/downgrade and schema drift check on SQLite.
- Idempotent superadmin/CPU seed bootstrap tests.
- Member registration, login, authenticated profile read/name update and password change tests.
- Superadmin initial-password flag and verified password-change transition tests.
- Initial/max HP 3 migration, including SQLite round-trip and PostgreSQL offline SQL generation.
- Superadmin access denial before the initial password change and member access denial.
- Member listing/activation, CPU create/update and dialogue CRUD API tests.
- New CPU creation adds stage 0 progress for every existing member.
- RiichiEnv adapter rejects missing or illegal seat actions before calling the engine.
- A fixed-seed authoritative session completed in 300 steps with all three injected CPU agents.
- Human turns expose seat 0 observation/legal actions while other seats' hands remain hidden.
- Frontend TypeScript production build with HumanTurn/action types and tile-id conversion.
- Responsive four-seat table, scores, discards, hand actions, dora and result components.
- Tier 0 prioritizes wins/riichi, filters discards by shanten and approximate ukeire, and only
  calls when shanten improves.
- A fixed-seed authoritative match with three production Tier 0 agents completed in 381 steps;
  final scores `(18600, 37000, 26600, 17800)`, ranks `(3, 1, 2, 4)`.
- Completed server sessions decrement only player HP when seat 0 is fourth, or increment only the
  mapped user's CPU defeat stage when a CPU seat is fourth.
- HP 0, completed stage 3 and duplicate process-local settlement boundaries are rejected.

## Deferred to final integration

- `docker compose config/build/up`
- Web root and nginx-proxied `/api/health`
- PostgreSQL container health
- `postgres_data` and `media_data` persistence

These remain unverified until the final Docker integration task succeeds.

## Next entry point

Read:

1. `AGENTS.md`
2. `docs/WORK_INSTRUCTIONS.md`
3. `docs/WORK_START.md`
4. CPU selection and replay loop foundation

Profile/CPU image upload requirements remain undecided. Do not implement that media path or
begin CG generation, and do not add CG binaries to the repository.
