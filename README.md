# MarketRevamp Automation

Automated **seven-slide** editorial Instagram news carousel for @marketrevampdaily. The pipeline is source-extractive and does **not** use a paid image or language-model API. Summaries are source-grounded but **not independently fact-checked**.

## Architecture

Weekday GitHub Actions production workflow (`.github/workflows/marketrevamp.yml`) checks the Toronto publishing window, restores the persistent history checkout, installs Python dependencies/fonts, runs safeguards, collects recent RSS news, selects seven distinct stories, renders 1080×1350 newspaper-style cards, uploads images to Cloudinary, prepares the carousel manifest, and calls the Instagram Graph API.

`news_collector.py` collects RSS feeds and extracts publisher text using Trafilatura. `news_quality.py` screens source fidelity, attribution, event duplicates, and corroboration signals. `image_generator.py` and `newspaper_design.py` draw editorial cards locally using Pillow. `upload_to_cloudinary.py` uploads media. `prepare_instagram_carousel.py` validates seven stories and constructs the caption/manifest. `publish_instagram.py` is the only live publishing entry point.

## Configuration

GitHub production environment: `instagram-production`.

Secrets: `INSTAGRAM_ACCESS_TOKEN`, Cloudinary upload credentials/preset used by `upload_to_cloudinary.py`; optional `FAILURE_WEBHOOK_URL` (a JSON webhook endpoint for workflow failures).

Variables: `INSTAGRAM_USER_ID` and Cloudinary variables used in the upload step. See workflow `env:` blocks for exact names.

**Never commit credentials or paste them into logs.** Instagram access tokens may expire; arrange secure rotation/monitoring in the Meta developer account. The pipeline does not currently persist a refreshed token.

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
