"""R83: bounded, owner-authorized Reel release decisions (no network calls).

A source-screened headline is not independently fact checked. Every public
caption discloses this. A separate controlled first-live fingerprint and Meta
readback must exist before unattended automation can be switched on.
"""
import hashlib
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from publish_instagram import normalize_article_url
from reel_r46_launch_gate import (ReleaseBlocked, validate_and_fingerprint,
                                   authorize_publication)
from reel_r49_first_live import _check_article_reuse
from reel_editorial_quality import same_reel_event, summary_supports_headline

TORONTO = ZoneInfo("America/Toronto")
SOURCES = {
    "techcrunch.com": "TechCrunch",
    "arstechnica.com": "Ars Technica",
    "coindesk.com": "CoinDesk",
    "cnbc.com": "CNBC",
    "bbc.com": "BBC News",
    "bbc.co.uk": "BBC News",
    "bbci.co.uk": "BBC News",
}
APPROVED_HOOK = "Here's what's making headlines today."
APPROVED_CTA = "Follow MarketRevamp for quick, clear updates. Stay informed."
AUTO_POLICY = "owner_authorized_source_attribution_v1"
BLOCKED_CATEGORIES = {"Politics", "Opinion", "Unverified"}


def require(ok, message):
    if not ok:
        raise ReleaseBlocked(message)


def source_name(url):
    u = urlsplit(url)
    hostname = (u.hostname or "").lower().removeprefix("www.")
    require(u.scheme == "https" and not u.username and not u.password,
            "Publisher source URL must be HTTPS")
    require(hostname in SOURCES, "Publisher not in reviewed source list")
    return SOURCES[hostname]


def validate_draft(qa, review, sources, video, history, *, now=None):
    """Validate today's R72 draft and all R67 provenance; no authorization."""
    date = (now or datetime.now(TORONTO)).astimezone(TORONTO)
    today = date.date().isoformat()
    require(isinstance(history, dict), "Authoritative publishing history missing")
    require(all(isinstance(v, dict) for v in history.values()),
            "Malformed history record")
    require(isinstance(qa, dict) and isinstance(review, dict)
            and isinstance(sources, dict), "Missing source review artifacts")
    require(all(part.get("toronto_date") == today for part in (qa, review, sources)),
            "Stale or future-dated news: do not publish")
    require(qa.get("version") == review.get("version") == "R72"
            and sources.get("version") == "R67", "Review chain mismatch")
    require(qa.get("status") == review.get("status") == sources.get("status") == "review_only",
            "Review artifacts have unexpected status")
    for doc in (qa, review, sources):
        require(doc.get("published") is False and doc.get("editorial_approved") is False,
                "Review-only source must not claim publication or prior approval")
    require(qa.get("cloudinary_uploaded") is False
            and qa.get("instagram_published") is False
            and sources.get("cloudinary_uploaded") is False
            and sources.get("instagram_published") is False
            and sources.get("render_authorized") is False,
            "Review-only publication flags inconsistent")
    require(qa.get("synthetic_content") is False
            and qa.get("real_source_headlines") is True
            and qa.get("not_independently_fact_checked") is True,
            "No real source-screened draft")
    require(qa.get("seven_scenes") == 7 and qa.get("presentation_segments") == 9
            and qa.get("spoken_hook") == APPROVED_HOOK
            and qa.get("spoken_follow_cta") == APPROVED_CTA,
            "Approved R71 sequence missing")
    require(qa.get("dimensions") == "1080x1920"
            and qa.get("video_codec") == "h264" and qa.get("audio_codec") == "aac"
            and qa.get("caption_font_size_px") == 80
            and qa.get("subtitle_placement") == "below_artwork"
            and float(qa.get("alignment_token_ratio", 0)) >= 0.99
            and int(qa.get("tts_word_boundaries", 0)) >= 90
            and 45 <= float(qa.get("duration_seconds", 0)) <= 90,
            "Visual, audio or speech alignment quality gate failed")
    require(qa.get("history_checked") is True, "Review lacked history check")
    candidates = review.get("stories")
    publishers = sources.get("stories")
    require(isinstance(candidates, list) and isinstance(publishers, list)
            and len(candidates) == len(publishers) == 7
            and sources.get("story_count") == 7,
            "Exactly seven source-screened stories required")
    urls = []
    eligible = []
    for i, (r, origin) in enumerate(zip(candidates, publishers), 1):
        require(isinstance(r, dict) and isinstance(origin, dict),
                f"Story {i} has malformed source")
        require(r.get("editorial_approved") is False
                and origin.get("editorial_approved") is False
                and origin.get("fact_check_status") ==
                    "source_matched_not_independently_fact_checked"
                and r.get("fact_check_status") ==
                    "source_supported_pending_editorial_approval",
                f"Story {i} lacks screened publisher support")
        url = normalize_article_url(r.get("source_url"))
        require(url == normalize_article_url(origin.get("source_url")),
                f"Story {i} URL differs from R67 screening")
        require(r.get("headline") == origin.get("headline")
                and r.get("category") == origin.get("category"),
                f"Story {i} headline/category changed after screening")
        require(isinstance(origin.get("summary"), str)
                and 30 <= len(origin["summary"].split()) <= 90
                and r.get("deck") == origin["summary"],
                f"Story {i} visible context differs from screened publisher summary")
        require(summary_supports_headline(r.get("headline", ""),
                                          origin["summary"]),
                f"Story {i} publisher paragraph is unrelated to its headline")
        require(not any(same_reel_event(r.get("headline", ""),
                                        previous.get("headline", ""))
                        for previous in eligible),
                f"Story {i} duplicates an existing named news event")
        require(r.get("category") not in BLOCKED_CATEGORIES,
                f"Story {i} is not in permitted topic coverage")
        publisher = source_name(url)
        require(r.get("source_name") == publisher,
                f"Story {i} source name is not bound to its URL")
        narration = r.get("narration_text", "")
        require(isinstance(narration, str) and
                narration.startswith(f"According to {publisher}, "),
                f"Story {i} lacks publisher attribution")
        require(9 <= len(narration.split()) <= 40,
                f"Story {i} has unsafe narration length")
        published = datetime.fromisoformat(origin.get("published_at", ""))
        require(published.tzinfo is not None and
                0 <= (date - published).total_seconds() <= 48*3600,
                f"Story {i} article is stale or future-dated")
        require(url not in urls, "Duplicate story URL")
        urls.append(url)
        # True means policy-approved, not independently corroborated.
        eligible.append({**r, "source_url": url,
                         "editorial_approved": True,
                         "fact_check_status": "source_supported",
                         "approval_mode": AUTO_POLICY})
    require(len({s["category"] for s in eligible}) >= 3,
            "Insufficient topic coverage")
    require([normalize_article_url(u) for u in qa.get("source_links", [])] == urls,
            "Rendered video source list mismatches source review")
    _check_article_reuse(eligible, history)
    require(not any(r.get("media_kind") == "reel" and
                    r.get("toronto_date") == today and
                    (r.get("status") in {"published", "pending", "unknown"}
                     or r.get("publish_attempted_at"))
                    for r in history.values()),
            "Today's Reel is already pending, unknown or published")
    require(Path(video).is_file() and Path(video).stat().st_size > 1024,
            "Rendered video is unavailable")
    require(sum(len(x["narration_text"].split()) for x in eligible) <= 180,
            "Total narration exceeds reviewed speech budget")
    sources_text = "\n".join(f"{i}. {u}" for i, u in enumerate(urls, 1))
    caption = ("MarketRevamp — today's seven AI, technology, crypto and market stories.\n"
               "Headlines and context are attributed to their reporting publishers; "
               "these reports are not independently fact-checked by MarketRevamp.\n"
               "Sources:\n" + sources_text +
               "\n\n#MarketRevamp #AINews #TechNews #CryptoNews #MarketNews #NewsReel")
    require(len(caption) <= 2200, "Source attribution cannot fit in Instagram caption")
    metadata = {
        "toronto_date": today,
        "editorial_approved": True,
        "visual_qa_approved": True,
        "audio_qa_approved": True,
        "official_logo_verified": True,
        "word_timing_origin": "tts_word_boundaries",
        "voice": "en-US-AndrewNeural",
        "reviewed_by": "Automated source-attribution policy, not human review",
        "editorial_review_mode": AUTO_POLICY,
        "caption": caption,
    }
    return metadata, eligible


