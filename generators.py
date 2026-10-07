import asyncio
import json
import logging
import os
import re
import httpx

import notation
from google import genai

logger = logging.getLogger(__name__)
_gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "").strip())
_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_SUNO_BASE = os.getenv("SUNO_BASE_URL", "").rstrip("/")
_SUNO_KEY = os.getenv("SUNO_API_KEY", "").strip()


# ─── Text (Gemini 2.5 Flash) ──────────────────────────────────────────────────

async def gen_text(section: str, material_name: str, topic: str, lang: str = "kz", name_ru: str = "") -> str:
    section_label = "мектепке" if section == "mektep" else "балабақшаға"
    if lang == "ru":
        ru_name = name_ru or material_name
        section_ru = "школы" if section == "mektep" else "детского сада"
        instruction = (
            f"Ты — MuzMugalim Bot, AI-помощник для учителей музыки в Казахстане. "
            f"Отвечай ТОЛЬКО на русском языке. Создай готовый к использованию материал.\n\n"
            f"Раздел: для {section_ru}\n"
            f"Тип материала: {ru_name}\n"
            f"Тема: {topic}\n\n"
            f"Подготовь «{ru_name}» по данной теме."
        )
    else:
        instruction = (
            f"Сен — MuzMugalim Bot, Қазақстандағы музыка мұғалімдеріне арналған AI көмекші. "
            f"Барлық жауапты тек қазақ тілінде бер. Нақты, пайдаланылуға дайын материал жаса.\n\n"
            f"Бөлім: {section_label} арналған материал.\n"
            f"Материал түрі: {material_name}\n"
            f"Тақырып: {topic}\n\n"
            f"Осы тақырыпқа «{material_name}» дайында."
        )
    response = await asyncio.to_thread(
        _gemini.models.generate_content,
        model="gemini-2.5-flash",
        contents=instruction,
    )
    return response.text


# ─── Presentation (Gemini → slides) ───────────────────────────────────────────

def parse_slides(raw: str) -> list:
    """Parse Gemini JSON output into [{"title": str, "bullets": [str]}]."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError("Презентация форматы дұрыс емес") from e
    items = data.get("slides") if isinstance(data, dict) else data
    slides = []
    for it in items or []:
        if not isinstance(it, dict) or not it.get("title"):
            continue
        bullets = [str(b).strip() for b in it.get("bullets", []) if str(b).strip()]
        slides.append({"title": str(it["title"]).strip(), "bullets": bullets})
    if not slides:
        raise ValueError("Презентацияда слайд жоқ")
    return slides


async def gen_slides(section: str, topic: str, lang: str = "kz") -> list:
    audience = "школы" if section == "mektep" else "детского сада"
    audience_kz = "мектепке" if section == "mektep" else "балабақшаға"
    if lang == "ru":
        instruction = (
            f"Ты — AI-помощник учителя музыки в Казахстане. Отвечай ТОЛЬКО на русском. "
            f"Подготовь презентацию для {audience} по теме «{topic}»."
        )
    else:
        instruction = (
            f"Сен — Қазақстандағы музыка мұғаліміне арналған AI көмекші. Тек қазақ тілінде жауап бер. "
            f"«{topic}» тақырыбына {audience_kz} арналған презентация дайында."
        )
    instruction += (
        '\n\nТек JSON қайтар / Return ONLY JSON: {"slides": [{"title": "...", "bullets": ["...", "..."]}]}. '
        "8–10 слайд, әр слайдта 3–5 қысқа пункт (әрқайсысы 12 сөзден аспасын). "
        "Бірінші слайд — мақсаты, соңғы слайд — қорытынды/сұрақтар."
    )
    from google.genai import types

    response = await asyncio.to_thread(
        _gemini.models.generate_content,
        model="gemini-2.5-flash",
        contents=instruction,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return parse_slides(response.text)


# ─── Notation (Gemini → melody → sheet music) ─────────────────────────────────

def parse_melody(raw: str) -> dict:
    """Parse Gemini JSON into a melody whose every measure fits the time signature."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError("Ноталар форматы дұрыс емес") from e
    if not isinstance(data, dict):
        raise ValueError("Ноталар форматы дұрыс емес")

    m = re.fullmatch(r"\s*(\d{1,2})\s*/\s*(2|4|8)\s*", str(data.get("time", "4/4")))
    num, den = (int(m.group(1)), int(m.group(2))) if m else (4, 4)
    beats = num * 4 / den

    measures = []
    for bar in data.get("measures") or []:
        notes, total = [], 0.0
        for n in bar if isinstance(bar, list) else []:
            if not isinstance(n, dict):
                continue
            dur = notation.snap_duration(n.get("d"))
            if total + dur > beats + 1e-6:
                break
            pitch = str(n.get("p", "")).strip()
            if pitch.upper() not in ("R", "REST"):
                try:
                    notation.pitch_to_step(pitch)
                except ValueError:
                    continue
            notes.append({"p": pitch, "d": dur, "l": str(n.get("l") or "").strip()})
            total += dur
        if not notes:
            continue
        notes.extend(notation.rest_fill(beats - total))
        measures.append(notes)
    if not measures:
        raise ValueError("Әуенде нота жоқ")

    try:
        tempo = int(data.get("tempo", 90))
    except (TypeError, ValueError):
        tempo = 90
    return {
        "title": str(data.get("title") or "Ноталар").strip(),
        "time": (num, den),
        "beats": beats,
        "tempo": tempo,
        "measures": measures,
    }


