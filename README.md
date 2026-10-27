# MarketRevamp Automation

Automated **seven-slide** editorial Instagram news carousel for @marketrevampdaily. The pipeline is source-extractive and does **not** use a paid image or language-model API. Summaries are source-grounded but **not independently fact-checked**.

## Weekday schedule reliability (effective October 26, 2026)

GitHub-hosted scheduled workflows can occasionally be delayed or omitted,
especially near the start of an hour. MarketRevamp now attempts preparation
at **18:13 Toronto** and again at **19:13 Toronto** Monday–Friday. UTC
expressions are set for both Eastern daylight and standard time, including
the Tue–Sat UTC crossover in winter. `schedule_guard.py` validates each
originating cron against the intended Toronto-local weekday; extra UTC
triggers cannot publish an unrelated or weekend batch. Automatic Instagram
publishing reuses the existing same-day history/fingerprint/duplicate locks,
so a successful first slot cannot be posted twice by the backup slot.

The missed Monday, October 26 carousel is recovered by a dedicated
`.github/marketrevamp-live-20261026.trigger` push with seven standard
news cards. It is valid **only on October 26 Toronto time** and cannot
recur on later days. The October 25 quote-first publication remains a
separate expired one-shot; recurring weekday cards are not switched to
quote mode. Both production workflows remain separate from test fixtures.

## Architecture

Weekday GitHub Actions production workflow (`.github/workflows/marketrevamp.yml`) checks the Toronto publishing window, restores the persistent history checkout, installs Python dependencies/fonts, runs safeguards, collects recent RSS news, selects seven distinct stories, renders 1080×1350 newspaper-style cards, uploads images to Cloudinary, prepares the carousel manifest, and saves artifacts for human review. Scheduled preparation runs never call Instagram directly. The `.github/workflows/publish-automatic.yml` workflow now automatically publishes a successful same-day scheduled artifact using configured production credentials; the separate `.github/workflows/publish-approved.yml` remains available for manually approved recovery without regenerating images.

`editorial_config.py` is the reviewed source of truth for RSS feeds, category keyword lists, exclusion terms, feed headers, and summary word limits. Update these values in a PR and run the test suite; the seven-slide safety contract remains fixed. `news_collector.py` collects RSS feeds and extracts publisher text using Trafilatura. `news_quality.py` screens source fidelity, attribution, event duplicates, and corroboration signals. `image_generator.py` and `newspaper_design.py` draw editorial cards locally using Pillow. `upload_to_cloudinary.py` uploads media. `prepare_instagram_carousel.py` validates seven stories and constructs the caption/manifest. `publish_instagram.py` is the only live publishing entry point.

## Official logo and editorial masthead

The newspaper-style 1080×1350 cards use the approved transparent
`marketrevamp_logo_horizontal.png` in the repository root. The generator
extracts the **existing** circular MR emblem and MarketRevamp wordmark from
that same PNG and sizes both for a **compact, centered editorial masthead**
(78px maximum icon, 410px maximum wordmark); it does not redraw the brand
name or replace the approved artwork. The publication tagline is centered
underneath with more whitespace around the logo. The original
`marketrevamp_logo.png` is retained for backwards compatibility.

The offline `python test_image_layout.py` test creates
`marketrevamp_brand_preview.png` with synthetic example text (not actual
news), and the **Safe Validation** pull-request workflow attaches it as a
seven-day preview artifact. Inspect this preview before merging any future
masthead edits. Neither rendering nor CI sends Instagram API requests.

## One-time requested live quote-first post (Toronto, October 25, 2026)

A separately authorized, one-shot **Sunday** post is enabled by
`.github/marketrevamp-live-20261025.trigger`, through the existing
`MarketRevamp Automation` preparation and `Auto Publish MarketRevamp
Carousel` publishing workflows. Only the first push to `main` that changes
this trigger can start it; `schedule_guard.py` additionally requires the
exact pinned Toronto date, file contents and production branch.

On this single push, `MARKETREVAMP_QUOTE_FIRST=true` reorders the seven
source-screened *fresh* articles so an exact attributed quote appears on
slide 1. The six remaining slides retain the original approved editorial
layout. If no suitable direct quote is available, or one fails source
checks or 1080×1350 fitting, the run **fails closed** with no publishing.
The resulting news-results file, artwork, Cloudinary order and caption
must all share the same story order. The quote card uses the approved
artwork without its test-only warning.

The automatic publishing workflow accepts this push-source run only on
the pinned local date, with a successful same-day preparation provenance,
a seven-image manifest, a quote-first attestation, source-fingerprint
binding, and the existing duplicate/pending publishing-history barriers.
Ordinary push or manual dispatch cannot use the one-shot path. The
regular Mon–Fri 18:00 Toronto schedule is unchanged, with quote mode off.

This marker is intentionally unusable after 2026-10-25. It is not a
general Sunday schedule or authorization for recurring quote posts.
The synthetic `quote_first_preview/` artifact in Safe Validation must
not be uploaded or published as actual news.

