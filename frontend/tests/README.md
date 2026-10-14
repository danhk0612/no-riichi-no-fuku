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
