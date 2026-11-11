"""Build opt-in narrated 9:16 Reels from rendered slides and audio."""
import json
import math
import re
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


def write_captions(text, seconds, destination, spoken_seconds=None, word_timings=None):
    """Write two-line maximum ASS captions in the reserved lower band."""
    words = str(text).split()
    if not words or seconds <= 0:
        raise ReelBuildError("Caption text and duration are required")
    # Prefer phrase boundaries; avoid changing spoken text or fabricating timestamps.
    chunks = []
    remaining = words[:]
    while remaining:
        limit = min(8, len(remaining))
        boundary = next((j for j in range(3, limit + 1)
                         if re.search(r"[.!?;:,]$", remaining[j - 1])), limit)
        chunk = remaining[:boundary]
        del remaining[:boundary]
        lines = textwrap.wrap(" ".join(chunk), width=29, break_long_words=False)
        if len(lines) > 2:
            lines = [" ".join(chunk[:4]), " ".join(chunk[4:])]
        chunks.append((r"\N".join(_escape_ass(line) for line in lines), len(chunk)))
    # Keep subtitles inside the actual spoken interval, leaving the
    # inter-story quiet beat visually uncluttered.
    caption_seconds = seconds if spoken_seconds is None else min(seconds, spoken_seconds)
    if caption_seconds <= 0:
        raise ReelBuildError("Spoken caption duration must be positive")
    # Approximate phrase timing by word count, not equal time per subtitle.
    # Exact word alignment requires timestamps from the TTS service.
    total_words = sum(count for _, count in chunks)
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,DejaVu Sans,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H99000000,"
        f"-1,0,0,0,100,100,0,0,1,2,0,8,65,65,{CAPTION_BAND_TOP + 38},1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    offset = 0
    if word_timings is not None and len(word_timings) != total_words:
        raise ReelBuildError("Caption word timings do not match narration")
    for chunk, count in chunks:
        if word_timings is not None:
            start = max(0.0, float(word_timings[offset]["start_seconds"]))
            last = word_timings[offset + count - 1]
            end = min(seconds, float(last["start_seconds"]) + float(last["duration_seconds"]))
            if end <= start:
                raise ReelBuildError("Invalid caption word timestamps")
        else:
            start = caption_seconds * offset / total_words
            end = caption_seconds * (offset + count) / total_words
        offset += count
        events.append(
            f"Dialogue: 0,{_timestamp(start)},{_timestamp(end)},Default,,0,0,0,,{chunk}\n"
        )
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
            subtitle = write_captions(narration, seconds, temporary / f"captions_{i}.ass", spoken_seconds=voice_seconds)
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