async def gen_melody(section: str, topic: str, lang: str = "kz") -> dict:
    audience = "школьников" if section == "mektep" else "детского сада"
    audience_kz = "оқушыларға" if section == "mektep" else "балабақша балаларына"
    if lang == "ru":
        intro = (
            f"Ты — учитель музыки. Сочини короткую простую мелодию для {audience} по теме «{topic}». "
            f"Слова (слоги под нотами) — на русском."
        )
    else:
        intro = (
            f"Сен — музыка мұғалімісің. «{topic}» тақырыбына {audience_kz} арналған қысқа, қарапайым ән әуенін шығар. "
            f"Сөздері (ноталардың астындағы буындар) қазақ тілінде болсын."
        )
    instruction = intro + (
        "\n\nТек JSON қайтар / Return ONLY JSON:\n"
        '{"title": "...", "time": "4/4", "tempo": 96, "measures": ['
        '[{"p": "C4", "d": 1, "l": "сөз"}, {"p": "R", "d": 1}, ...], ...]}\n'
        "Ережелер: ключ — скрипка, тональдық — до мажор (диез/бемольсіз, қажет болса C#4/Bb4 түрінде жаз). "
        "Дыбыс аралығы C4–A5. p — нота (C4, D4, E4, F4, G4, A4, B4, C5 ...) немесе R (үзіліс). "
        "d — ұзақтығы ширек нотамен: 4, 3, 2, 1.5, 1, 0.5. "
        "Әр такт ұзақтығының қосындысы өлшемге тең болсын (4/4 → 4, 3/4 → 3, 2/4 → 2). "
        "8 такт, соңы тұрақты дыбыспен (C4 немесе E4/G4) аяқталсын. "
        "l — сол нотаға сәйкес сөз буыны (бір нота — бір буын), қажет емес жерде бос қалдыр."
    )
    from google.genai import types

    response = await asyncio.to_thread(
        _gemini.models.generate_content,
        model="gemini-2.5-flash",
        contents=instruction,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return parse_melody(response.text)


# ─── Image (DALL-E 3) ─────────────────────────────────────────────────────────

async def _gen_image_gemini(prompt: str) -> bytes:
    from google.genai import types

    response = await asyncio.to_thread(
        _gemini.models.generate_content,
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            return part.inline_data.data
    raise ValueError("Gemini сурет қайтармады")


async def gen_poster(section: str, material_name: str, topic: str, kind: str = "poster") -> bytes:
    section_label = "school music class" if section == "mektep" else "kindergarten music class"
    if kind == "visual":
        prompt = (
            f"Educational visual aid illustration for a {section_label} in Kazakhstan. "
            f"Topic: {topic}. Clear, simple, large central subject on a clean light background, "
            f"child-friendly colorful cartoon style, suitable to show on a classroom screen. "
            f"No text or letters in the image."
        )
    else:
        prompt = (
            f"Educational cartoon-style poster for a {section_label} in Kazakhstan. "
            f"Topic: {topic}. Bright, child-friendly, colorful illustration. "
            f"Include musical notes, instruments, and Kazakh cultural elements. "
            f"High quality, clean design suitable for classroom display. "
            f"Do not put any text, letters or words in the image."
        )

    if not _OPENAI_KEY:
        # No OpenAI key configured: use Gemini image generation instead
        return await _gen_image_gemini(prompt)

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {_OPENAI_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
                "response_format": "url",
            },
        )
        resp.raise_for_status()
        image_url = resp.json()["data"][0]["url"]

    async with httpx.AsyncClient(timeout=60) as client:
        img_resp = await client.get(image_url)
        img_resp.raise_for_status()
        return img_resp.content


async def gen_slide_images(section: str, topic: str, slides: list, max_content: int = 4) -> dict:
    """Pictures for a presentation: cover (-1) plus the first `max_content` slides.

    Returns {index: png_bytes} for the ones that succeeded; failures are skipped.
    """
    targets = [(-1, topic)] + [
        (i, f"{topic}: {slides[i]['title']}") for i in range(min(max_content, len(slides)))
    ]
    sem = asyncio.Semaphore(3)

    async def one(idx, subject):
        async with sem:
            return idx, await gen_poster(section, "", subject, kind="visual")

    results = await asyncio.gather(*(one(i, t) for i, t in targets), return_exceptions=True)
    images = {}
    for r in results:
        if isinstance(r, Exception):
            logger.error("slide image error: %s", r)
        else:
            images[r[0]] = r[1]
    return images


# ─── Music (Suno AI) ──────────────────────────────────────────────────────────

async def gen_music(section: str, material_name: str, topic: str) -> tuple[bytes, str]:
    if not _SUNO_BASE or not _SUNO_KEY:
        raise RuntimeError("SUNO_BASE_URL немесе SUNO_API_KEY орнатылмаған")

    section_label = "мектеп" if section == "mektep" else "балабақша"
    prompt = (
        f"Қазақ балалар музыкасы, {section_label} үшін, тақырып: {topic}. "
        f"Жарқын, оптимистік, педагогикалық мақсатқа арналған."
    )

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{_SUNO_BASE}/api/generate",
            headers={"Authorization": f"Bearer {_SUNO_KEY}"},
            json={"prompt": prompt, "make_instrumental": False, "wait_audio": True},
        )
        resp.raise_for_status()
        data = resp.json()

    item = data[0] if isinstance(data, list) and data else data
    audio_url = item.get("audio_url") or item.get("url", "")
    title = item.get("title") or item.get("name") or topic

    if not audio_url:
        raise ValueError("Suno API audio_url қайтармады")

    async with httpx.AsyncClient(timeout=60) as client:
        audio_resp = await client.get(audio_url)
        audio_resp.raise_for_status()
        return audio_resp.content, title


# ─── Helpers ──────────────────────────────────────────────────────────────────

def split_long_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts
