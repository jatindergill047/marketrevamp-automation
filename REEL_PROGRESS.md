# Reels implementation progress

Opt-in only. The existing carousel and publishing path must remain unchanged until Reel functionality is independently verified.

| ID | Item | Status | Commit | Notes |
| --- | --- | --- | --- | --- |
| R1 | Config, flag, deps | BLOCKED | 10bed773, 1ca46e7 | Config and unit tests committed; pinned edge-tts resolution, requirements.lock regeneration, full suite, and pip-audit blocked by unavailable package-index access. No dependency files modified. |
| R2 | Narration builder | DONE | e5b23da, 65e2d53 | Builder and tests committed; local equivalent implementation passed 4 tests and compileall. Full repository suite not run; R1 dependency blocker remains. |
| R3 | TTS module | DONE | 88c52ab, 71da717 | Five isolated unit tests passed locally; full repository suite not run, live edge-tts unavailable until R1 dependencies are resolved. |
| R4 | 9:16 composite renderer | DONE | e2a4b1b, 56b36b9 | Three focused tests passed locally (1080x1920, foreground contrast, source preservation, invalid inputs); full repository suite remains unverified. |
| R5 | ASS captions + assembly | DOING | - | Implementing ffmpeg assembly, captions, timing, and tests |
| R6 | Cloudinary video upload | IMPLEMENTED / UNVERIFIED | ca3f3b8, 1a17bea, 4724a48 | Separate MP4 upload to /video/upload, signed/unsigned fields, HTTPS URL validation and four mocked tests committed; tests not executed. |
| R7 | Manifest reel block | IMPLEMENTED / UNVERIFIED | 99175d8, e90241d, 3740269 | Optional Reel metadata and validation committed; fallback retains legacy manifest. Tests and fingerprint integration not yet executed. |
| R8 | Fingerprint + gate extension | IMPLEMENTED / UNVERIFIED | 093324d, c1a6797, e5a9924, eebef36 | Reel URL/cover/duration/caption validation, distinct approval fingerprint, REEL_ENABLED authorization gate, and three offline tests committed. Tests not executed; R9 dispatch remains pending. |
| R9 | Publish dispatch + history | TODO | - | - |
| R10 | Workflow wiring | TODO | - | - |
| R11 | Tests | TODO | - | - |
| R12 | Docs | TODO | - | - |

## Baseline

Pending: full unittest suite cannot be run through the connected GitHub read/write API alone. No live publishing or workflow triggers authorized.
