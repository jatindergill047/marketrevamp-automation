"""MarketRevamp 9:16 Reel design with clean frames and readable karaoke captions.

Presentation only: no media uploads, Instagram calls, text or audio changes.
"""
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont

PAPER=(248,247,244)
PANEL=(243,240,236)
RED=(172,32,44)
INK=(16,25,38)
CAPTION_DARK=(20,27,38)
FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
KEY_BOX=(72,1070,1008,1330)
SUBTITLE_BOX=(65,1225,1015,1505)
CAPTION_FONT_SIZE=80
ORIGINAL_CAPTION_SIZE=53

def _text_lines(draw, text, face, width):
    lines,current=[],""
    for word in text.split():
        trial=(current+" "+word).strip()
        if current and draw.textbbox((0,0),trial,font=face)[2]>width:
            lines.append(current)
            current=word
        else:
            current=trial
    if current:
        lines.append(current)
    return lines

def style_scene(input_image, detail_text, output_image):
    """Remove the legacy key-detail visual and keep the caption band.

    The second argument remains for compatibility with existing call sites;
    it is deliberately never rendered into the video.
    """
    picture=Image.open(input_image).convert("RGB")
    if picture.size!=(1080,1920):
        raise ValueError("Expected 1080x1920 editorial Reel frame")
    draw=ImageDraw.Draw(picture)
    # Clear any previously rendered legacy key-detail heading, copy or panel.
    draw.rectangle((66,1060,1015,1337),fill=PAPER)
    draw.rounded_rectangle(SUBTITLE_BOX,radius=26,fill=CAPTION_DARK)
    destination=Path(output_image)
    destination.parent.mkdir(parents=True,exist_ok=True)
    picture.save(destination,optimize=True)
    return {"detail_lines":0,"image_path":str(destination)}

def enlarge_subtitles(source_ass, output_ass):
    """Keep the exact timecoded/karaoke dialogue and update presentation style only."""
    original=Path(source_ass).read_text(encoding="utf-8")
    rows=original.splitlines()
    count=0
    for idx,row in enumerate(rows):
        if row.startswith("Style: Words,"):
            fields=row[len("Style: "):].split(",")
            if len(fields)!=23:
                raise ValueError("Unexpected 23-field ASS style schema")
            fields[2]=str(CAPTION_FONT_SIZE)   # 72 px -> 80 px (+11.1%)
            fields[3]="&H001D23E0"        # Active word red
            fields[4]="&H00FFFFFF"        # Inactive words white
            fields[5]="&H000A1020"        # Contrast outline
            fields[15]="1"                # Border style
            fields[16]="2"                # Outline px
            fields[17]="0"                # Shadow
            fields[18]="5"                # Center inside below-artwork caption band
            fields[19]="110"              # Left margin
            fields[20]="110"              # Right margin
            fields[21]="0"                # Explicit \\pos below artwork is applied per event
            fields[22]="1"                # Unicode/ASS encoding
            rows[idx]="Style: "+",".join(fields)
            count+=1
    if count!=1:
        raise ValueError("Expected one Words style")
    # Keep 80 px karaoke text under artwork; split groups to avoid clipping.
    # Split visual caption groups while retaining every word's karaoke
    # centisecond duration and its absolute service-aligned start.
    def parse_time(value):
        hrs,mins,sec=value.split(":")
        return int(hrs)*3600+int(mins)*60+float(sec)

    def ass_time(value):
        ticks=round(max(0.0,value)*100)
        return f"{ticks//360000}:{(ticks//6000)%60:02d}:{(ticks//100)%60:02d}.{ticks%100:02d}"

    face=ImageFont.truetype(FONT_BOLD,CAPTION_FONT_SIZE)
    new_rows=[]
    original_word_schedule=[]
    revised_word_schedule=[]
    original_groups=0
    for row in rows:
        if not row.startswith("Dialogue:"):
            new_rows.append(row)
            continue
        original_groups+=1
        items=row.split(",",9)
        if len(items)!=10:
            raise ValueError("Unsupported ASS event schema")
        start_time=parse_time(items[1])
        end_time=parse_time(items[2])
        tokens=re.findall(r"(\{\\kf(\d+)\})([^{}]*?)(?=\{\\kf|$)",items[9])
        if not tokens:
            raise ValueError("Missing karaoke word timings")
        token_data=[]
        cursor=0
        for markup,centis,word in tokens:
            token_data.append((markup,int(centis),word.strip()))
            original_word_schedule.append((word.strip(),round(start_time+cursor/100,2)))
            cursor+=int(centis)
        chunks=[]
        current=[]
        for token in token_data:
            candidate=current+[token]
            words=" ".join(item[2] for item in candidate)
            if current and (len(candidate)>3 or face.getlength(words)>820):
                chunks.append(current)
                current=[token]
            else:
                current=candidate
        if current:
            chunks.append(current)
        cursor=0
        for chunk in chunks:
            split_start=start_time+cursor/100
            span=sum(t[1] for t in chunk)
            split_end=min(end_time,split_start+span/100)
            if split_end<=split_start:
                split_end=split_start+0.05
            parts=items.copy()
            parts[1]=ass_time(split_start)
            parts[2]=ass_time(split_end)
            parts[9]=r"{\\an5\\pos(540,1365)}"+" ".join(t[0]+t[2] for t in chunk)
            new_rows.append(",".join(parts))
            for markup,centis,word in chunk:
                revised_word_schedule.append((word,round(start_time+cursor/100,2)))
                cursor+=centis
    if original_word_schedule!=revised_word_schedule:
        raise AssertionError("Word-level karaoke alignment changed")
    revised="\n".join(new_rows)+"\n"
    new_groups=sum(line.startswith("Dialogue:") for line in new_rows)
    if original_groups<1 or new_groups<original_groups:
        raise AssertionError("Subtitle events lost")
    target=Path(output_ass)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(revised,encoding="utf-8")
    return {"caption_font_size":CAPTION_FONT_SIZE,
            "original_groups":original_groups,
            "new_groups":new_groups,
            "word_starts_preserved":len(original_word_schedule),
            "output":str(target)}
