"""R52: dated, source-linked Reel REVIEW package. No Cloudinary or Instagram calls."""
import asyncio
import difflib
import json
import math
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from reel_r51_design import style_scene, enlarge_subtitles, CAPTION_FONT_SIZE

PAPER=(248,247,244)
INK=(16,25,38)
RED=(172,32,44)
MUTED=(88,98,109)
LINE=(216,216,215)
SIZE=(1080,1920)
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
R52_DATE="2026-11-20"

def check_call(cmd, timeout=600):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout).stdout

def probe(path):
    return json.loads(check_call(["ffprobe","-v","error",
         "-show_format","-show_streams","-of","json",str(path)],timeout=30))

def stamp(t):
    t=max(0.0,float(t))
    centis=round(t*100)
    return f"{centis//360000}:{(centis//6000)%60:02d}:{(centis//100)%60:02d}.{centis%100:02d}"

def escape_ass(value):
    return str(value).replace("\\","\\\\").replace("{","\\{").replace("}","\\}").replace("\n"," ")

def words_normalized(s):
    return re.findall(r"[a-z0-9]+",str(s).casefold())

def validate_input(data, history):
    # This is a dated, review-only reconstruction; never use it for a new-day publication.
    review_day = datetime.fromisoformat(R52_DATE).date()
    today = datetime.now(ZoneInfo("America/Toronto")).date()
    if not (0 <= (today - review_day).days <= 1):
        raise RuntimeError("R52 dated review expired: a newer story set is required")
    if data.get("toronto_date") != R52_DATE or data.get("editorial_approved") is not False:
        raise RuntimeError("R52 sources must be date-bound and review-only")
    stories=data.get("stories")
    if not isinstance(stories,list) or len(stories)!=7:
        raise RuntimeError("Seven fresh source-linked stories are required")
    if not isinstance(history,dict):
        raise RuntimeError("Publishing history is required")
    seen=set()
    for i,story in enumerate(stories,1):
        for field in ("headline","deck","source_url","narration_text","source_name","published_date"):
            if not isinstance(story.get(field),str) or not story[field].strip():
                raise RuntimeError(f"Story {i} missing {field}")
        if story.get("fact_check_status") not in (
            "source_supported_pending_editorial_approval",
            "reported_plan_pending_editorial_approval"):
            raise RuntimeError("Source claim has not passed preliminary review")
        u=urlsplit(story["source_url"])
        if u.scheme!="https" or not u.hostname or not u.hostname.count("."):
            raise RuntimeError("Invalid source URL")
        canonical=(u.hostname.lower(),u.path.rstrip("/"))
        if canonical in seen:
            raise RuntimeError("Duplicate source within Reel")
        seen.add(canonical)
        if story["published_date"] not in ("2026-11-19","2026-11-20"):
            raise RuntimeError("A stale article was selected")
        if story.get("editorial_approved") is True:
            raise RuntimeError("R52 review build must not mark editorial approval")
    for record in history.values():
        if not isinstance(record,dict):
            raise RuntimeError("Malformed publishing history")
        if record.get("status")=="published":
            for url in record.get("article_urls",[]):
                p=urlsplit(url)
                if (p.hostname.lower(),p.path.rstrip("/")) in seen:
                    raise RuntimeError("Previously published article detected; stop R52")
    return stories

def font(size,bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)

def wrap(draw,text,face,width):
    current=""
    output=[]
    for word in text.split():
        test=(current+" "+word).strip()
        if current and draw.textbbox((0,0),test,font=face)[2]>width:
            output.append(current)
            current=word
        else:
            current=test
    if current:
        output.append(current)
    return output

def make_logo():
    logo_path=Path(__file__).resolve().parent/"marketrevamp_logo_horizontal.png"
    if not logo_path.is_file():
        raise RuntimeError("Official MarketRevamp logo absent; no fallback accepted")
    original=Image.open(logo_path).convert("RGBA")
    original.thumbnail((615,115),Image.Resampling.LANCZOS)
    # Replace only nearly-white matte pixels with paper color; colored artwork stays.
    canvas=Image.new("RGBA",original.size,PAPER+(255,))
    # For opaque logo files, near-white pixels become transparent.
    px=original.load()
    for y in range(original.height):
        for x in range(original.width):
            r,g,b,a=px[x,y]
            w=min(r,g,b)
            if w>=244:
                px[x,y]=(r,g,b,0)
            elif w>205:
                aa=int(a*(244-w)/39)
                px[x,y]=(r,g,b,aa)
    canvas.alpha_composite(original)
    return canvas.convert("RGB")

