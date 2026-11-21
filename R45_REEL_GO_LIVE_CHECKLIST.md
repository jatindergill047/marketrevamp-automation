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

## R46–R48 execution evidence (2026-11-20 Toronto)

- PASS: R46 Cloudinary video/upload and HTTPS playback. [Run 44835680312](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44835680312).
- PASS: R46 release/editorial/fingerprint safety tests, plus R47 nonpublishing container-unit tests. [Run 44836101211](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44836101211).
- PARTIAL: R47 Cloudinary staging stage passed; Instagram stage failed **before any steps ran**, so no Instagram Reel container was tested. Do not claim Instagram success. [Run 44836118299](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44836118299).
- PASS: R48 isolated nine-second synthetic Cloudinary sample uploaded and staging URL saved as artifact. [Run 44836583508](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44836583508). Synthetic asset is not a publishable news Reel.
- READY FOR REVIEW: [PR #60](https://github.com/jatindergill047/marketrevamp-automation/pull/60) contains one main-branch-only **manual container-processing test**. It has no `media_publish` call. It is NOT merged.
- Production `main` carousel remains unchanged; no Reel was scheduled, approved or published. The R45 news Reel remains unapproved and is dated November 20 — never reuse it on another day's schedule.

### Updated remaining release gates
1. Review and deliberately merge PR #60 (no automatic merge), then manually execute preflight on `main` with the exact Cloudinary staging URL; require `FINISHED` and no publish call.
2. Editorially approve a freshly generated, current-day seven-story news Reel; approve **all** on-screen claims, caption, audio and source URLs.
3. Upload the exact approved real Reel MP4 to Cloudinary and validate it in Instagram's Reel container.
4. Publish one controlled public Reel with an exact approval fingerprint, record the returned media ID and verify posting history/rollback.
5. Build and separately review daily new-news Reel generation, duplicate guards, monitoring and schedule; never silently re-post stale R45 material.

## R49 controlled first-live progress (2026-11-20 Toronto)

- **PASS:** [Protected-main Instagram container preflight run 44840882263](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44840882263): GitHub artifact reports `processing_status=FINISHED`, `instagram_published=false`. This validates media-container processing, **not public Reel publication**.
- **PASS:** Local R45 vs publishing-history comparison found an exact previously published Meta Muse article in the November 19 carousel. **Never publish R45 unchanged**; it also lacks editorial signoff.
- **PASS:** [R49 isolated publishing safeguards and CI](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44841732625) on the clean manual first-live branch.
- **DRAFT PR:** [#61 — manual approved first public Reel workflow](https://github.com/jatindergill047/marketrevamp-automation/pull/61). This is not merged or active, and contains no schedule. It requires an exact fingerprint, a current-day successful R50 approved package, a dedicated Cloudinary Reel video preset, and protected production credentials.
- **NO PUBLICATION:** No public Reel has been submitted. The existing daily carousel system on `main` remains unchanged.

### Next implementation work

1. Generate the R50 **fresh, dated** seven-story Reel source package with supporting citations, approved spoken scripts, and real TTS word boundaries, without auto-approving editorial claims.
2. Complete visual/source QA and obtain explicit release approval for the exact video fingerprint.
3. Configure `CLOUDINARY_REEL_UPLOAD_PRESET` in `instagram-production` for production-compatible video hosting, with verified signing and permissions.
4. Only after R50 exists and approval gates pass, review PR #61 and perform one manual controlled public Reel publication, then reconcile Instagram media ID/history.
5. Separately design and test a weekday (or user-approved daily) schedule using current-day news, fail-closed freshness checks, and duplicate protection.
