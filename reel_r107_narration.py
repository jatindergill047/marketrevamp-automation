"""R107 source-grounded narration polish for the opt-in daily Reel only.

No network calls, editorial approval, Cloudinary access or Instagram writes.
"""
import re
from bisect import bisect_right


def additional_source_context(summary, headline, relevance):
    """Select one complete verbatim, on-topic publisher-summary sentence.

    Prefer a sentence containing material beyond the already spoken headline.
    If no suitable source extract is available, do not manufacture context.
    """
    head_terms = set(re.findall(r"[a-z0-9]+", headline.casefold()))
    candidates = []
    for sentence in re.split(r"(?<=[.!?])\s+", summary.strip()):
        sentence = sentence.strip()
        if not (8 <= len(sentence.split()) <= 23
                and sentence.endswith((".", "!", "?"))
                and relevance(headline, sentence)):
            continue
        unique = set(re.findall(r"[a-z0-9]+", sentence.casefold())) - head_terms
        if len(unique) >= 4:
            candidates.append((len(unique), sentence))
    return max(candidates, default=(0, ""))[1]


def readable_subtitle_events(events):
    """Replace phonetic speech hints in captions, retaining provider timings.

    Collapse multi-token pronunciation hints into one visible name, with its
    karaoke span covering every original syllable. Do not alter speech events
    used for chapter matching.
    """
    phrases = (
        (("s", "and", "p", "five", "hundred"), "S&P 500"),
        (("open", "a", "i"), "OpenAI"),
        (("b", "t", "c"), "BTC"),
    )
    display = []
    index = 0
    while index < len(events):
        item = dict(events[index])
        word = str(item["text"])
        if re.fullmatch(r"an-THROP-ik(?:['’]s)?", word, re.I):
            item["text"] = "Anthropic's" if word.endswith(("'s", "’s")) else "Anthropic"
        elif re.fullmatch(r"Naz-dak", word, re.I):
            item["text"] = "Nasdaq"
        else:
            for spoken, visible in phrases:
                selection = events[index:index+len(spoken)]
                if (len(selection) == len(spoken)
                        and tuple(str(x["text"]).casefold() for x in selection) == spoken):
                    last = selection[-1]
                    item["duration_seconds"] = max(
                        item["duration_seconds"],
                        last["start_seconds"] + last["duration_seconds"] - item["start_seconds"])
                    item["text"] = visible
                    index += len(spoken)-1
                    break
        display.append(item)
        index += 1
    return display


def insert_story_pauses(source, target, events, chapter_starts, *, probe, run,
                        pause_seconds=0.16):
    """Add eight genuine short silences before each following chapter.

    Word starts are shifted by exactly the amount of inserted silence.
    The original TTS word timing remains authoritative between pauses.
    """
    if len(chapter_starts) != 9 or not 0.12 <= pause_seconds <= 0.25:
        raise ValueError("Expected nine chapters and a short pause")
    length = float(probe(source)["format"]["duration"])
    boundaries = [events[ix]["start_seconds"] for ix in chapter_starts[1:]]
    if not (0.25 < boundaries[0] < length
            and all(a < b for a, b in zip(boundaries, boundaries[1:]))
            and boundaries[-1] < length - 0.2):
        raise ValueError("Unsafe neural audio scene boundaries")
    cuts = [0.0, *boundaries, length]
    filters = [
        f"[0:a]atrim=start={a:.6f}:end={b:.6f},asetpts=PTS-STARTPTS[a{i}]"
        for i, (a, b) in enumerate(zip(cuts, cuts[1:]))
    ]
    filters += [
        f"anullsrc=r=48000:cl=mono,atrim=duration={pause_seconds:.3f}[p{i}]"
        for i in range(8)
    ]
    ordered = "".join(f"[a{i}]" + (f"[p{i}]" if i < 8 else "")
                      for i in range(9))
    filters.append(f"{ordered}concat=n=17:v=0:a=1[aout]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
         "-filter_complex", ";".join(filters), "-map", "[aout]",
         "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(target)],
        timeout=180)
    return [
        {**event, "start_seconds": round(
            event["start_seconds"] + pause_seconds * bisect_right(
                boundaries, event["start_seconds"] + 1e-7), 6)}
        for event in events
    ]