## Experimental ONE-quote-card preview (not live)

This pull request introduces an **offline test only**. The production collector,
`image_generator.py` default renderer, automatic publishing workflows and
Instagram manifest remain unchanged. In particular, **scheduled auto-publishing
is enabled on main**, so this quote trial must remain in its experimental PR
branch until the new card has been reviewed and explicitly approved.

The deterministic `quote_cards.py` selector allows at most **one** short
(12–38 words) double-quoted verbatim excerpt per existing seven-slide carousel.
It accepts only close-by attribution to a two-part capitalized speaker name;
it never constructs, paraphrases, truncates, or edits a publisher quote.
Ambiguous attributions and weak/missing quotes produce normal cards instead.
The preview renderer checks quote text and speaker against the source again.

Safe Validation runs `test_quote_cards.py` and
`python run_quote_card_preview.py`. This generates seven synthetic 1080x1350
news slides in the isolated `quote_card_trial/` directory (six unchanged
newspaper cards, one visibly labelled experimental quote card), alongside
`standard_card_comparison.png`, `quote_card_experiment.png` and
`before_after.png`. The `marketrevamp-single-quote-test` GitHub Actions
artifact contains the complete non-publishable test. No live feeds, news
claims, Cloudinary or Instagram credentials are used to produce it.

**Rollback:** close the experimental PR without merging; `main` stays
exactly as it was. Even after approval, production integration would require
a separate explicit reviewed change with a default-off feature gate.

## Headline-answer summaries and mobile typography

The source-extractive news selector now favors concrete, source-supported
findings over commentary about how interesting an article or report is. When
a headline explicitly asks **who profits / benefits / wins**, the summary
must contain a source sentence naming a plausible beneficiary category
*and* the revenue, savings, fee or profit mechanism. Unresolved questions
such as "which companies capture the revenue?" do **not** count as answers.
If the publisher's available text has no suitable answer, the pipeline skips
that article and attempts another; it never fabricates beneficiaries.

The larger **KEY DETAILS** font prefers 34px (previously 29px) and adapts
down to 22px for longer extracts, keeping complete source sentences and a
safe margin above the footer. Its slightly wider text line preserves the
content card's margins. The approved Option C2 logo and other layout
components are unchanged. The safe test suite publishes an offline synthetic
sample called `marketrevamp_headline_answer_preview.png` as a CI artifact.
These tests do not fact-check article claims or post to Instagram.

## Editorial quality and tokenization imagery

The extractive summary selector rejects repeated three-word descriptive leads
when they do not supply new numeric detail. The independent summary screener
also holds such duplicated phrasing for review instead of silently paraphrasing
the original publisher. This is a heuristic, not independent fact-checking.

The 2D newspaper illustration selector uses a certificate-to-token diagram
for headlines about tokenization or real-world assets; actual Bitcoin news
retains its own ledger artwork. The bottom editorial disclaimer is raised so
it no longer crowds the paper's frame. The approved Option C2 masthead is
unchanged.

Safe Validation generates both `marketrevamp_brand_preview.png` and
`marketrevamp_tokenization_preview.png` using offline sample copy. These
previews are **not** live stories or publishable Instagram content.

## Configuration

GitHub production environment: `instagram-production`.

Secrets: `INSTAGRAM_ACCESS_TOKEN`, Cloudinary upload credentials/preset used by `upload_to_cloudinary.py`; optional `FAILURE_WEBHOOK_URL` (a JSON webhook endpoint for workflow failures).

Variables: `INSTAGRAM_USER_ID` and Cloudinary variables used in the upload step. The manual workflow takes `approval_fingerprint` as a per-run input, not a persistent variable. See workflow `env:` blocks for exact names.

### Automatic weekday publishing and manual fallback

**Opt-in automatic publishing is enabled for weekdays at 18:00 America/Toronto.** The preparation run generates seven slides; once it completes successfully, the separate automatic workflow validates the run's branch, source, local date, manifest and article count, derives the exact-content fingerprint, and publishes it once. The original publishing-history duplicate and pending checks remain active. Scheduled GH Actions can be delayed, so 18:00 is a target, not a guaranteed delivery time. If automatic publication is blocked or fails, inspect the run before taking any action; never blindly retry ambiguous posts.

The manual approved-artifact route remains available for exceptional recovery:

1. Open the successful **MarketRevamp Automation** GitHub Actions run and inspect its `marketrevamp-images`, `marketrevamp-news`, and `marketrevamp-instagram-carousel` artifacts. Verify each image, headline, source, caption, and alt text.
2. Copy the `REVIEW FINGERPRINT` (64 hexadecimal characters) printed by the preparation run. The SHA-256 digest binds the seven image URLs and their order, all article URLs, slide alt text, and caption. Editing any reviewed content invalidates approval.
3. Go to **Actions → Publish Approved MarketRevamp Carousel → Run workflow** on `main`. Enter the **source_run_id** of that *successful preparation run* and its exact **approval_fingerprint**.
4. The manual workflow retrieves the already-reviewed manifest, rechecks the source workflow and publishing history, runs offline safeguards, and publishes only when the supplied fingerprint matches. It does **not** create a fresh seven-slide selection.

