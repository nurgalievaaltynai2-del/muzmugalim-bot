import io
import os
from datetime import datetime

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_FONT_REGULAR = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
_FONT_BOLD = os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")


def make_pdf(title: str, section_label: str, topic: str, content: str) -> tuple:
    """
    Returns (bytes_io, filename, mime).
    Falls back to plain .txt if fpdf2 or font is unavailable.
    """
    try:
        return _make_fpdf(title, section_label, topic, content)
    except Exception:
        return _make_txt(title, topic, content)


def _make_fpdf(title, section_label, topic, content):
    from fpdf import FPDF  # type: ignore

    if not os.path.exists(_FONT_REGULAR):
        raise FileNotFoundError("DejaVu font not found")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    pdf.add_font("DejaVu", fname=_FONT_REGULAR)
    bold_path = _FONT_BOLD if os.path.exists(_FONT_BOLD) else _FONT_REGULAR
    pdf.add_font("DejaVu", style="B", fname=bold_path)

    # Header
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 7, f"{section_label}  •  {topic}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 7, datetime.now().strftime("%d.%m.%Y"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_draw_color(180, 180, 180)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(7)

    # Body
    pdf.set_font("DejaVu", "", 11)
    pdf.multi_cell(0, 7, content)

    # Footer
    pdf.set_y(-18)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8, "MuzMugalim Bot  |  @muzmugalim", align="C")

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    safe = "".join(c for c in title if c.isalnum() or c in " _-")[:40]
    return buf, f"{safe}.pdf", "application/pdf"


def _make_txt(title, topic, content):
    text = (
        f"{title}\n"
        f"{'=' * 50}\n"
        f"Тақырып / Тема: {topic}\n"
        f"{'=' * 50}\n\n"
        f"{content}\n\n"
        f"{'=' * 50}\n"
        f"MuzMugalim Bot | @muzmugalim"
    )
    buf = io.BytesIO(text.encode("utf-8"))
    safe = "".join(c for c in title if c.isalnum() or c in " _-")[:40]
    return buf, f"{safe}.txt", "text/plain"
