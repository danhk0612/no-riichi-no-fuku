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
```

For a different Vite address, set `TEST_BASE_URL`.

Covered sequences: dialogue before the first turn, preservation on the next turn, immediate
dialogue updates on an existing turn, latest line per CPU seat, and empty dialogue history when
starting the next match. No media files are created.

Also covers server-supplied melds at all four seats: three-tile calls, open/concealed kans,
red fives, honor tiles, multiple groups, turn replacement and new-round clearing. Checks page
overflow at desktop and mobile widths. These fixtures verify rendering, not engine rules.
