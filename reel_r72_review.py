"""R72: source-linked, fresh daily Reel REVIEW, never a publication workflow.

The R67 collector is the source of truth for screened article candidates.
This module revalidates dates, history and source attribution before deriving
short *provisional* scripts. It does not assert independent fact checking.
"""
import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageDraw, ImageFont
from edge_tts.exceptions import NoAudioReceived

from r67_weekday_news import (TORONTO, REQUIRED_STORIES, MAX_AGE_HOURS,
                              _source, load_published_history)
from reel_r50_review import (PAPER, captions, check_call, draw_frames,
                             make_logo, map_chapters, probe, synthesize)
from reel_artwork import (overlay_filter, write_artwork_concat,
                         composite_artwork_preview, story_theme)
from reel_bookends import (HOOK_LINE, FOLLOW_LINE, build_bookends,
                           joined_narration, narration_segments,
                           validate_bookend_timing)
from reel_r51_design import CAPTION_FONT_SIZE
from reel_script import clean_text
from reel_editorial_quality import (same_reel_event, summary_supports_headline,
                                    sentence_supports_headline)

MAX_TOTAL_STORY_WORDS = 180
MIN_TOTAL_STORY_WORDS = 95
TOPICS = frozenset(("AI", "Technology", "Crypto", "Markets"))
PUBLISHER_NAMES = {
    "techcrunch.com": "TechCrunch",
    "arstechnica.com": "Ars Technica",
    "coindesk.com": "CoinDesk",
    "cnbc.com": "CNBC",
    "bbc.co.uk": "BBC News",
    "bbci.co.uk": "BBC News",
    "bbc.com": "BBC News",
}


def publisher_from_url(url):
    host = (urlsplit(_source(url)).hostname or "").lower().removeprefix("www.")
    if host not in PUBLISHER_NAMES:
        raise ValueError("Source publisher is not on MarketRevamp's reviewed feed list")
    return PUBLISHER_NAMES[host]


def _complete_context(summary, headline):
    """Optional short verbatim extract; never reword or truncate a claim."""
    sentences = re.split(r"(?<=[.!?])\s+", summary.strip())
    return next((s.strip() for s in sentences
                 if 8 <= len(s.split()) <= 22 and s.rstrip().endswith((".", "!", "?"))
                 and sentence_supports_headline(headline, s)),
                "")


def prepare_stories(package, published_urls, *, now):
    """Derive short source-attributed narration from screened, fresh sources."""
    local = now.astimezone(TORONTO)
    if package.get("status") != "review_only" or package.get("version") != "R67":
        raise ValueError("Input must be an R67 review-only package")
    if package.get("toronto_date") != local.date().isoformat():
        raise ValueError("News package must match today's Toronto date")
    if package.get("story_count") != REQUIRED_STORIES:
        raise ValueError("Exactly seven screened source stories required")
    if any(package.get(k) is not False for k in (
        "editorial_approved", "published", "cloudinary_uploaded",
        "instagram_published", "render_authorized"
    )):
        raise ValueError("R67 input has unexpected publication authorization")
    if not isinstance(published_urls, set):
        raise ValueError("Authoritative publishing history is required")
    entries = package.get("stories")
    if not isinstance(entries, list) or len(entries) != REQUIRED_STORIES:
        raise ValueError("R72 requires seven source-linked story records")
    stories = []
    seen = set()
    extra = []
    for index, item in enumerate(entries, 1):
        if not isinstance(item, dict) or item.get("editorial_approved") is not False:
            raise ValueError("Every source story must remain editorially unapproved")
        if item.get("fact_check_status") != "source_matched_not_independently_fact_checked":
            raise ValueError("Publisher extraction provenance is not verified")
        title = item.get("headline")
        category = item.get("category")
        summary = item.get("summary")
        url = _source(item.get("source_url"))
        if not isinstance(title, str) or not title.strip() or len(title) > 180:
            raise ValueError("Bad source headline")
        if category not in TOPICS or not isinstance(summary, str):
            raise ValueError("Category/summary not supported")
        if not 30 <= len(summary.split()) <= 90:
            raise ValueError("Summary outside source-screened word range")
        if not summary_supports_headline(title, summary):
            raise ValueError("Unrelated source paragraph cannot appear in Reel")
        stamp = datetime.fromisoformat(item.get("published_at", ""))
        if stamp.tzinfo is None or not 0 <= (now-stamp).total_seconds()/3600 <= MAX_AGE_HOURS:
            raise ValueError("Stale or future source article")
        if url in seen or url in published_urls:
            raise ValueError("Previously published or repeated URL in Reel")
        if any(same_reel_event(title, previous["headline"]) for previous in stories):
            raise ValueError("Near-duplicate news event in Reel")
        seen.add(url)
        publisher = publisher_from_url(url)
        title_spoken = clean_text(title).rstrip(".!?")
        if not title_spoken or len(title_spoken.split()) > 28:
            raise ValueError("Unusable or excessively long news headline")
        spoken = f"According to {publisher}, {title_spoken}."
        stories.append({
            "headline": title.strip(),
            "category": category,
            "deck": summary,
            "narration_text": spoken,
            "source_url": url,
            "source_name": publisher,
            "published_date": stamp.date().isoformat(),
            "fact_check_status": "source_supported_pending_editorial_approval",
            "editorial_approved": False,
            "story_index": index,
        })
        context = _complete_context(summary, title)
        extra.append(context if context.casefold() not in title.casefold() else "")

    if len({s["category"] for s in stories}) < 3:
        raise ValueError("Insufficient topic coverage")
    count = sum(len(s["narration_text"].split()) for s in stories)
    if count > MAX_TOTAL_STORY_WORDS:
        raise ValueError("Narration budget exceeded by headlines")
    # Add complete extractive sentence context while within a conservative
    # budget; never slice a quote, paraphrase claims, or invent a consequence.
    for index in sorted(range(REQUIRED_STORIES), key=lambda k: len(extra[k].split())):
        context = extra[index]
        if count >= 135:
            break
        if not context:
            continue
        n = len(context.split())
        if count + n > MAX_TOTAL_STORY_WORDS or (
            len(stories[index]["narration_text"].split()) + n > 38
        ):
            continue
        stories[index]["narration_text"] += " " + clean_text(context)
        count += n
    if count < MIN_TOTAL_STORY_WORDS:
        raise ValueError("Too little supported narration for a useful news Reel")
    return stories


