"""MarketRevamp R51 9:16 editorial Reel design: key detail + readable karaoke captions.

Presentation only: no media uploads, Instagram calls, text or audio changes.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PAPER=(248,247,244)
PANEL=(243,240,236)
RED=(172,32,44)
INK=(16,25,38)
CAPTION_DARK=(20,27,38)
FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
KEY_BOX=(72,1070,1008,1330)
SUBTITLE_BOX=(65,1355,1015,1585)
CAPTION_FONT_SIZE=72
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
    if current:lines.append(current)
    return lines

def style_scene(input_image, detail_text, output_image):
    """Restyle only the original key-detail area and reserved caption band."""
    picture=Image.open(input_image).convert("RGB")
    if picture.size!=(1080,1920):
        raise ValueError("Expected 1080x1920 editorial Reel frame")
    draw=ImageDraw.Draw(picture)
    draw.rectangle((66,1060,1015,1337),fill=PAPER)
    draw.rounded_rectangle(KEY_BOX,radius=20,fill=PANEL)
    draw.rounded_rectangle((72,1070,83,1330),radius=5,fill=RED)
    title_font=ImageFont.truetype(FONT_BOLD,33)
    body_font=ImageFont.truetype(FONT_REG,41)
    draw.text((118,1091),"THE KEY DETAIL",fill=RED,font=title_font)
    lines=_text_lines(draw,detail_text,body_font,850)
    if len(lines)>3:
        body_font=ImageFont.truetype(FONT_REG,37)
        lines=_text_lines(draw,detail_text,body_font,850)
    if len(lines)>3:
        raise ValueError("Key detail would overflow its readable region")
    for index,line in enumerate(lines):
        draw.text((118,1165+54*index),line,fill=INK,font=body_font)
    # Caption overlay is 25 px below detail panel and 20 px above reporting source.
    draw.rounded_rectangle(SUBTITLE_BOX,radius=26,fill=CAPTION_DARK)
    destination=Path(output_image)
    destination.parent.mkdir(parents=True,exist_ok=True)
    picture.save(destination,optimize=True)
    return {"detail_lines":len(lines),"detail_font_size":body_font.size,"image_path":str(destination)}

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
            fields[2]="72"                 # Original 53 px -> 72 px (+35.8%)
            fields[3]="&H001D23E0"        # Active word red
            fields[4]="&H00FFFFFF"        # Inactive words white
            fields[5]="&H000A1020"        # Contrast outline
            fields[15]="1"                # Border style
            fields[16]="2"                # Outline px
            fields[17]="0"                # Shadow
            fields[18]="2"                # Bottom-centered alignment
            fields[19]="110"              # Left margin
            fields[20]="110"              # Right margin
            fields[21]="390"              # Bottom margin; captions stay in dark band
            fields[22]="1"                # Unicode/ASS encoding
            rows[idx]="Style: "+",".join(fields)
            count+=1
    if count!=1:
        raise ValueError("Expected one Words style")
    revised="\n".join(rows)+"\n"
    original_events=[x for x in original.splitlines() if x.startswith("Dialogue:")]
    new_events=[x for x in revised.splitlines() if x.startswith("Dialogue:")]
    if not original_events or original_events!=new_events:
        raise AssertionError("Speech word timing or dialogue was changed")
    target=Path(output_ass)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(revised,encoding="utf-8")
    return {"caption_font_size":CAPTION_FONT_SIZE,
            "karaoke_events_unchanged":len(original_events),
            "output":str(target)}
