# R14 Launch-readiness assessment (feature branch only)

Status: **NOT READY FOR PRODUCTION**. The R14 preview workflow generates a fictional editorial demo and exports a short-lived review artifact; successful CI does not equal human editorial approval.

## Verified before R14
- R13 GitHub Actions run 41697885025: seven real edge-tts voices and an actual H.264/AAC 1080x1920 sample with captions.
- Cloudinary staging run 41708205381: signed upload and HTTP playback succeeded for **one synthetic test video**.
- Production main and Instagram publishing remain unchanged and disabled for these tests.

## R14 automated checks
- Fictional seven-story preview; each scene uses existing slide composer, voice, zoompan, ASS subtitles.
- FFprobe validates codec and 1080x1920 output; segment metadata checks continuity and narration length.
- CI uploads a preview MP4, contact sheet, timing JSON, and QA report as a GitHub Actions artifact (not Cloudinary).
- CI run result and artifact must be inspected before marking R14 automated verification complete.

## Open launch blockers
1. Human watch/listen review of the actual MP4 for pronunciation, audible silence, subtitle timing and readability, and pacing.
2. Official MarketRevamp logo is **not** embedded/verified in the R14 demo; its header is a text placeholder.
3. No crossfade or editorial transition system has been implemented; current scenes cut between gentle zoompan clips.
4. Safe-area legibility and accessibility require visual review on a phone.
5. Demo headlines are fictional; real-story facts, sourcing and approvals remain unverified.
6. Full repository-wide dependency audit and production readiness review remain outstanding.
7. No permission to publish Instagram or upload additional videos. Do not enable publishing flags.

## Release gate
Keep REEL_ENABLED, REEL_UPLOAD_ENABLED, INSTAGRAM_PUBLISH_ENABLED false for validation. Require explicit approval and a separate deployment plan before production.
