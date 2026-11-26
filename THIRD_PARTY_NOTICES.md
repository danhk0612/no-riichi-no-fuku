# Third-Party Notices

The Windows player ZIP includes Electron’s license and Chromium notices at its root.
Under `resources/app/notices/`, `frontend-licenses.md` lists modules bundled by Vite,
`Python-LICENSE.txt` comes from the build interpreter, and `engine-packages.txt`
lists installed Python distributions matched to the PyInstaller analysis and the
number of notice files copied from each. Package subdirectories retain the
original notices. Native libraries can have additional upstream notices.

The player includes the mahjong tile artwork. Character images are generated on
the user's PC. No character image pack, model weights or LoRAs ship with the player.

## RiichiEnv

- Project: https://github.com/smly/RiichiEnv
- License: Apache License 2.0
- Version: 0.4.8

Before a release, verify the exact dependency tree and include every notice/license required by the versions actually shipped in the Docker images.
