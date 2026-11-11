"""R14 seven-story editorial DEMO preview. Fictional headlines; no uploads."""
import json
import os
import subprocess
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont
from build_reel import build_reel
from reel_frames import compose
from reel_script import build_connected_all
from tts import speak, duration

STORIES = [
    ("AI research", "Researchers test a new way to evaluate AI systems",
     "Researchers introduce a hypothetical new evaluation method for AI systems.",
     "In this fictional scenario, researchers introduce a new method for evaluating AI systems."),
    ("Semiconductors", "Experimental processor targets lower energy use",
     "A fictional chipmaker announces an experimental energy efficient processor.",
     "A fictional chipmaker has announced an experimental processor designed to use less energy."),
    ("Blockchain", "Sample network proposes faster transaction settlement",
     "A sample blockchain project proposes faster transaction settlement.",
     "A hypothetical blockchain project is proposing faster transaction settlement."),
    ("Cybersecurity", "Security team releases defensive checklist",
     "An illustrative security team publishes a new defensive checklist.",
     "An illustrative security team has released a new defensive checklist."),
    ("Cloud computing", "Cloud provider tests data center cooling approach",
     "A fictional cloud provider tests more efficient data center cooling.",
     "A fictional cloud provider is testing a more efficient approach to data center cooling."),
    ("Digital payments", "Payments company explores cross border settlement",
     "A sample payments company explores cross border settlement.",
     "A sample payments company is exploring cross-border settlement."),
    ("Market outlook", "Analysts review technology sector risks",
     "Analysts in this fictional scenario review technology sector risks.",
     "In this fictional market update, analysts are reviewing risks across the technology sector."),
]

def main():
    if any(os.getenv(key, "false").lower() == "true" for key in
           ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED")):
        raise RuntimeError("R14 preview must never publish or upload")
    root = Path("r14_preview")
    root.mkdir(exist_ok=True)
    frames, voices = [], []
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
        voices.append(speak(narration, root / f"voice_{index:02d}.mp3"))
    video = build_reel(frames, voices, narrations, root / "marketrevamp_r14_demo.mp4",
                       root / "segments.json", fps=5)
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
    for segment, voice in zip(data["segments"], voices):
        assert segment["duration_seconds"] >= duration(voice)
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
        "- AI narration: seven real edge-tts files generated.\n"
        "- Video: 1080x1920 H.264 and AAC verified with ffprobe.\n"
        "- Captions: ASS burn-in by build_reel; visual legibility requires human inspection.\n"
        "- Timing: seven nonoverlapping segments, each at least voice duration.\n"
        "- Motion: existing gentle zoompan; no crossfade transitions implemented.\n"
        "- Branding: placeholder text only; official logo asset NOT verified.\n"
        "- Audio pronunciation, subtitle sync and Instagram safe zones require human QA.\n"
        "- Cloudinary: NOT uploaded. Instagram: NOT published.\n"
        f"- Total planned duration: {data['duration_seconds']} seconds.\n",
        encoding="utf-8")
    print("R14 preview generated; duration", data["duration_seconds"], "seconds; no upload")

if __name__ == "__main__":
    main()
