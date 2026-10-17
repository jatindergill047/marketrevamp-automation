# MarketRevamp Automation

Automated **seven-slide** editorial Instagram news carousel for @marketrevampdaily. The pipeline is source-extractive and does **not** use a paid image or language-model API. Summaries are source-grounded but **not independently fact-checked**.

## Architecture

Weekday GitHub Actions production workflow (`.github/workflows/marketrevamp.yml`) checks the Toronto publishing window, restores the persistent history checkout, installs Python dependencies/fonts, runs safeguards, collects recent RSS news, selects seven distinct stories, renders 1080×1350 newspaper-style cards, uploads images to Cloudinary, prepares the carousel manifest, and saves artifacts for human review. **Scheduled runs never send Instagram publishing requests.** The manual `.github/workflows/publish-approved.yml` workflow publishes a reviewed saved manifest without regenerating images.

`editorial_config.py` is the reviewed source of truth for RSS feeds, category keyword lists, exclusion terms, feed headers, and summary word limits. Update these values in a PR and run the test suite; the seven-slide safety contract remains fixed. `news_collector.py` collects RSS feeds and extracts publisher text using Trafilatura. `news_quality.py` screens source fidelity, attribution, event duplicates, and corroboration signals. `image_generator.py` and `newspaper_design.py` draw editorial cards locally using Pillow. `upload_to_cloudinary.py` uploads media. `prepare_instagram_carousel.py` validates seven stories and constructs the caption/manifest. `publish_instagram.py` is the only live publishing entry point.

## Configuration

GitHub production environment: `instagram-production`.

Secrets: `INSTAGRAM_ACCESS_TOKEN`, Cloudinary upload credentials/preset used by `upload_to_cloudinary.py`; optional `FAILURE_WEBHOOK_URL` (a JSON webhook endpoint for workflow failures).

Variables: `INSTAGRAM_USER_ID` and Cloudinary variables used in the upload step. The manual workflow takes `approval_fingerprint` as a per-run input, not a persistent variable. See workflow `env:` blocks for exact names.

### Explicit per-carousel approval

**A scheduled run prepares a seven-slide package but never publishes it.** After it completes:

1. Open the successful **MarketRevamp Automation** GitHub Actions run and inspect its `marketrevamp-images`, `marketrevamp-news`, and `marketrevamp-instagram-carousel` artifacts. Verify each image, headline, source, caption, and alt text.
2. Copy the `REVIEW FINGERPRINT` (64 hexadecimal characters) printed by the preparation run. The SHA-256 digest binds the seven image URLs and their order, all article URLs, slide alt text, and caption. Editing any reviewed content invalidates approval.
3. Go to **Actions → Publish Approved MarketRevamp Carousel → Run workflow** on `main`. Enter the **source_run_id** of that *successful preparation run* and its exact **approval_fingerprint**.
4. The manual workflow retrieves the already-reviewed manifest, rechecks the source workflow and publishing history, runs offline safeguards, and publishes only when the supplied fingerprint matches. It does **not** create a fresh seven-slide selection.

The scheduled workflow has `INSTAGRAM_PUBLISH_ENABLED=false` and is not given Instagram publishing credentials. The manual workflow alone enables the publisher and receives `INSTAGRAM_ACCESS_TOKEN`. Its environment is `instagram-production`. Required-reviewer rules can add a second authorization gate, but because scheduled preparation currently uses this same environment, those rules would also hold preparation runs; separate the environments before enabling review requirements if you want unattended preparation. A manual run is an explicit publication action: never enter a fingerprint until all images and text have been reviewed. <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments>

The manifest's `publish_enabled` flag and successful automated tests are additional safety checks, **not** human approval.

**Never commit credentials or paste them into logs.** Instagram access tokens may expire; arrange secure rotation/monitoring in the Meta developer account. The pipeline does not currently persist a refreshed token.

## Hashtags in the first comment

New carousel manifests keep the caption's sources and disclosure but move the six hashtag labels to a separate `first_comment` field. **Review the first comment together with the caption and slides**: it is included in the approval fingerprint. After successful `media_publish`, the publisher checkpoints `first_comment_status=pending`, then submits a top-level comment to the published Instagram media ID. When Meta confirms success it records the comment ID and status `posted`.

This requires the Instagram comment-management permission for the chosen Meta login flow (for Instagram Login, `instagram_business_manage_comments`). If the first-comment request times out or its result is otherwise unknown, the carousel stays marked `published` and the comment remains `pending`: **inspect Instagram and reconcile manually, never republish the carousel to retry a comment**. The code is covered by offline mocks, but live comment permissions and behavior must be verified with an explicitly approved real publication.

## Persistent publishing history

The `publishing-history` Git branch holds `instagram_publish_history.json`, restored into the workflow before collecting news. Each carousel is keyed by a fingerprint and marked `pending` before Instagram calls, then `published` on confirmed success. An unresolved `pending` is deliberately blocking: the API may have published successfully even if the response was lost. **Never delete pending records, force-push history, or rerun production to fix a timeout without reconciling Instagram first.** Publishing history is written to both the worktree and history checkout.

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
