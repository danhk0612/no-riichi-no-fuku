# Work Handoff

## Current status

GitHub bootstrap is complete. No feature implementation beyond the minimal Docker/API/frontend scaffold has been started.

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

## Not verified in this environment

- Full `npm install` / frontend build: dependency installation exceeded the execution time limit.
- Full `docker compose build/up`: Docker runtime was not available in the current execution environment.
- RiichiEnv runtime integration/API: intentionally deferred to the first Work spike.

These are the first Work's verification tasks, not assumed working facts.

## First Work entry point

Read:

1. `AGENTS.md`
2. `docs/WORK_INSTRUCTIONS.md`
3. `docs/WORK_START.md`
4. GitHub issue `Bootstrap validation + RiichiEnv 0.4.8 spike`

Do not begin CG generation or add CG binaries to the repository.
