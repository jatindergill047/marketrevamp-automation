"""Offline/nonpublishing seven-scene rendered Reel smoke test.

Synthetic news-copy only. Tests real neural voice, subtitles, audio mastering,
video assembly and the clean visual layout without relying on a live news feed.
"""
import asyncio
import json
from pathlib import Path

from PIL import Image

from reel_bookends import (HOOK_LINE, FOLLOW_LINE, build_bookends,
                           narration_segments, joined_narration,
                           validate_bookend_timing)
from reel_artwork import (write_artwork_concat, overlay_filter,
                         composite_artwork_preview, story_theme)
from reel_r50_review import (
    CAPTION_FONT_SIZE, PAPER, captions, check_call, draw_frames, map_chapters,
    make_logo,
    probe, synthesize,
)

ROOT = Path("reel_clean_review")
SCENES = [
    ("AI model deployment", "An example AI system is being evaluated.",
     "This is synthetic sample narration for the MarketRevamp review. The story is not a real news report. We are checking clean typography, audio levels, and the timed subtitles."),
    ("Smartphone hardware", "A sample processor shipment is described.",
     "This second synthetic headline tests the reading flow in a technology scene. We check that the headline remains visible and source attribution stays below the subtitles for accessibility."),
    ("Blockchain tokenization update", "A hypothetical network update is being reviewed.",
     "The third test story is fictional and does not describe a market event. Its purpose is to ensure that audio and the visual chapter changes follow the narration correctly."),
    ("Cybersecurity testing", "An imaginary AI benchmark is introduced.",
     "This sample story covers a hypothetical evaluation. The key detail section should never appear on screen, but the original headline and the subtitles must remain easy to read."),
    ("Smart glasses industry briefing", "A synthetic chip design study is described.",
     "The fifth story uses longer phrasing to check proper subtitle wrapping across scenes. The recorded voice timing should match the highlighted words without drifting beyond scene boundaries."),
    ("AI safety regulation proposal", "A sample cloud deployment is described.",
     "This fictional infrastructure story checks rendering stability during transitions. No real company is making any claim here. Source labels must still be retained below the caption area."),
    ("Stock market research note", "A fabricated analytics example is presented.",
     "The final fictional test story verifies the video ending, sound quality and disclaimer placement. This content is only a test and will not be uploaded or published anywhere."),
]


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    stories = [
        {"headline": title, "deck": deck,
         "category": ("AI", "Technology", "Crypto", "Technology",
                      "Technology", "AI", "Markets")[i-1],
         "source_name": "SYNTHETIC DEMO — NOT NEWS",
         "narration_text": voice,
         "source_url": f"https://example.org/synthetic-review/{i}"}
        for i, (title, deck, voice) in enumerate(SCENES, 1)
    ]
    story_frames = draw_frames(stories, ROOT)
    intro, outro = build_bookends(make_logo(), ROOT, "R50")
    frames = [intro] + story_frames + [outro]
    for frame in story_frames:
        with Image.open(frame) as image:
            assert image.size == (1080, 1920)
            assert image.getpixel((75, 1100)) == PAPER
            assert image.getpixel((75, 1250)) != PAPER
    segments = narration_segments(stories)
    text = joined_narration(segments)
    source_audio = ROOT / "neural_voice_source.mp3"
    events_file = ROOT / "neural_word_boundaries.json"
    events = asyncio.run(synthesize(text, source_audio, events_file))
    starts, match, _, _ = map_chapters(segments, events)
    if match < .90:
        raise RuntimeError("Voice alignment too low")
    mastered = ROOT / "master_audio.wav"
    check_call([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source_audio),
        "-af", ("aresample=48000,highpass=f=68,"
                "equalizer=f=2800:t=q:w=1.1:g=1.0,"
                "acompressor=threshold=0.34:ratio=1.4:attack=20:release=160,"
                "loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.12"),
        "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(mastered)
    ], timeout=180)
    duration = float(probe(mastered)["format"]["duration"])
    cuts = [0] + [events[ix]["start_seconds"] for ix in starts[1:]] + [duration]
    bookends_qa = validate_bookend_timing(cuts)
    concat = ROOT / "chapters.ffconcat"
    lines = ["ffconcat version 1.0"]
    for i, frame in enumerate(frames):
        lines += [f"file '{frame.resolve()}'", f"duration {cuts[i+1]-cuts[i]:.6f}"]
    lines += [f"file '{frames[-1].resolve()}'"]
    concat.write_text("\n".join(lines)+"\n", encoding="utf-8")
    ass = ROOT / "subtitles.ass"
    groups = captions(events, ass, 1.0)
    art_concat = write_artwork_concat(ROOT, "R50", cuts,
                                     include_bookends=True)
    output = ROOT / "marketrevamp-clean-reel-review-only.mp4"
    check_call([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-safe", "0", "-f", "concat", "-i", str(concat),
        "-safe", "0", "-f", "concat", "-i", str(art_concat),
        "-i", str(mastered),
        "-filter_complex", overlay_filter(ass),
        "-map", "[v]", "-map", "2:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p", "-r", "12",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-t", f"{duration:.3f}", str(output),
    ], timeout=900)
    info = probe(output)
    streams = info["streams"]
    rendered_length = float(info["format"]["duration"])
    assert any(s.get("codec_name") == "h264" and
               (s.get("width"), s.get("height")) == (1080, 1920) for s in streams)
    assert any(s.get("codec_name") == "aac" for s in streams)
    assert abs(rendered_length-duration) < .4
    assert groups > 10 and len(events) >= 160
    assert rendered_length <= 90
    contact = Image.new("RGB", (1080, 960), PAPER)
    for index, frame in enumerate(story_frames):
        with Image.open(frame) as image:
            art = ROOT / f"R50_artwork_{index+1:02d}.png"
            preview = composite_artwork_preview(frame, art)
            thumb = preview.resize((270, 480))
            contact.paste(thumb, ((index % 4)*270, (index // 4)*480))
    contact.save(ROOT/"contact_sheet.png")
    qa = {
        "status": "review_only", "synthetic_content": True,
        "editorial_approved": False, "published": False,
        "cloudinary_uploaded": False, "instagram_published": False,
        "key_detail_visible": False, "seven_scenes": len(story_frames),
        "spoken_hook": HOOK_LINE, "spoken_follow_cta": FOLLOW_LINE,
        **bookends_qa,
        "caption_font_size_px": CAPTION_FONT_SIZE,
        "subtitle_placement": "below_artwork",
        "artwork_themes": [story_theme(story) for story in stories],
        "artwork_animation": "subtle_vertical_float_8px",
        "tts_word_boundaries": len(events),
        "alignment_token_ratio": round(match, 4),
        "caption_groups": groups,
        "duration_seconds": round(rendered_length, 3),
        "video_codec": "h264", "audio_codec": "aac",
        "dimensions": "1080x1920",
    }
    (ROOT/"QA.json").write_text(json.dumps(qa, indent=2)+"\n", encoding="utf-8")
    print("REVIEW_ONLY_COMPLETE", json.dumps(qa), flush=True)


if __name__ == "__main__":
    main()