async def synthesize_with_retry(script, audio_path, boundaries_path,
                                *, attempts=3, sleep=asyncio.sleep):
    """Retry transient neural voice failures without accepting partial audio."""
    if not 1 <= attempts <= 3:
        raise ValueError("Neural TTS retry count must remain bounded")
    for number in range(attempts):
        try:
            return await synthesize(script, audio_path, boundaries_path,
                                    min_events=80)
        except (NoAudioReceived, OSError, TimeoutError, ConnectionError):
            for file in (audio_path, boundaries_path):
                candidate=Path(file)
                if candidate.exists():
                    candidate.unlink()
            if number==attempts-1:
                raise
            await sleep(4*(number+1))


def render_review(stories, *, output_dir, toronto_date, synthetic=False):
    """Render with R71 visual/audio pipeline. No Cloudinary or Instagram code."""
    if len(stories) != REQUIRED_STORIES:
        raise ValueError("Seven stories are required")
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    local_date = datetime.fromisoformat(toronto_date)
    label = local_date.strftime("%b %d, %Y").upper()
    story_frames = draw_frames(stories, target, display_date=label, prefix="R72")
    intro, outro = build_bookends(make_logo(), target, "R72")
    frames = [intro] + story_frames + [outro]
    if synthetic:
        # Never let fabricated integration-fixture news look like real reporting.
        for frame in frames:
            with Image.open(frame) as img:
                marked = img.convert("RGB")
            ImageDraw.Draw(marked).text(
                (72, 1530), "SYNTHETIC DEMO - NOT NEWS",
                font=ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26),
                fill=(172, 32, 44)
            )
            marked.save(frame, optimize=True)
    segments = narration_segments(stories)
    script = joined_narration(segments)
    source_audio = target / "r72_voice_source.mp3"
    speech_boundaries = target / "r72_word_boundaries.json"
    events = asyncio.run(synthesize_with_retry(
        script, source_audio, speech_boundaries))
    starts, match, expected_count, actual_count = map_chapters(segments, events)
    if match < 0.90:
        raise RuntimeError("Voice timing drifted from the approved script")
    raw_length = float(probe(source_audio)["format"]["duration"])
    if raw_length <= 0 or raw_length > 110:
        raise RuntimeError("Narration is too long for a safe 90-second master")
    tempo = max(1.0, raw_length / 87.0)
    if tempo > 1.15:
        raise RuntimeError("Narration would need excessive speech acceleration")
    scale = 1.0 / tempo
    mastered = target / "r72_master_audio.wav"
    audio_filter = (
        "aresample=48000,highpass=f=68,"
        "equalizer=f=2800:t=q:w=1.1:g=1.0,"
        "acompressor=threshold=0.34:ratio=1.4:attack=20:release=160,"
        f"atempo={tempo:.6f},loudnorm=I=-16:TP=-1.5:LRA=11,"
        "afade=t=in:d=0.12"
    )
    check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", str(source_audio),
                "-af", audio_filter, "-ar", "48000", "-ac", "1",
                "-c:a", "pcm_s16le", str(mastered)], timeout=180)
    duration = float(probe(mastered)["format"]["duration"])
    cuts = [0] + [events[i]["start_seconds"] * scale for i in starts[1:]] + [duration]
    bookend_qa = validate_bookend_timing(cuts)
    scene_file = target / "r72_scenes.ffconcat"
    lines = ["ffconcat version 1.0"]
    for index, frame in enumerate(frames):
        lines.extend((f"file '{frame.resolve()}'",
                      f"duration {cuts[index+1]-cuts[index]:.6f}"))
    lines.append(f"file '{frames[-1].resolve()}'")
    scene_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    captions_path = target / "r72_subtitles.ass"
    caption_groups = captions(events, captions_path, scale)
    artwork_concat = write_artwork_concat(target, "R72", cuts,
                                          include_bookends=True)
    output = target / "marketrevamp-r72-real-news-review-only.mp4"
    check_call([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-safe", "0", "-f", "concat", "-i", str(scene_file),
        "-safe", "0", "-f", "concat", "-i", str(artwork_concat),
        "-i", str(mastered), "-filter_complex", overlay_filter(captions_path),
        "-map", "[v]", "-map", "2:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p", "-r", "12", "-c:a", "aac",
        "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        "-t", f"{duration:.3f}", str(output)
    ], timeout=900)
    info = probe(output)
    length = float(info["format"]["duration"])
    streams = info["streams"]
    if not 45 <= length <= 90 or abs(length-duration) > .4:
        raise RuntimeError("Rendered news Reel failed 45-90 second timing gate")
    if not any(s.get("codec_name") == "h264" and
               (s.get("width"),s.get("height")) == (1080, 1920)
               for s in streams):
        raise RuntimeError("Expected 1080x1920 H264 video")
    if not any(s.get("codec_name") == "aac" for s in streams):
        raise RuntimeError("Expected AAC narration")
    sheet = Image.new("RGB", (1080, 960), PAPER)
    for i, frame in enumerate(story_frames):
        preview = composite_artwork_preview(
            frame, target/f"R72_artwork_{i+1:02d}.png"
        ).resize((270, 480), Image.Resampling.LANCZOS)
        sheet.paste(preview, ((i % 4)*270, (i // 4)*480))
    sheet.save(target/"r72_contact_sheet.png")
    qa = {
        "version": "R72", "status": "review_only",
        "synthetic_content": bool(synthetic),
        "real_source_headlines": not synthetic,
        "not_independently_fact_checked": True,
        "editorial_approved": False,
        "published": False, "cloudinary_uploaded": False,
        "instagram_published": False,
        "toronto_date": toronto_date,
        "seven_scenes": 7, "presentation_segments": 9,
        "spoken_hook": HOOK_LINE, "spoken_follow_cta": FOLLOW_LINE,
        **bookend_qa,
        "caption_font_size_px": CAPTION_FONT_SIZE,
        "subtitle_placement": "below_artwork",
        "artwork_themes": [story_theme(s) for s in stories],
        "alignment_token_ratio": round(match, 4),
        "script_tokens": expected_count,
        "timing_event_tokens": actual_count,
        "tts_word_boundaries": len(events),
        "caption_groups": caption_groups,
        "duration_seconds": round(length, 3),
        "dimensions": "1080x1920",
        "video_codec": "h264", "audio_codec": "aac",
        "source_links": [s["source_url"] for s in stories],
        "history_checked": True,
    }
    (target / "r72_qa.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return qa


def main(argv=None):
    parser = argparse.ArgumentParser(description="R72 real news review only")
    parser.add_argument("--sources", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--output-dir", default="r72_review")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)
    now = datetime.now(TORONTO)
    package = json.loads(Path(args.sources).read_text(encoding="utf-8"))
    history = load_published_history(args.history)
    stories = prepare_stories(package, history, now=now)
    target = Path(args.output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "editorial_pending_stories.json").write_text(
        json.dumps({
            "version": "R72", "status": "review_only",
            "editorial_approved": False, "published": False,
            "toronto_date": now.date().isoformat(),
            "fact_check_disclaimer": "Real publisher headlines; independent editorial verification pending",
            "stories": stories
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    if not args.prepare_only:
        qa = render_review(stories, output_dir=target,
                           toronto_date=now.date().isoformat())
        print("R72_REAL_NEWS_REVIEW_ONLY", qa["duration_seconds"],
              qa["alignment_token_ratio"])
    else:
        print("R72_EDITORIAL_CANDIDATES_ONLY")


if __name__ == "__main__":
    main()
