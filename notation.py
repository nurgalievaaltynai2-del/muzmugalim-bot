"""Renders a simple melody as sheet music on a "music notebook" page (PNG)."""
import io
import os
import re

from PIL import Image, ImageDraw, ImageFont

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_TEXT = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
_TEXT_BOLD = os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")
_MUSIC = os.path.join(_FONT_DIR, "NotoMusic-Regular.ttf")

_LETTER = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
ALLOWED_DURATIONS = (4.0, 3.0, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25)  # in quarter notes
_BOTTOM_STEP = 30   # E4: bottom line of the treble staff
_TOP_STEP = 38      # F5: top line

_PAPER = (253, 249, 236)
_INK = (35, 35, 45)
_MARGIN = (225, 140, 140)

_REST_GLYPH = {4.0: "\U0001D13B", 2.0: "\U0001D13C", 1.0: "\U0001D13D", 0.5: "\U0001D13E", 0.25: "\U0001D13F"}


def pitch_to_step(pitch: str) -> tuple:
    """'F#4' -> (31, '#'): diatonic step counted from C0, plus accidental."""
    m = re.fullmatch(r"([A-Ga-g])([#b]?)(\d)", (pitch or "").strip())
    if not m:
        raise ValueError(f"Нота биіктігі дұрыс емес: {pitch!r}")
    letter, acc, octave = m.groups()
    return int(octave) * 7 + _LETTER[letter.upper()], acc


def snap_duration(d) -> float:
    try:
        d = float(d)
    except (TypeError, ValueError):
        d = 1.0
    return min(ALLOWED_DURATIONS, key=lambda a: abs(a - d))


def rest_fill(total: float) -> list:
    """Decompose a duration into rest notes using the allowed values."""
    out = []
    left = round(total, 4)
    while left > 0.01:
        d = next((a for a in ALLOWED_DURATIONS if a <= left + 1e-6), None)
        if d is None:
            break
        out.append({"p": "R", "d": d, "l": ""})
        left = round(left - d, 4)
    return out


def _font(path, size):
    return ImageFont.truetype(path, size)


def _is_rest(note) -> bool:
    return str(note.get("p", "")).strip().upper() in ("R", "REST")


def _note_width(note, lyric_font, draw, s) -> int:
    lyric = note.get("l") or ""
    lw = draw.textlength(lyric, font=lyric_font) + 18 if lyric else 0
    return int(max(s * 3.4, s * 2.6 + s * 1.9 * min(note["d"], 2.0), lw))