def draw_frames(stories,folder):
    logo=make_logo()
    frames=[]
    for i,story in enumerate(stories,1):
        picture=Image.new("RGB",SIZE,PAPER)
        draw=ImageDraw.Draw(picture)
        draw.rectangle((0,0,1080,16),fill=RED)
        picture.paste(logo,(70,74))
        draw.text((73,229),"MARKETREVAMP  /  THE DAILY BRIEF",font=font(24,True),fill=MUTED)
        draw.text((73,268),f"NOV 20, 2026     •     {i:02d} / 07",font=font(25),fill=MUTED)
        draw.line((72,336,1007,336),fill=RED,width=3)
        category=story.get("category","NEWS").upper()
        chip_width=math.ceil(draw.textbbox((0,0),category,font=font(25,True))[2]+50)
        draw.rounded_rectangle((72,384,72+chip_width,444),radius=18,fill=(229,224,219))
        draw.text((95,397),category,font=font(25,True),fill=RED)
        title=story["headline"]
        y=468
        for point_size in (62,58,54,50,46,42):
            face=font(point_size,True)
            lines=wrap(draw,title,face,920)
            line_height=round(point_size*1.24)
            if len(lines)<=5 and y+(len(lines)-1)*line_height+point_size<=834:
                break
        else:
            raise RuntimeError(f"Story {i} headline cannot fit above centered subtitles")
        for line in lines:
            draw.text((72,y),line,font=face,fill=INK)
            y+=line_height
        # Centered word captions occupy y=850–1070; source starts below 1605.
        draw.line((72,1605,1007,1605),fill=LINE,width=3)
        draw.text((72,1641),"REPORTING SOURCE",font=font(23,True),fill=MUTED)
        draw.text((72,1692),story["source_name"],font=font(34,True),fill=INK)
        draw.text((72,1780), "Market news • Not financial advice" if i == 7 else "AI-assisted narration  •  Source-linked reporting", font=font(23), fill=MUTED)
        draw.line((72,1852,1008,1852),fill=RED,width=5)
        dest=folder/f"R52_scene_{i:02d}.png"
        picture.save(dest,optimize=True)
        # Leave the former key-detail area blank and retain the caption band,
        # headline, reporting source and editorial disclaimer.
        style_scene(dest, story["deck"], dest)
        frames.append(dest)
    return frames

async def synthesize(script, destination, offsets):
    import edge_tts
    events=[]
    communicator=edge_tts.Communicate(script,"en-US-AndrewNeural",
                                      rate="-2%",pitch="-1Hz",boundary="WordBoundary")
    with destination.open("wb") as handle:
        async for block in communicator.stream():
            if block["type"]=="audio":
                handle.write(block["data"])
            elif block["type"]=="WordBoundary":
                events.append({"text":block["text"],
                    "start_seconds":block["offset"]/10000000,
                    "duration_seconds":block["duration"]/10000000})
    if len(events)<160 or not destination.is_file() or destination.stat().st_size<10000:
        raise RuntimeError(f"Neural speech failed: {len(events)} word cues")
    offsets.write_text(json.dumps(events,indent=2)+"\n",encoding="utf-8")
    return events

def map_chapters(stories,events):
    expected=[(i,t) for i,s in enumerate(stories) for t in words_normalized(s["narration_text"])]
    actual=[t for e in events for t in words_normalized(e["text"])]
    matcher=difflib.SequenceMatcher(a=[x[1] for x in expected],b=actual,autojunk=False)
    matching=[(b.a+i,b.b+i) for b in matcher.get_matching_blocks() for i in range(b.size)]
    quality=len(matching)/max(1,len(expected))
    if quality<0.90:
        raise RuntimeError(f"Speech alignment does not reliably match script: {quality:.1%}")
    matchmap=dict(matching)
    # Build token-to-boundary-event map in case the service splits hyphenated tokens.
    indices=[idx for idx,e in enumerate(events) for _ in words_normalized(e["text"])]
    positions=[next(j for j,(story,_) in enumerate(expected) if story==i) for i in range(7)]
    starts=[]
    for ix in positions:
        if ix in matchmap:
            target=matchmap[ix]
        else:
            neighbors=sorted(matching,key=lambda pair:abs(pair[0]-ix))
            if not neighbors:
                raise RuntimeError("No word matching data")
            target=neighbors[0][1]+(ix-neighbors[0][0])
        target=max(0,min(len(indices)-1,target))
        starts.append(indices[target])
    if starts[0]!=0 or any(x>=y for x,y in zip(starts,starts[1:])):
        raise RuntimeError("Invalid service chapter alignment")
    return starts,quality,len(expected),len(actual)

