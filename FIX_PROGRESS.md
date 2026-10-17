# MarketRevamp hardening progress

Status is based on merged code and CI evidence, not commit-message wording. **DONE** means code and regression coverage are merged; **IN REVIEW** is not done; **BLOCKED** needs credentials/provider decisions.

| Backlog item | Status | Notes |
| --- | --- | --- |
| P0 seven-slide logging | DONE | PR #21 |
| P0 pre-publish failed retry | DONE | PR #27; only safe pre-publication failures retry, ambiguous final requests remain pending |
| P0 Instagram token refresh and persistence | BLOCKED | Requires confirming Meta token flow and secure write-capable secret storage; 401 warning is not refresh |
| P0 invalid-summary fallback | DONE | PR #21 |
| P0 pinned Python dependencies | DONE | PR #21; exact direct dependencies and requirements.lock |
| P0 duplicate urlsplit import | DONE | PR #21 |
| P1 failure alert | DONE (optional configuration) | FAILURE_WEBHOOK_URL secret required to send webhook |
| P1 feed/extraction retry | DONE | PR #21 |
| P1 history push conflict automatic reconciliation | NOT DONE | Fail-closed diagnostic implemented; safe merge/retry not implemented |
| P1 atomic history JSON | DONE | PR #21 |
| P1 GitHub Actions SHA pinning | DONE | PR #27; verified checkout/setup-python/upload-artifact tag refs |
| P1 Cloudinary unsigned preset replacement | PARTIAL | Signed upload code merged in PR #28; migration needs secrets, compatible preset and disabling old unsigned preset |
| P1 dependency vulnerability audit | DONE | PR #21 |
| P1 Graph API version review | PARTIAL | Explicit v24.0 constant, no automated sunset monitoring |
| P2 syndicated corroboration detection | PARTIAL | Explicit `original_source_url` / `syndicated_from_url` provenance prevents counting reprints as independent; automatic detection of unmarked syndication remains open |
| P2 publisher diversity | DONE | PR #25 |
| P2 carousel alt text | DONE | PR #26; requires provider compatibility verification |
| P2 hashtags in first comment | NOT DONE | |
| P2 summary coherence | PARTIAL | PR #31 merged; extractive summaries now constrain sentence distance and have offline regression coverage. Full semantic coherence remains unverified |
| P2 editorial config | NOT DONE | |
| P3 dead functions and imports | DONE (targeted) | PR #27 removes unused legacy extractor, cleaner, five-item selector and two image fitting functions; retains active wrap_lines |
| P3 README | DONE | PR #21 |
| P3 centralize seven-slide count | DONE | PR #26 shared constant; PR #27 removes remaining dead legacy helper |
| P3 Ruff and pre-commit | DONE (limited rules) | PR #26 |
| P3 PR CI | DONE | Safe Validation workflow |
| P3 type hints, main decomposition, structured logs | NOT DONE | |
| Module docstrings | DONE | PR #27 |
| Production full pre-publish regression suite | DONE | PR #27 |

## Production safety

Do not manually dispatch production to test. Unknown `pending` states may represent a successful Instagram publication; reconcile before retry. No automatic token or Cloudinary secret rotation without a secure persistence mechanism.
