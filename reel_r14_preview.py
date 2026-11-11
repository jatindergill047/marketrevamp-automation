"""R14 seven-story editorial DEMO preview. Fictional headlines; no uploads."""
import json
import os
import subprocess
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont
from build_reel import build_continuous_reel
from reel_frames import compose
from reel_script import build_connected_all, connected_script
from tts import speak_with_boundaries, duration

STORIES = [
    ("AI research", "Researchers test a new way to evaluate AI systems",
     "Researchers introduce a hypothetical new evaluation method for AI systems.",
     "This is a fictional technology briefing, not real news. First, researchers are testing a new way to evaluate AI systems. The demo does not establish whether it works better than existing methods."),
    ("Semiconductors", "Experimental processor targets lower energy use",
     "A fictional chipmaker announces an experimental energy efficient processor.",
     "A fictional chipmaker is developing a processor intended to use less energy. No independent performance results are included in this example."),
    ("Blockchain", "Sample network proposes faster transaction settlement",
     "A sample blockchain project proposes faster transaction settlement.",
     "A hypothetical blockchain network proposes faster settlement. The example provides no measured transaction speeds."),
    ("Cybersecurity", "Security team releases defensive checklist",
     "An illustrative security team publishes a new defensive checklist.",
     "An illustrative security team has released a defensive checklist. The specific recommendations are not provided in this demo."),
    ("Cloud computing", "Cloud provider tests data center cooling approach",
     "A fictional cloud provider tests more efficient data center cooling.",
     "A fictional cloud provider is testing a different cooling approach. This example includes no verified energy savings."),
    ("Digital payments", "Payments company explores cross border settlement",
     "A sample payments company explores cross border settlement.",
     "A sample payments company is exploring cross-border settlement, but the demo gives no launch date."),
    ("Market outlook", "Analysts review technology sector risks",
     "Analysts in this fictional scenario review technology sector risks.",
     "Finally, fictional analysts are reviewing technology sector risks. Across these examples, the proposals remain unverified, and none should be treated as a real-world announcement."),
]

def main():
    if any(os.getenv(key, "false").lower() == "true" for key in
           ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED")):
        raise RuntimeError("R14 preview must never publish or upload")
    root = Path("r14_preview")
    root.mkdir(exist_ok=True)
    frames = []
    narrations = build_connected_all([{"headline": h, "summary": s, "category": category, "narration_text": script} for category, h, s, script in STORIES])
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 75)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 29)
    body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 43)
    for index, ((category, headline, summary, script), narration) in enumerate(zip(STORIES, narrations), 1):
        slide = Image.new("RGB", (1080, 1350), (21, 27, 40))
        draw = ImageDraw.Draw(slide)
        draw.rectangle((0, 0, 1080, 18), fill=(220, 46, 51))
        draw.text((65, 85), "MARKETREVAMP  /  EDITORIAL DEMO", font=small, fill=(240, 240, 240))
        draw.text((65, 320), category.upper(), font=font, fill=(255, 255, 255))
        for line_no, line in enumerate(textwrap.wrap(summary, width=38)):
            draw.text((65, 510 + line_no * 67), line, font=body_font, fill=(225, 229, 236))
        draw.text((65, 900), "FICTIONAL DEMO — NOT REAL NEWS", font=small, fill=(245, 130, 130))
        draw.text((65, 1080), f"TECH  /  STORY {index:02d} OF 07", font=small, fill=(210, 210, 210))
        path = root / f"slide_{index:02d}.png"
        slide.save(path)
        frames.append(compose(path, index, root / f"frame_{index:02d}.png"))

    voice, boundaries = speak_with_boundaries(connected_script([{"narration_text": script} for _, _, _, script in STORIES]), root / "continuous_voice.mp3", root / "word_boundaries.json")
    video = build_continuous_reel(frames, voice, narrations, root / "marketrevamp_r14_demo.mp4",
                                  root / "segments.json", fps=5, boundaries_path=boundaries)
    data = json.loads((root / "segments.json").read_text())
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "stream=codec_name,codec_type,width,height:format=duration",
                            "-of", "json", str(video)], capture_output=True, text=True,
                           check=True, timeout=30)
    streams = json.loads(probe.stdout)["streams"]
    assert any(s.get("codec_type") == "video" and s.get("codec_name") == "h264" and
               (s.get("width"), s.get("height")) == (1080, 1920) for s in streams)
    assert any(s.get("codec_type") == "audio" and s.get("codec_name") == "aac" for s in streams)
    assert len(data["segments"]) == 7
    assert data["audio_mode"] == "single_continuous_tts"
    assert data["chapter_timing"] == "tts_word_boundaries"
    assert abs(data["duration_seconds"] - duration(voice)) < 0.01
    assert all(data["segments"][i]["end_seconds"] <= data["segments"][i+1]["start_seconds"] + 0.002
               for i in range(6))
    contact = Image.new("RGB", (1080 * 4, 1920 * 2), (0, 0, 0))
    for i, frame in enumerate(frames):
        with Image.open(frame) as picture:
            contact.paste(picture, ((i % 4) * 1080, (i // 4) * 1920))
    contact.thumbnail((1600, 1500))
    contact.save(root / "contact_sheet.jpg", quality=85)
    (root / "QA_REPORT.md").write_text(
        "# R14 automated preview QA\n\n"
        "- Source: fictional editorial demo, not verified news.\n"
        "- AI narration: one continuous edge-tts file generated.\n"
        "- Video: 1080x1920 H.264 and AAC verified with ffprobe.\n"
        "- Captions: ASS burn-in by build_reel; visual legibility requires human inspection.\n"
        "- Timing: seven chapters aligned to service-provided word boundaries; human sync QA still required.\n"
        "- Motion: existing gentle zoompan; no crossfade transitions implemented.\n"
        "- Branding: placeholder text only; official logo asset NOT verified.\n"
        "- Audio pronunciation, subtitle sync and Instagram safe zones require human QA.\n"
        "- Cloudinary: NOT uploaded. Instagram: NOT published.\n"
        f"- Total planned duration: {data['duration_seconds']} seconds.\n",
        encoding="utf-8")
    print("R14 preview generated; duration", data["duration_seconds"], "seconds; no upload")

if __name__ == "__main__":
    main()