def captions(events,ass_path,scale):
    header="""[Script Info]
Title: MarketRevamp R52 - real voice-provider word timing
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Words,DejaVu Sans,53,&H001D23BF,&H00FFFFFF,&H990A1020,&H70050D20,1,0,0,0,100,100,0,0,1,2,0,2,60,60,440,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines=[]
    i=0
    while i<len(events):
        j=i+1
        while j<len(events):
            gap=events[j]["start_seconds"]-(events[j-1]["start_seconds"]+events[j-1]["duration_seconds"])
            if j-i>=5 or events[j]["start_seconds"]-events[i]["start_seconds"]>=2.7 or gap>.38:
                break
            j+=1
        batch=events[i:j]
        start=batch[0]["start_seconds"]*scale
        end=(batch[-1]["start_seconds"]+batch[-1]["duration_seconds"]+.08)*scale
        if j<len(events):
            end=min(end,events[j]["start_seconds"]*scale-.01)
        end=max(end,start+.12)
        words=[]
        for k,event in enumerate(batch):
            nextstart=batch[k+1]["start_seconds"] if k+1<len(batch) else end/scale
            cs=max(2,round((nextstart-event["start_seconds"])*scale*100))
            words.append(r"{\kf"+str(cs)+"}"+escape_ass(event["text"]))
        displayed=' '.join(words)
        displayed=re.sub(r'\{\\kf(\d+)\}I \{\\kf(\d+)\}P \{\\kf(\d+)\}O\b',
                         lambda m:r'{\kf'+str(sum(map(int,m.groups())))+'}IPO', displayed)
        displayed=re.sub(r'\{\\kf(\d+)\}A \{\\kf(\d+)\}I\b',
                         lambda m:r'{\kf'+str(sum(map(int,m.groups())))+'}AI', displayed)
        lines.append(f"Dialogue: 0,{stamp(start)},{stamp(end)},Words,,0,0,0,,{displayed}\n")
        i=j
    ass_path.write_text(header+"".join(lines),encoding="utf-8")
    # R51: enlarge from 53px to 72px without altering provider word timings.
    enlarged = enlarge_subtitles(ass_path, ass_path)
    assert enlarged["caption_font_size"] == CAPTION_FONT_SIZE
    return len(lines)

def run():
    root=Path(__file__).resolve().parent
    target=root/"r52_review"
    target.mkdir(exist_ok=True)
    data=json.loads((root/"r52_review_sources.json").read_text(encoding="utf-8"))
    history_path=root/"publishing-history"/"instagram_publish_history.json"
    if not history_path.is_file():
        raise RuntimeError("Authoritative publishing history checkout missing")
    history=json.loads(history_path.read_text(encoding="utf-8"))
    stories=validate_input(data,history)
    frames=draw_frames(stories,target)
    script=" ".join(s["narration_text"] for s in stories)
    source_audio=target/"R52_andrew_neural_source.mp3"
    boundary_file=target/"R52_word_boundaries.json"
    events=asyncio.run(synthesize(script,source_audio,boundary_file))
    starts,confidence,ntokens,actual_tokens=map_chapters(stories,events)
    length=float(probe(source_audio)["format"]["duration"])
    if not 45<=length<=110:
        raise RuntimeError(f"Unexpected neural audio duration: {length}")
    tempo=max(1.0,length/87.5)
    if tempo>1.17:
        raise RuntimeError("Narration too long to safely fit 90-second Reel")
    scale=1.0/tempo
    master=target/"R52_narration_master.wav"
    audio_filter=("aresample=48000,highpass=f=68,"
      "equalizer=f=2800:t=q:w=1.1:g=1.0,"
      "acompressor=threshold=0.34:ratio=1.4:attack=20:release=160,"
      f"atempo={tempo:.6f},loudnorm=I=-16:TP=-1.5:LRA=11,"
      "afade=t=in:d=0.12")
    check_call(["ffmpeg","-y","-loglevel","error","-i",str(source_audio),
                "-af",audio_filter,"-ar","48000","-ac","1",
                "-c:a","pcm_s16le",str(master)],timeout=180)
    duration=float(probe(master)["format"]["duration"])
    cuts=[0]+[events[ix]["start_seconds"]*scale for ix in starts[1:]]+[duration]
    if any(b-a<5.0 for a,b in zip(cuts,cuts[1:])):
        raise RuntimeError(f"Story scenes too short or misaligned: {cuts}")
    concat=target/"R52_scenes.ffconcat"
    items=["ffconcat version 1.0"]
    for i,img in enumerate(frames):
        items+= [f"file '{img.resolve()}'",f"duration {cuts[i+1]-cuts[i]:.6f}"]
    items+=[f"file '{frames[-1].resolve()}'"]
    concat.write_text("\n".join(items)+"\n",encoding="utf-8")
    ass=target/"R52_word_aligned_captions.ass"
    group_count=captions(events,ass,scale)
    output=target/"marketrevamp-r52-review.mp4"
    check_call(["ffmpeg","-y","-hide_banner","-loglevel","error",
                "-safe","0","-f","concat","-i",str(concat),
                "-i",str(master),"-vf",f"fps=12,ass={ass.resolve().as_posix()},format=yuv420p",
                "-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast",
                "-crf","21","-pix_fmt","yuv420p","-r","12","-c:a","aac",
                "-b:a","192k","-ar","48000","-movflags","+faststart",
                "-t",f"{duration:.3f}",str(output)],timeout=900)
    info=probe(output)
    video=float(info["format"]["duration"])
    streams=info["streams"]
    if not 45<=video<=90 or not any(
        s.get("codec_name")=="h264" and (s.get("width"),s.get("height"))==SIZE
        for s in streams) or not any(s.get("codec_name")=="aac" for s in streams):
        raise RuntimeError("R52 rendered media failed format/safety QA")
    if abs(video-duration)>.4:
        raise RuntimeError("Audio/video duration mismatch")
    image=Image.new("RGB",(4*270,2*480),PAPER)
    for idx,img in enumerate(frames):
        small=Image.open(img).resize((270,480),Image.Resampling.LANCZOS)
        image.paste(small,((idx%4)*270,(idx//4)*480))
    image.save(target/"R52_contact_sheet.jpg",quality=88)
    qa={
        "version":"R52",
        "design_revision":"R51",
        "key_detail_visible":False,
        "caption_font_size_px":CAPTION_FONT_SIZE,
        "subtitle_placement":"center",
        "toronto_date":R52_DATE,
        "status":"review_only",
        "editorial_approved":False,
        "published":False,
        "cloudinary_uploaded":False,
        "instagram_published":False,
        "voice":"en-US-AndrewNeural",
        "narration_words":len(script.split()),
        "tts_word_boundaries":len(events),
        "alignment_token_ratio":round(confidence,4),
        "script_tokens":ntokens,
        "timing_event_tokens":actual_tokens,
        "caption_groups":group_count,
        "caption_origin":"tts_word_boundaries",
        "duration_seconds":round(video,3),
        "dimensions":"1080x1920",
        "stream_types":[s.get("codec_name") for s in streams],
        "source_links":[s["source_url"] for s in stories],
        "source_duplicates_checked_against_history":True,
        "scene_starts":[round(x,2) for x in cuts[:-1]],
        "remaining":["Final independent source/caption/visual/voice human approval",
                     "Approved R52 generation workflow and exact release fingerprint",
                     "Controlled first live posting after approval"]
    }
    caption_lines=["MARKETREVAMP | NOV 20, 2026","","Seven AI, tech and crypto stories in under 90 seconds:",""]
    for idx, story in enumerate(stories,1):
        caption_lines += [f"{idx}. {story['headline']}",f"Source: {story['source_url']}",""]
    caption_lines += ["AI-generated voiceover. Headlines summarize the linked reporting.",
                     "Market news is informational only, not financial advice.","",
                     "#MarketRevamp #AI #TechNews #Blockchain #Bitcoin #CryptoNews"]
    caption="\n".join(caption_lines)
    if len(caption)>2200:
        raise RuntimeError("Instagram caption exceeds 2200 characters")
    (target/"R52_instagram_caption.txt").write_text(caption+"\n",encoding="utf-8")
    (target/"R52_QA.json").write_text(json.dumps(qa,indent=2)+"\n",encoding="utf-8")
    (target/"R52_script_and_sources.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print("R52_REVIEW_READY",json.dumps({
        "video":output.name,"duration":round(video,2),
        "word_boundaries":len(events),"source_count":len(stories),
        "published":False,"editorial_approved":False,"alignment_ratio":round(confidence,3)
    }),flush=True)

if __name__=="__main__":
    run()
