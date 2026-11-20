# MarketRevamp Reels — R45 Go-Live Gate

Date: 2026-11-20 (America/Toronto). This file is an operational record, **not** publication approval.

## Confirmed

- User selected R44 Microsoft **en-US-AndrewNeural** narration voice; feature-branch config and tests were updated.
- Latest feature-branch opt-in validation run `44832781627`: **success**.
- R45 local release-candidate render: 1080×1920 H.264/AAC MP4, 82.4 seconds, seven scenes, 194 speech-service word timing events.
- Official MarketRevamp logo artwork included and R44 editorial-preview / not-approved on-video text removed in the local R45 render.
- Seven R44 source stories were checked against current reporting; the Bitcoin exact dollar price remains omitted.
- Connected Metricool brand: `marketrevampdaily` (`7354494`), timezone America/Toronto; no upcoming posts scheduled in Metricool for November 20–December 3.
- Existing `main` workflow is a **weekday carousel** pipeline, not a scheduled Reel pipeline.

## MUST PASS before unattended daily Instagram Reels

1. **Final story QA:** Review visible headlines, context text, speech, and source links against current-day articles. Flag reported allegations as allegations. Do not reuse the November 20 package on another day.
2. **Asset QA:** Readable phone-size captions, proper safe zones, original logo, accessible contrast, normal playback and audio level, source licensing and correct AI-generated-media disclosure.
3. **Public video hosting:** Upload the finalized MP4 to a compatible HTTPS video host with appropriate account authorization; confirm URL, processing and playback on Instagram/Metricool. A ChatGPT sandbox link is not a public media URL.
4. **One controlled Instagram Reel delivery:** Test upload/publish on connected account. Confirm Instagram media ID, caption, soundtrack, thumbnail, account and time. Store posting evidence in publishing history and verify no duplicate.
5. **Daily content generation:** Build a fresh dated Reel from seven source-checked stories each publication day (including weekends if daily is the chosen cadence). Use Andrew Neural, real speech WordBoundary timestamps, approved logo and template.
6. **Safety gates:** Fail closed for missing/uncertain sources, unapproved scripts, stale dates, missing video/audio, failed media processing or unclear publish status. Prevent duplicate Instagram posts and avoid repeated retries without checking history.
7. **Rollout:** Deploy via a separately reviewed PR only after the above passes; keep the established carousel publisher unchanged. Record rollback procedure and monitor the first several real runs.

## Current decision

**NO-GO for unattended recurring Reel publication.** The user has authorized working toward daily Instagram posting, but neither future daily story QA nor production Reel posting has been validated. Do not interpret successful feature-branch CI or a local review MP4 as proof of live publication. Keep Reel publish/upload flags disabled in all review CI.

## Links

- Reel opt-in validation: https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44832781627
- R44 successful neural-voice job: https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44830089082
