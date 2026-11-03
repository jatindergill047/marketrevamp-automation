# Reels implementation progress

Opt-in only. The existing carousel and publishing path must remain unchanged until Reel functionality is independently verified.

| ID | Item | Status | Commit | Notes |
| --- | --- | --- | --- | --- |
| R1 | Config, flag, deps | BLOCKED | 10bed773, 1ca46e7 | Config and unit tests committed; pinned edge-tts resolution, requirements.lock regeneration, full suite, and pip-audit blocked by unavailable package-index access. No dependency files modified. |
| R2 | Narration builder | TODO | - | - |
| R3 | TTS module | TODO | - | - |
| R4 | 9:16 composite renderer | TODO | - | - |
| R5 | ASS captions + assembly | TODO | - | - |
| R6 | Cloudinary video upload | TODO | - | - |
| R7 | Manifest reel block | TODO | - | - |
| R8 | Fingerprint + gate extension | TODO | - | - |
| R9 | Publish dispatch + history | TODO | - | - |
| R10 | Workflow wiring | TODO | - | - |
| R11 | Tests | TODO | - | - |
| R12 | Docs | TODO | - | - |

## Baseline

Pending: full unittest suite cannot be run through the connected GitHub read/write API alone. No live publishing or workflow triggers authorized.