The scheduled *preparation* workflow sets `INSTAGRAM_PUBLISH_ENABLED=true` but intentionally receives neither `INSTAGRAM_APPROVED_FINGERPRINT` nor live Instagram credentials, so it cannot publish. The **automatic publishing workflow** receives scoped production credentials only after verifying a successful, same-date scheduled preparation run and the exact seven-slide artifact; its computed fingerprint authorizes that package. This is explicit **automation authorization**, not human review. The manual workflow separately requires a user-provided approval fingerprint. The automatic and manual publishing workflows enable the publisher and receive `INSTAGRAM_ACCESS_TOKEN` only in their final publishing steps. Its environment is `instagram-production`. Required-reviewer rules can add a second authorization gate, but because scheduled preparation currently uses this same environment, those rules would also hold preparation runs; separate the environments before enabling review requirements if you want unattended preparation. A manual run is an explicit publication action: never enter a fingerprint until all images and text have been reviewed. <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments>

The manifest's `publish_enabled` flag and successful automated tests are additional safety checks, **not** human approval.

**Never commit credentials or paste them into logs.** Instagram access tokens may expire; arrange secure rotation/monitoring in the Meta developer account. The pipeline does not currently persist a refreshed token.

## Hashtags in Instagram captions

New seven-slide carousel manifests preserve the article headline/source lines,
follow call-to-action, and news/not-investment-advice disclaimer, then append
`#MarketRevamp #AI #Technology #Crypto #Bitcoin #StockMarket` at the very end
of the Instagram caption. `caption_format.py` validates the complete
caption against Instagram's 2,200-character limit, including hashtags.
If the caption would overflow, preparation fails closed rather than dropping
sources or the disclaimer.

New manifests set `first_comment` to an empty string. This avoids the
separate first-comment API call that had an unknown outcome after the
October 19 publication. The existing publisher can still process an older
explicitly prepared/approved manifest that contains a first comment; its
uncertain-comment checkpoint remains protected against duplicate publishing.
Previously published captions are **not** edited by this code change.

The exact caption is bound to the auto-publication fingerprint; tampering with
hashtags invalidates the saved package. Offline tests in
`test_caption_format.py` and `test_publishing_flow.py` check the new format
and confirm that publishing makes **zero** comments API requests for the new
manifests.

## Persistent publishing history

The `publishing-history` Git branch holds `instagram_publish_history.json`, restored into the workflow before collecting news. Each carousel is keyed by a fingerprint and marked `pending` before Instagram calls, then `published` on confirmed success. An unresolved `pending` is deliberately blocking: the API may have published successfully even if the response was lost. **Never delete pending records, force-push history, or rerun production to fix a timeout without reconciling Instagram first.** Publishing history is written to both the worktree and history checkout.

## Safe manual diagnostics

The legacy **Test Instagram Carousel (Offline)** and **Test Publishing History (Offline)** Actions perform only local unit/integration checks. They require neither Instagram credentials nor a publishing-history checkout, and cannot create Instagram media containers or add test records to the live history branch. The old network-connected carousel script and write-capable history test scripts have been retired.

## Local validation (no live post)

```bash
python -m pip install -r requirements.txt
python prepare_fonts.py
python -m unittest -v test_reliability.py test_news_quality.py test_seven_pipeline.py test_editorial_layout.py
python test_image_layout.py
python test_publishing_flow.py
```

`python news_collector.py` requires a valid history file and internet access. Generating cards from saved news data does not publish; publishing is enabled only by production environment gates and credentials. Prefer pull requests and the `Safe Validation` workflow; do **not** manually dispatch the production workflow as a test.

## Operational recovery

1. Check the failed GitHub Actions run and `publishing-history` branch.
2. If `pending` exists, reconcile the container/media ID and actual Instagram account feed before changing status.
3. If source extraction produces fewer than seven eligible stories, the run fails closed rather than posting incomplete content.
4. Check access-token validity, Cloudinary upload results, and API responses; rotate credentials via GitHub Secrets.
5. Re-run only non-publishing CI tests to verify code fixes.

## Cloudinary signed upload migration

The uploader supports signed uploads when both `CLOUDINARY_API_KEY` and `CLOUDINARY_API_SECRET` are configured as GitHub environment secrets. It signs the `timestamp` and `upload_preset` parameters with SHA-1 according to Cloudinary's upload API. **Never log or commit the secret.** To migrate, configure both secrets and a compatible Cloudinary preset, validate with a non-production test, then disable the old unsigned preset in Cloudinary. Until the credentials are configured, the existing unsigned preset remains in use for compatibility; signed upload migration is **not** complete.
