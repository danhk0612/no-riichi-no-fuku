# Work Handoff

## Current status

GitHub bootstrap and the RiichiEnv 0.4.8 spike are complete. Docker/Compose runtime
validation is intentionally deferred to the final integration stage.

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
4. Backend foundation: settings, database models, Alembic, superadmin bootstrap and CPU seed path

Do not begin CG generation or add CG binaries to the repository.
