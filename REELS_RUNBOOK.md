# MarketRevamp optional Reels — R12 operator runbook

**Status: feature-branch experiment; NOT approved for live Instagram publishing.**
This runbook applies to `feature/reels-opt-in` only. The existing production carousel pipeline on `main` remains the default and must not be changed by Reel validation.

## Architecture and data flow

1. `news_results.json` must contain exactly seven `selected_stories`, each with `title` and `summary`.
2. `reel_script.py` produces seven narration texts.
3. `reel_frames.py` composites `instagram_images/slide_01.png` through `slide_07.png` into 1080×1920 frames.
4. `tts.py` synthesizes each narration with optional `edge-tts` (voice configured in `reel_config.py`).
5. `build_reel.py` uses FFmpeg/FFprobe to create H.264/AAC `reel_output/marketrevamp_reel.mp4`, captions, and `reel_segments.json`.
6. `reel_cloudinary.py` can upload MP4 media to Cloudinary **only when independently opted in**. Upload metadata is written to `cloudinary_reel_upload.json`.
7. `reel_manifest.py`, `reel_security.py`, and `reel_publish.py` validate Reel metadata, fingerprint, and payload. `publish_instagram.py` is the existing publishing entry point; **do not invoke it during validation**.

The Reel workflow is separate from the existing seven-card carousel preparation, approval, publishing history, and production schedules.

## Dependencies and environment

Use Python 3.12, install `requirements.lock` and the separate optional `requirements.reel.txt` (currently pins `edge-tts==7.3.1`), and install system `ffmpeg` including `ffprobe`. Do not edit the production dependency lock as part of this experiment. FFmpeg must support `libx264`, AAC and ASS subtitle rendering.

| Variable | Default / handling | Purpose |
| --- | --- | --- |
| `REEL_ENABLED` | `false`; only literal `true` opts in | Allow optional Reel preparation |
| `REEL_UPLOAD_ENABLED` | `false`; keep off for offline tests | Allow optional Cloudinary upload after render |
| `INSTAGRAM_PUBLISH_ENABLED` | `false` in Reel CI; never enable in tests | Existing Instagram publishing gate |
| `CLOUDINARY_CLOUD_NAME` | Unset | Required only for authorized staging upload |
| `CLOUDINARY_UPLOAD_PRESET` | Unset | Required only for authorized staging upload |
| `CLOUDINARY_API_KEY` | Unset | Optional signed upload credentials |
| `CLOUDINARY_API_SECRET` | Unset | Optional signed upload credentials; secret, never log |

Never store credentials in the repository, test fixtures, artifacts, PR comments, or logs. Staging credentials must be scoped to a separate nonproduction Cloudinary account/preset, not the production upload configuration.

## Safe local validation

Run from the repository root with publishing and upload flags disabled:

```bash
export REEL_ENABLED=false REEL_UPLOAD_ENABLED=false INSTAGRAM_PUBLISH_ENABLED=false
python -m unittest -v test_reel_config.py test_reel_script.py test_tts.py test_reel_frames.py test_build_reel.py test_reel_cloudinary.py test_reel_manifest.py test_reel_security.py test_reel_publish.py test_prepare_reel.py test_reel_recovery.py
python -m unittest -v test_auto_publish_gate.py test_reliability.py test_publish_retry.py
python test_publishing_flow.py
python -m unittest -v test_reel_integration.py
python prepare_reel.py
```

The integration test synthesizes seven silent test audio clips and sample artwork, renders an actual 1080×1920 MP4, checks audio/video with FFprobe, and mocks the Cloudinary HTTP response. It **does not** validate natural voice quality or perform a real Cloudinary upload. Test output must never be published as real news.

For a separate, explicitly authorized voice-quality review, use non-news sample text and a controlled temporary directory. This requires network access to the external TTS provider and is **not** part of offline CI. Inspect pronunciation, audio duration, caption synchronization, and licensing/terms before release.

## Cloudinary staging verification (NOT yet performed)

Prerequisites: explicitly authorized nonproduction Cloudinary credentials/preset, test-only MP4, and confirmation that uploading media incurs acceptable costs. Keep `INSTAGRAM_PUBLISH_ENABLED=false` throughout. Upload only to the staging account with `reel_cloudinary.upload_video`; validate the returned HTTPS `res.cloudinary.com/.../video/upload/...mp4` URL, `resource_type=video`, playback, file size, and segment metadata. Record a redacted result, delete staging media after review according to retention policy, and do not connect the URL to Instagram. Do not run this step using production secrets by default.

## Failure handling, safety, and rollback

- Fail closed on missing stories, frames, audio, FFmpeg, invalid timing, invalid Cloudinary URLs, or TTS/upload errors. Do not treat a failed Reel as authorization to retry Instagram publishing.
- `test_reel_recovery.py` injects frame, TTS, render, and upload errors and asserts the existing carousel fixture remains unchanged. This is an isolation regression, **not** a proof that every possible production failure is handled.
- Never enable Reel flags in the production scheduled workflows as a side effect of testing. Never run `publish_instagram.py` from the Reel validation workflow.
- If a Reel test fails: leave `REEL_ENABLED=false`, `REEL_UPLOAD_ENABLED=false`, `INSTAGRAM_PUBLISH_ENABLED=false`; inspect GitHub Actions logs and correct the feature branch. Stop any staging uploads.
- Rollback before merge: abandon or revert the feature branch/PR. Rollback after any separately approved deployment: disable the Reel flags, stop any Reel-specific job, and retain the original carousel manifest, approval fingerprint and publishing-history state. Never erase history to force a retry.
- If an Instagram publication outcome is ambiguous, use existing history/duplicate guards and inspect remote state; **do not blindly republish**.

## Launch gates — all required

- [x] Feature branch CI: synthetic seven-segment MP4 with FFprobe audio/video validation (run 41696872019).
- [x] Feature branch CI: 36 Reel safety/recovery tests and 18 carousel regression tests (run 41696872019).
- [x] Disabled Reel path verified; no Instagram publishing invoked in the feature-branch CI.
- [ ] Real TTS narration generated and manually reviewed for pronunciation and synchronization.
- [ ] Authorized nonproduction Cloudinary MP4 upload and playback independently verified.
- [ ] Final visual QA on real 9:16 Reel: safe areas, caption legibility, logo, pacing, accessibility and factual/source review.
- [ ] Dependency security audit and complete repository-wide regression suite reviewed.
- [ ] Explicit human approval of any production deployment and Instagram publishing; separate PR and release plan.

**Do not describe the Reel feature as production-ready while any unchecked gate remains.**

## Final CI evidence

See `.github/workflows/reel-opt-in-validation.yml` and GitHub Actions on `feature/reels-opt-in`. That workflow is validation-only, sets all publishing/upload flags false, installs FFmpeg, runs offline unit/regression and video integration tests, and never invokes an Instagram publishing command.