def release_decision(qa, review, sources, video, history,
                     *, activation, first_live=False,
                     approved_video_sha256="", now=None):
    """Return release fingerprint only with exact first-live or verified rollout gate."""
    metadata, stories = validate_draft(
        qa, review, sources, video, history, now=now
    )
    require(isinstance(activation, dict) and
            activation.get("owner_authorized") is True and
            activation.get("policy") == AUTO_POLICY,
            "No owner authorization for automated source policy")
    digest = hashlib.sha256(Path(video).read_bytes()).hexdigest()
    if first_live:
        require(activation.get("controlled_first_live") is True
                and approved_video_sha256 == digest
                and activation.get("first_video_sha256") == digest,
                "First public Reel requires exact reviewed video hash")
    else:
        require(activation.get("daily_enabled") is True,
                "Recurring public Reel publishing remains disabled")
        verified = activation.get("verified_first_media_id")
        require(isinstance(verified, str) and verified.isdigit(),
                "No verified first-live Instagram media ID")
        require(any(str(record.get("instagram_media_id")) == verified
                    and record.get("media_kind") == "reel"
                    and record.get("status") == "published"
                    and record.get("instagram_readback_verified") is True
                    and record.get("template_version") == "R72"
                    for record in history.values()),
                "First R72 public Reel readback not yet recorded")
    release = validate_and_fingerprint(
        metadata, stories, video, now=now
    )
    authorize_publication(release, release["release_fingerprint"], history, now=now)
    return {"metadata": metadata, "stories": stories,
            "fingerprint": release["release_fingerprint"],
            "video_sha256": digest, "owner_authorized": True,
            "policy": AUTO_POLICY, "first_live": first_live}
