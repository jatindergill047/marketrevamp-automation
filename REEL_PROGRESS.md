# Reels implementation progress

Opt-in only. The existing carousel and publishing path must remain unchanged until Reel functionality is independently verified.

| ID | Item | Status | Commit | Notes |
| --- | --- | --- | --- | --- |
| R1 | Config, flag, deps | PARTIAL | 10bed773, 1ca46e7 | Config and unit tests committed; pinned edge-tts resolution, requirements.lock regeneration, full suite, and pip-audit blocked by unavailable package-index access. No dependency files modified. |
| R2 | Narration builder | DONE | e5b23da, 65e2d53 | Builder and tests committed; local equivalent implementation passed 4 tests and compileall. Full repository suite not run; R1 dependency blocker remains. |
| R3 | TTS module | DONE | 88c52ab, 71da717 | Five isolated unit tests passed locally; full repository suite not run, live edge-tts unavailable until R1 dependencies are resolved. |
| R4 | 9:16 composite renderer | DONE | e2a4b1b, 56b36b9 | Three focused tests passed locally (1080x1920, foreground contrast, source preservation, invalid inputs); full repository suite remains unverified. |
| R5 | ASS captions + assembly | DOING | - | Implementing ffmpeg assembly, captions, timing, and tests |
| R6 | Cloudinary video upload | IMPLEMENTED / UNVERIFIED | ca3f3b8, 1a17bea, 4724a48 | Separate MP4 upload to /video/upload, signed/unsigned fields, HTTPS URL validation and four mocked tests committed; tests not executed. |
| R7 | Manifest reel block | IMPLEMENTED / UNVERIFIED | 99175d8, e90241d, 3740269 | Optional Reel metadata and validation committed; fallback retains legacy manifest. Tests and fingerprint integration not yet executed. |
| R8 | Fingerprint + gate extension | IMPLEMENTED / UNVERIFIED | 093324d, c1a6797, e5a9924, eebef36 | Reel URL/cover/duration/caption validation, distinct approval fingerprint, REEL_ENABLED authorization gate, and three offline tests committed. Tests not executed; R9 dispatch remains pending. |
| R9 | Publish dispatch + history | IMPLEMENTED / UNVERIFIED | db20e0b, 80ed106, ea30acf, 0b8227b, 5e8c702 | Opt-in REELS container dispatch and existing publish/history checkpoints integrated; carousel path retained. Tests not executed; no live publish. |
| R10 | Workflow wiring | IMPLEMENTED / CI PENDING | 1a403fb, 837f886, 9442bdc, f1c5e5a, 738de8b, 6300a10, 04a3c0d, 786c532 | Isolated opt-in orchestrator, optional TTS pin and feature-branch push CI for offline Reel/carousel tests. No production workflows changed; no CI result observed; end-to-end render, Cloudinary upload and transitive lock unverified. |
| R11 | Tests | OFFLINE VERIFIED / EXTERNAL STAGING BLOCKED | 063d386, f12b696, 0a4bca7, e22b115, 8569bc1 | GitHub Actions run 41696872019 passed: 36 Reel safety/recovery tests (including four injected failures), 18 carousel regression tests, actual seven-segment 1080x1920 MP4 with audio/ffprobe, mocked Cloudinary upload and manifest. Live edge-TTS and credentialed Cloudinary staging are NOT verified; require separate external access. No Instagram publishing. |
| R12 | Docs | CI VERIFIED | 3cebe81, 0edd065, 83385b1, f26da34 | Documentation and safety validation passed GitHub Actions run 41697367041. No production changes. |
| R13 | Staging validation | IN PROGRESS | 21b860d, 6eaf4e8 | CI attempts actual edge-tts voice generation and seven-scene MP4 rendering with FFprobe in isolated temporary files. External voice outcome pending. Cloudinary staging credentials are not accessible through available GitHub tooling; no upload authorized to production. No Instagram publishing. |

## Baseline

Pending: full unittest suite cannot be run through the connected GitHub read/write API alone. No live publishing or workflow triggers authorized.
