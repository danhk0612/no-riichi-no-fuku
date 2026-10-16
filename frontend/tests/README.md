# Table browser regression

This check runs the real React client in Chromium and supplies REST/WebSocket responses through
Playwright routing. It verifies message-to-screen behavior, not backend game simulation.

Use Node.js with Playwright and its Chromium browser installed in the test environment. No
production dependency is added. If Playwright is outside this project, set
`PLAYWRIGHT_MODULE_PATH` to its package directory. An existing Chromium executable can be supplied
with `TEST_CHROMIUM_EXECUTABLE`.

From `frontend`, start Vite in one terminal:

```sh
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Run the check in another terminal:

```sh
node tests/dialogue.browser.mjs
node tests/connection.browser.mjs
node tests/result-asset.browser.mjs
node tests/local-sound.browser.mjs
node tests/local-content.browser.mjs
```

For a different Vite address, set `TEST_BASE_URL`.

Covered sequences: dialogue before the first turn, preservation on the next turn, immediate
dialogue updates on an existing turn, latest line per CPU seat, and empty dialogue history when
starting the next match. No media files are created.

Also covers server-supplied melds at all four seats: three-tile calls, open/concealed kans,
red fives, honor tiles, multiple groups, turn replacement and new-round clearing. Checks page
overflow at desktop and mobile widths. These fixtures verify rendering, not engine rules.
Round labels cover East 1, East 4 with two honba and South 1 using the server kyoku index.

Result checks cover CPU defeat, a player loss with HP remaining and server-declared game over:
ordinary results keep the next-match loop, while game over shows the notice and final scores
without a next-match button. Progress reset and HP recovery policies are not implemented here.

`connection.browser.mjs` checks unfinished WebSocket closure with codes 1000 and 1011:
controls lock and the refresh/re-login recovery notice appears. Refresh and login discover the
same active session; the next action uses the restored server action version. It uses routed
REST/WebSocket fixtures rather than a real server restart.

`result-asset.browser.mjs` uses metadata and HTTP 503 responses without image files. It checks
that CG failure replaces the loading message while scores/next-match controls remain available,
and that a failed asset response arriving after next-match selection cannot display an old error.

`local-sound.browser.mjs` uses the real desktop-mode React renderer with routed REST/WebSocket
fixtures and mock `Audio`. It checks one-track BGM repeat, preserving the active track through
order changes, stale `ended` and media-load callbacks, media replacement for the same track ID,
recovery after file/autoplay failures, clearing inactive sound references, and a committed final SFX
that resolves after `match_complete`. Duplicate/replayed event identities stay silent; no audio
content is generated.

`local-content.browser.mjs` checks the desktop character editor using routed REST responses. It covers
dirty-only and explicit empty saves, failure/conflict draft preservation, delayed save responses,
late character loads/saves, and deduplicating an in-flight scan when returning to the pack tab.
It generates no prompt content or media. W05 runs it with the existing Playwright/Vite setup.

## Real-server browser integration

`live-game.browser.mjs` starts its own FastAPI and Vite processes, applies real Alembic
migrations to a temporary SQLite database and removes the database/processes on completion.
Ports 8000 and 5193 must be unused; it refuses to reuse an existing service. Install backend
dependencies in a Python environment and run `npm ci` before this test.

```sh
TEST_PYTHON=/path/to/backend-venv/bin/python node tests/live-game.browser.mjs
```

Use the same `PLAYWRIGHT_MODULE_PATH` and `TEST_CHROMIUM_EXECUTABLE` environment options as
the other browser checks if needed. This test manages its own servers; no separate Vite is needed.

It signs up through the UI, seeds stage 2 progress only in its temporary test DB, logs in again,
selects three production Tier2 CPUs (policy 2), and plays a seed 5 match through actual DOM
controls and the Vite REST/WebSocket proxy. It restarts the API process after 12 accepted actions,
refreshes/re-logs in, and compares the entire restored turn and session URL. After completion it
compares result/HP/progress to DB rows, restarts the API again, reopens the completed session,
and verifies that its response and DB settlement remain unchanged before returning to selection.

No REST/WebSocket responses are mocked. Test seed injection fixes only the registry's match seed;
production agents, game rules, auth, migrations and persistence code are used. No images are
created. This is direct FastAPI/Vite with SQLite, not Docker/nginx/PostgreSQL or a power-loss test.