def build_continuous_reel(frames, audio, narrations, output_path, segments_path=None, fps=5, boundaries_path=None):
    """R23 preview: one uninterrupted audio track, seven synchronized visual chapters.

    Chapter boundaries use word-weighted estimates, NOT actual TTS word timestamps.
    """
    if not frames or len(frames) != len(narrations) or not all(str(s).strip() for s in narrations):
        raise ReelBuildError("Continuous Reel requires matching frames and scripts")
    audio = Path(audio)
    if not audio.is_file() or not all(Path(frame).is_file() for frame in frames):
        raise ReelBuildError("Missing continuous Reel media")
    if shutil.which("ffmpeg") is None or fps <= 0:
        raise ReelBuildError("ffmpeg unavailable or invalid frame rate")
    voice_seconds = duration(audio)
    word_counts = [len(script.split()) for script in narrations]
    total_words = sum(word_counts)
    timing_mode = "estimated_word_weighted"
    aligned = None
    per_story_timings = None
    if boundaries_path is not None:
        events = json.loads(Path(boundaries_path).read_text(encoding="utf-8"))
        def tokens(s):
            return re.findall(r"[a-z0-9]+", str(s).casefold())
        spoken_tokens = [tokens(e.get("text", "")) for e in events]
        story_tokens = [tokens(s) for s in narrations]
        flattened = [token for group in spoken_tokens for token in group]
        expected = [token for group in story_tokens for token in group]
        if flattened != expected:
            raise ReelBuildError("Word boundaries do not match reviewed narration")
        starts = []
        offset = 0
        for story in story_tokens:
            starts.append(offset)
            offset += len(story)
        token_event_indices = [i for i, group in enumerate(spoken_tokens) for _ in group]
        aligned = [0.0] + [float(events[token_event_indices[n]]["start_seconds"])
                           for n in starts[1:]] + [voice_seconds]
        if any(a >= z for a, z in zip(aligned, aligned[1:])):
            raise ReelBuildError("Word boundaries must increase")
        per_story_timings = []
        for i, script in enumerate(narrations):
            # ASS captions group whitespace-delimited words, whereas the
            # TTS alignment tokenizes punctuation and hyphenated words.
            # Map every displayed word to its first and last speech token.
            first = starts[i]
            chapter_start = aligned[i]
            cursor = first
            word_times = []
            for displayed_word in script.split():
                parts = tokens(displayed_word)
                if not parts:
                    raise ReelBuildError("Caption word has no speech tokens")
                start_event = events[token_event_indices[cursor]]
                end_event = events[token_event_indices[cursor + len(parts) - 1]]
                start_time = max(0.0, float(start_event["start_seconds"]) - chapter_start)
                end_time = float(end_event["start_seconds"]) + float(end_event["duration_seconds"]) - chapter_start
                word_times.append({"start_seconds": start_time,
                                   "duration_seconds": max(0.0, end_time - start_time)})
                cursor += len(parts)
            if cursor != first + len(story_tokens[i]):
                raise ReelBuildError("Caption tokens do not match narration")
            per_story_timings.append(word_times)
        timing_mode = "tts_word_boundaries"
    # Use exact frame counts to avoid gaps between chapters.
    total_frames = max(len(frames), math.ceil(voice_seconds * fps))
    boundaries = [0]
    for i in range(1, len(frames)):
        proposed = (round(aligned[i] * fps) if aligned is not None else
                    round(total_frames * sum(word_counts[:i]) / total_words))
        boundaries.append(max(boundaries[-1] + 1, min(proposed, total_frames - (len(frames) - i))))
    boundaries.append(total_frames)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix="marketrevamp_r23_") as folder:
        root = Path(folder)
        clips = []
        for i, (frame, narration) in enumerate(zip(frames, narrations)):
            count = boundaries[i + 1] - boundaries[i]
            seconds = count / fps
            subtitle = write_captions(narration, seconds, root / f"caption_{i}.ass",
                                      word_timings=per_story_timings[i] if per_story_timings else None)
            clip = root / f"visual_{i}.mp4"
            zoom = f"min(1+on/{max(count-1,1)}*{ZOOM_MAX-1:.6f},{ZOOM_MAX:.6f})"
            filters = (
                f"scale={REEL_WIDTH*2}:{REEL_HEIGHT*2},"
                f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={count}:s={REEL_WIDTH}x{REEL_HEIGHT}:fps={fps},"
                f"ass={subtitle.as_posix()},format=yuv420p"
            )
            _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(frame),
                  "-vf", filters, "-frames:v", str(count), "-an", "-c:v", "libx264",
                  "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", str(clip)])
            clips.append(clip)
            records.append({"index": i + 1, "start_seconds": round(boundaries[i] / fps, 3),
                            "duration_seconds": round(seconds, 3),
                            "end_seconds": round(boundaries[i + 1] / fps, 3),
                            "narration": narration})
        manifest = root / "concat.txt"
        manifest.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips))
        visuals = root / "visuals.mp4"
        _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
              "-i", str(manifest), "-c", "copy", str(visuals)])
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(visuals), "-i", str(audio),
              "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
              "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(output)])
    if not output.is_file() or output.stat().st_size == 0:
        raise ReelBuildError("Continuous Reel output was not created")
    metadata = Path(segments_path) if segments_path else output.with_name("reel_segments.json")
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_text(json.dumps({"duration_seconds": round(voice_seconds, 3),
        "audio_mode": "single_continuous_tts", "chapter_timing": timing_mode,
        "segments": records}, indent=2) + "\n", encoding="utf-8")
    return output
