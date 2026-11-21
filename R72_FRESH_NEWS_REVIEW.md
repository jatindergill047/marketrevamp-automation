# R72 — Fresh daily Reel review integration

**Status:** Source-to-template implementation verified by offline GitHub CI;
**real current-news end-to-end run pending** a weekday source fetch. The
approved R71 Reel design is unchanged.

## What is integrated

1. **R67 collector** reads current publisher RSS, extracts/validates article
   text, selects exactly seven distinct source-screened stories and rejects
   canonical article links already present in `publishing-history` branch.
   The collector now receives the exact authoritative history file path.
2. **R72 adapter** revalidates the R67 result: it must be from **today in
   America/Toronto**, every day including weekends, within the recent-article window, sourced
   from reviewed publisher domains, have at least three topic categories, and
   remain editorially unapproved.
3. Narration takes exact source headlines with explicit publisher attribution
   and may add **complete** source-extracted summary sentences only where they
   fit the speech budget. It **never** invents a fact or assertion of
   independent fact checking. If a sufficient complete script cannot fit, it
   refuses to create a Reel.
4. The existing R71 review renderer creates the 9:16 Reel with
   `Here's what's making headlines today.`, seven animated 2D-artwork stories
   with source credits and 80px word-aligned subtitles, and the unchanged
   Follow MarketRevamp closing line. Duration must be 45–90 seconds.
5. Review assets include a caption ASS file, source URLs, editorial-pending
   scripts, an artwork contact sheet, QA JSON and optional H264/AAC MP4.

## Safety

- **No public upload, no automatic editorial approval, no Instagram
  publication.** Flags remain disabled in GitHub review workflows.
- A publisher-text-matched summary is **not independently fact-checked**.
  Sources, spoken claims, currency figures and editorial impact still need
  human review for the particular date and exact Reel.
- Failing a feed, insufficient fresh eligible candidates, source extraction,
  publishing-history access, timing or other gates ends in **no output that
  authorizes publishing**. There is no automatic retry of a public post.
- The existing Instagram carousel production workflow is unchanged.
- Historical date-bound R50/R52 review scripts retain their own restrictions;
  R72 is a new entry point, never a silent replacement of old stories.

## Running a future review

An operator may run `python r67_weekday_news.py
--history publishing-history/instagram_publish_history.json`, then

```sh
python reel_r72_review.py \
  --sources r67_review/review_sources.json \
  --history publishing-history/instagram_publish_history.json \
  --output-dir r72_review
```

This must run on any day, including Saturday and Sunday, after reading the latest authenticated history
from `publishing-history`. The R72 GitHub workflow's **push** event runs
synthetic/offline safeguards only. Its review job is gated to a manual dispatch
and the current Toronto date; a scheduled workflow on a feature-only branch would
**not** run from GitHub's default-branch scheduler. A future separately
reviewed default-branch entry point can enable manually triggered or scheduled
real-news *review* generation. No production Reel publisher has been activated.

## Release prerequisites still open

- Successfully render and inspect an exact *fresh-news* Reel with real TTS
  word boundaries and phone-readable captions.
- Independently verify and approve all seven stories, script, voice, claims,
  sources and timestamp for the exact news date.
- Confirm Cloudinary/Instagram processing with the actual approved media,
  approval fingerprint, history and de-duplication.
- Only then make a separately authorized first public Reel delivery; separately
  consider recurring weekday publishing.

**Do not treat this feature as an authorization to publish.**