def render_notation(melody: dict) -> bytes:
    s = 17                      # staff space
    W = 1700
    left, right = 130, 70
    header_h = 190
    system_h = 300
    footer_h = 70

    lyric_font = _font(_TEXT, 21)
    measures = melody["measures"]
    scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    clef_w = int(s * 5.6)
    time_w = int(s * 3.2)
    mwidths = []
    for bar in measures:
        mwidths.append(sum(_note_width(n, lyric_font, scratch, s) for n in bar) + int(s * 1.6))

    # Greedy line breaking
    systems, cur, cur_w = [], [], 0
    for i, w in enumerate(mwidths):
        avail = W - left - right - clef_w - (time_w if not systems else 0)
        if cur and cur_w + w > avail:
            systems.append(cur)
            cur, cur_w = [], 0
        cur.append(i)
        cur_w += w
    if cur:
        systems.append(cur)

    H = header_h + system_h * len(systems) + footer_h
    img = Image.new("RGB", (W, H), _PAPER)
    d = ImageDraw.Draw(img)

    # Notebook look: margin line and punch holes
    d.line([(78, 0), (78, H)], fill=_MARGIN, width=3)
    for y in (H * 0.2, H * 0.5, H * 0.8):
        d.ellipse([22, y - 14, 50, y + 14], fill=(228, 224, 210), outline=(205, 200, 185))

    # Header
    title_font = _font(_TEXT_BOLD, 46)
    sub_font = _font(_TEXT, 25)
    d.text((left, 40), str(melody.get("title") or "Ноталар"), font=title_font, fill=_INK)
    num, den = melody["time"]
    d.text(
        (left, 108),
        f"Нота дәптері  •  Өлшем: {num}/{den}  •  Темп: {melody.get('tempo', 90)} BPM",
        font=sub_font, fill=(95, 95, 110),
    )

    clef_font = _font(_MUSIC, int(s * 7.2))
    rest_font = _font(_MUSIC, int(s * 4.2))
    time_font = _font(_TEXT_BOLD, int(s * 2.6))
    acc_font = _font(_MUSIC, int(s * 2.6))

    def step_y(step, bottom_y):
        return bottom_y - (step - _BOTTOM_STEP) * s / 2

    for si, system in enumerate(systems):
        top_y = header_h + si * system_h + int(s * 4.5)
        bottom_y = top_y + 4 * s
        x_start = left
        for k in range(5):
            y = top_y + k * s
            d.line([(x_start, y), (W - right, y)], fill=_INK, width=2)
        d.line([(x_start, top_y), (x_start, bottom_y)], fill=_INK, width=3)

        # Clef (G line = second line from the bottom)
        d.text((x_start + 6, bottom_y - s), "\U0001D11E", font=clef_font, fill=_INK, anchor="ls")
        x = x_start + clef_w
        if si == 0:
            d.text((x + s * 0.9, top_y + 1 * s), str(num), font=time_font, fill=_INK, anchor="mm")
            d.text((x + s * 0.9, top_y + 3 * s), str(den), font=time_font, fill=_INK, anchor="mm")
            x += time_w

        avail = W - right - x
        natural = sum(mwidths[i] for i in system)
        stretch = min(avail / natural, 1.45) if natural else 1.0
        if si == len(systems) - 1 and natural < avail * 0.6:
            stretch = 1.0

        for mi in system:
            bar = measures[mi]
            bar_w = mwidths[mi] * stretch
            widths = [_note_width(n, lyric_font, scratch, s) for n in bar]
            scale = (bar_w - s * 1.6 * stretch) / max(sum(widths), 1)
            nx = x + s * 0.8 * stretch
            for note, w in zip(bar, widths):
                slot = w * scale
                cx = nx + slot / 2
                _draw_note(d, note, cx, top_y, bottom_y, s, step_y, rest_font, acc_font)
                lyric = note.get("l") or ""
                if lyric and not _is_rest(note):
                    d.text((cx, bottom_y + s * 4.9), lyric, font=lyric_font, fill=(60, 60, 75), anchor="mm")
                nx += slot
            x += bar_w
            last = mi == len(measures) - 1
            if last:
                d.line([(x - 8, top_y), (x - 8, bottom_y)], fill=_INK, width=3)
                d.line([(x, top_y), (x, bottom_y)], fill=_INK, width=7)
            else:
                d.line([(x, top_y), (x, bottom_y)], fill=_INK, width=3)

    foot = _font(_TEXT, 20)
    d.text((W - right, H - 38), "MuzMugalim Bot  |  @muzmugalim", font=foot, fill=(150, 150, 160), anchor="rs")

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _draw_note(d, note, cx, top_y, bottom_y, s, step_y, rest_font, acc_font):
    dur = note["d"]
    if _is_rest(note):
        glyph = _REST_GLYPH.get(dur) or _REST_GLYPH.get(min(_REST_GLYPH, key=lambda a: abs(a - dur)))
        if dur == 4.0:      # whole rest hangs from the 4th line
            d.text((cx, top_y + s), glyph, font=rest_font, fill=_INK, anchor="mm")
        elif dur == 2.0:    # half rest sits on the middle line
            d.text((cx, top_y + 2 * s - s * 0.55), glyph, font=rest_font, fill=_INK, anchor="mm")
        else:
            d.text((cx, top_y + 2 * s), glyph, font=rest_font, fill=_INK, anchor="mm")
        return

    step, acc = pitch_to_step(note["p"])
    cy = step_y(step, bottom_y)
    hw, hh = s * 1.35, s * 0.98

    # Ledger lines
    if step < _BOTTOM_STEP:
        for st in range(_BOTTOM_STEP - 2, step - 1, -2):
            y = step_y(st, bottom_y)
            d.line([(cx - hw * 0.95, y), (cx + hw * 0.95, y)], fill=_INK, width=2)
    if step > _TOP_STEP:
        for st in range(_TOP_STEP + 2, step + 1, 2):
            y = step_y(st, bottom_y)
            d.line([(cx - hw * 0.95, y), (cx + hw * 0.95, y)], fill=_INK, width=2)

    if acc:
        d.text((cx - hw - s * 0.35, cy), "♯" if acc == "#" else "♭", font=acc_font, fill=_INK, anchor="mm")

    head = [cx - hw / 2, cy - hh / 2, cx + hw / 2, cy + hh / 2]
    filled = dur < 2.0
    if filled:
        d.ellipse(head, fill=_INK)
    else:
        d.ellipse(head, outline=_INK, width=3)

    if dur < 4.0:
        up = step < 34
        stem_len = s * 3.5
        if up:
            sx = cx + hw / 2 - 1
            ey = cy - stem_len
            d.line([(sx, cy), (sx, ey)], fill=_INK, width=3)
        else:
            sx = cx - hw / 2 + 1
            ey = cy + stem_len
            d.line([(sx, cy), (sx, ey)], fill=_INK, width=3)
        flags = 2 if dur <= 0.25 else 1 if dur <= 0.75 else 0
        for f in range(flags):
            off = f * s * 0.7
            if up:
                y0 = ey + off
                d.line([(sx, y0), (sx + s * 0.9, y0 + s * 0.9), (sx + s * 0.8, y0 + s * 1.9)], fill=_INK, width=4)
            else:
                y0 = ey - off
                d.line([(sx, y0), (sx + s * 0.9, y0 - s * 0.9), (sx + s * 0.8, y0 - s * 1.9)], fill=_INK, width=4)

    if dur in (3.0, 1.5, 0.75):
        dy = cy - s / 2 if step % 2 == 0 else cy
        d.ellipse([cx + hw / 2 + 5, dy - 3, cx + hw / 2 + 11, dy + 3], fill=_INK)
