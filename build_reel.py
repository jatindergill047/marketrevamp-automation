"""Build opt-in narrated 9:16 Reels from rendered slides and audio."""
import json
import math
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from reel_config import CAPTION_BAND_TOP, MIN_SLIDE_SECONDS, REEL_HEIGHT, REEL_WIDTH, SLIDE_PAD_SECONDS, ZOOM_MAX
from tts import ReelBuildError, duration


def _run(args):
    try:
        subprocess.run(args, check=True, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReelBuildError("ffmpeg Reel assembly failed") from exc


def _escape_ass(value):
    return str(value).replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", " ")


def _timestamp(seconds):
    hundredths = round(seconds * 100)
    hours, remainder = divmod(hundredths, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def write_captions(text, seconds, destination):
    """Write two-line maximum ASS captions in the reserved lower band."""
    words = str(text).split()
    if not words or seconds <= 0:
        raise ReelBuildError("Caption text and duration are required")
    chunks = []
    while words:
        chunk = words[:8]
        del words[:8]
        lines = textwrap.wrap(" ".join(chunk), width=29, break_long_words=False)
        if len(lines) > 2:
            lines = [" ".join(chunk[:4]), " ".join(chunk[4:])]
        chunks.append(r"\N".join(_escape_ass(line) for line in lines))
    per_chunk = seconds / len(chunks)
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,DejaVu Sans,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H99000000,"
        f"-1,0,0,0,100,100,0,0,1,2,0,8,65,65,{CAPTION_BAND_TOP + 38},1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = [
        f"Dialogue: 0,{_timestamp(i * per_chunk)},{_timestamp((i + 1) * per_chunk)},Default,,0,0,0,,{chunk}\n"
        for i, chunk in enumerate(chunks)
    ]
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(header + "".join(events), encoding="utf-8")
    return target


def build_reel(frames, audios, narrations, output_path, segments_path=None, fps=30):
    """Render H.264/AAC MP4 and timing JSON. All sequences must align."""
    if not (len(frames) == len(audios) == len(narrations)) or not frames:
        raise ReelBuildError("Frames, audio, and narration must have equal nonzero lengths")
    if shutil.which("ffmpeg") is None:
        raise ReelBuildError("ffmpeg is unavailable")
    if fps <= 0:
        raise ReelBuildError("fps must be positive")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix="marketrevamp_reel_") as folder:
        temporary = Path(folder)
        clips = []
        elapsed = 0.0
        for i, (frame, audio, narration) in enumerate(zip(frames, audios, narrations), 1):
            frame, audio = Path(frame), Path(audio)
            if not frame.is_file() or not audio.is_file():
                raise ReelBuildError(f"Missing media for segment {i}")
            voice_seconds = duration(audio)
            seconds = max(MIN_SLIDE_SECONDS, voice_seconds + SLIDE_PAD_SECONDS)
            if not math.isfinite(seconds):
                raise ReelBuildError("Invalid segment duration")
            subtitle = write_captions(narration, seconds, temporary / f"captions_{i}.ass")
            clip = temporary / f"segment_{i:02d}.mp4"
            frames_count = math.ceil(seconds * fps)
            # Scale slightly larger before cropping so zoompan never reveals edges.
            zoom = f"min(1+on/{max(frames_count-1,1)}*{ZOOM_MAX-1:.6f},{ZOOM_MAX:.6f})"
            filter_chain = (
                f"scale={REEL_WIDTH*2}:{REEL_HEIGHT*2},"
                f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={frames_count}:s={REEL_WIDTH}x{REEL_HEIGHT}:fps={fps},"
                f"ass={subtitle.as_posix()},format=yuv420p"
            )
            _run([
                "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(frame),
                "-i", str(audio), "-filter_complex", f"[0:v]{filter_chain}[v]",
                "-map", "[v]", "-map", "1:a:0", "-t", f"{seconds:.3f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                "-c:a", "aac", "-b:a", "160k", "-af", "apad",
                "-r", str(fps), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip),
            ])
            clips.append(clip)
            records.append({
                "index": i, "start_seconds": round(elapsed, 3),
                "duration_seconds": round(seconds, 3),
                "end_seconds": round(elapsed + seconds, 3),
                "narration": narration,
            })
            elapsed += seconds
        manifest = temporary / "concat.txt"
        manifest.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
        _run([
            "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
            "-i", str(manifest), "-c", "copy", "-movflags", "+faststart", str(output),
        ])
    if not output.is_file() or output.stat().st_size == 0:
        raise ReelBuildError("Reel output was not created")
    metadata = Path(segments_path) if segments_path else output.with_name("reel_segments.json")
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_text(json.dumps({"duration_seconds": round(elapsed, 3), "segments": records}, indent=2) + "\n", encoding="utf-8")
    return output
