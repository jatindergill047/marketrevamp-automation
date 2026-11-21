# MarketRevamp R68 — Final approved Reel design

**Visual-design decision: APPROVED (2026-11-21, America/Toronto).** This means the
look, placement, typography and subtle animation of future **review-only**
Reels are approved. It does **not** approve any individual news script, source
claim, video fingerprint, production deployment, Cloudinary upload or Instagram
publication.

## Locked design

- **Format:** 7 stories, 1080 × 1920 vertical (9:16); official
  `marketrevamp_logo_horizontal.png` at top; source attribution and
  disclaimer preserved below y=1605.
- **Headlines:** top of frame, adaptively sized to avoid overlap.
- **2D artwork:** centered at the middle of each scene. Original geometrical
  Pillow editorial illustrations are reused from the 7-slide carousel:
  `newspaper_design.illustration_topic` and
  `draw_editorial_illustration`. Select by category **and** headline, including
  cybersecurity shield, AI chip, phone, market and ledger themes. Drawings
  contain no fabricated charts, market data, quotes or prices.
- **Artwork bounds:** transparent layer 860 × 370, centered at x=110, around
  y=822. Gentle ±8 px vertical float at a 3.6-second period; **no** movement of
  headlines, subtitles, official logo, source credit or disclaimer.
- **Subtitles:** keep the real service-timed karaoke word highlighting,
  font size **80 px**, dark band `(65, 1225, 1015, 1505)`, centered
  at `(540, 1365)` **below** artwork. Source/footer stays fully separate.
- **Removed:** the legacy “THE KEY DETAIL” panel and all its text. Do not
  reintroduce it.
- **Look:** off-white paper, restrained navy/black with MarketRevamp red
  accents, subtle original two-dimensional illustrations—no 3D/flash effects.

The machine-readable contract is `R68_APPROVED_DESIGN.json`. The regression
suite `test_r68_design_contract.py` keeps these decisions explicit and fails
if major layout elements drift without a separately reviewed design revision.
The permanent review-only workflow runs those checks.

## Evidence

R68 was merged into the experimental branch in
[PR #68](https://github.com/jatindergill047/marketrevamp-automation/pull/68),
commit `4dcd52a63375dca2a7236a8ddf72ee2053a7ee46`.

Validated successfully after merge:

- [Full MP4 artwork, audio, subtitle and motion review](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44934338793)
- [Artwork and caption regression](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44934338899)
- [Broader isolated Reel opt-in tests](https://github.com/jatindergill047/marketrevamp-automation/actions/runs/44934338859)

The 77.5-second Reel used **synthetic** stories. Passing these checks verifies
the visual/technical pipeline; it is **not** approval of a real-news Reel.

## Production deployment remains a separate gate

A new publication requires a fresh seven-story dated source package,
independent editorial review, exact narration/caption/media QA, duplicate
checks against authoritative publishing history, explicit approval of the
specific release fingerprint, validated media hosting and Instagram delivery.
A separate production-reviewed change is required before recurring Reel posts.
Never infer publishing authorization from this design approval.

Keep `REEL_ENABLED=false`, `REEL_UPLOAD_ENABLED=false`,
`REEL_FIRST_LIVE_ENABLED=false` and `INSTAGRAM_PUBLISH_ENABLED=false` in
review CI. Do **not** modify existing carousel production workflows on
`main` just to finalize this design.
