import io
from datetime import datetime

from pptx import Presentation
from pptx.util import Pt

_FOOTER = "MuzMugalim Bot  |  @muzmugalim"


def build_pptx(title: str, section_label: str, slides: list) -> tuple:
    """Build a .pptx from [{"title": str, "bullets": [str]}]. Returns (bytes_io, filename)."""
    prs = Presentation()
    prs.slide_width = Pt(960)   # 16:9
    prs.slide_height = Pt(540)

    cover = prs.slides.add_slide(prs.slide_layouts[0])
    cover.shapes.title.text = title
    cover.placeholders[1].text = f"{section_label}  •  {datetime.now().strftime('%d.%m.%Y')}\n{_FOOTER}"

    for slide in slides:
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = slide["title"]
        tf = s.placeholders[1].text_frame
        tf.clear()
        for i, bullet in enumerate(slide["bullets"]):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.text = bullet
            para.font.size = Pt(26)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    safe = "".join(c for c in title if c.isalnum() or c in " _-")[:40].strip() or "presentation"
    return buf, f"{safe}.pptx"
