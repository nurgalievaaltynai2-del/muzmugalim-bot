import asyncio
import io
import os

import httpx
from google import genai
from google.genai import types

_gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "").strip())

_SYSTEM = (
    "Сен — MuzMugalim Bot, Қазақстандағы музыка мұғалімдеріне арналған AI көмекші. "
    "Барлық жауапты тек қазақ тілінде бер. Нақты, пайдаланылуға дайын материал жаса. "
    "Форматтау анық болсын: тақырыптар, нөмірлер, бөлімдер қолдан."
)


# ─── Text ────────────────────────────────────────────────────────────────────

def _build_text_prompt(section: str, material_name: str, topic: str) -> str:
    section_label = "мектепке" if section == "mektep" else "балабақшаға"
    return (
        f"{_SYSTEM}\n\n"
        f"Бөлім: {section_label} арналған материал.\n"
        f"Материал түрі: {material_name}\n"
        f"Тақырып: {topic}\n\n"
        f"Осы тақырыпқа «{material_name}» дайында. Тек қазақша жауап бер."
    )


async def gen_text(section: str, material_name: str, topic: str) -> str:
    prompt = _build_text_prompt(section, material_name, topic)
    response = await asyncio.to_thread(
        _gemini.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


# ─── Poster (Imagen 4 Fast) ───────────────────────────────────────────────────

def _build_poster_prompt(section: str, material_name: str, topic: str) -> str:
    section_label = "school music class" if section == "mektep" else "kindergarten music class"
    return (
        f"Educational poster for a {section_label} in Kazakhstan. "
        f"Topic: {topic}. Style: bright, child-friendly, colorful illustration. "
        f"Include musical notes, instruments, and Kazakh cultural elements. "
        f"High quality, clean design suitable for classroom display."
    )


async def gen_poster(section: str, material_name: str, topic: str) -> bytes:
    prompt = _build_poster_prompt(section, material_name, topic)
    result = await asyncio.to_thread(
        _gemini.models.generate_images,
        model="imagen-4.0-fast-generate-001",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",
        ),
    )
    return result.generated_images[0].image.image_bytes


# ─── Music (Suno API) ─────────────────────────────────────────────────────────

_SUNO_BASE = os.getenv("SUNO_BASE_URL", "").rstrip("/")
_SUNO_KEY = os.getenv("SUNO_API_KEY", "").strip()


def _build_music_prompt(section: str, material_name: str, topic: str) -> str:
    section_label = "мектеп" if section == "mektep" else "балабақша"
    return (
        f"Қазақ балалар музыкасы, {section_label} үшін, тақырып: {topic}. "
        f"Жарқын, оптимистік, педагогикалық мақсатқа арналған."
    )


async def gen_music(section: str, material_name: str, topic: str) -> tuple:
    """Returns (mp3_bytes: bytes, title: str)"""
    if not _SUNO_BASE or not _SUNO_KEY:
        raise RuntimeError("SUNO_BASE_URL немесе SUNO_API_KEY орнатылмаған")

    prompt = _build_music_prompt(section, material_name, topic)

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{_SUNO_BASE}/api/generate",
            headers={"Authorization": f"Bearer {_SUNO_KEY}"},
            json={
                "prompt": prompt,
                "make_instrumental": False,
                "wait_audio": True,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data, list) and data:
        item = data[0]
    elif isinstance(data, dict):
        item = data
    else:
        raise ValueError("Suno API жауабы дұрыс емес")

    audio_url = item.get("audio_url") or item.get("url", "")
    title = item.get("title") or item.get("name") or topic

    if not audio_url:
        raise ValueError("Suno API audio_url қайтармады")

    async with httpx.AsyncClient(timeout=60) as client:
        audio_resp = await client.get(audio_url)
        audio_resp.raise_for_status()
        return audio_resp.content, title


# ─── Helpers ─────────────────────────────────────────────────────────────────

def split_long_message(text: str, limit: int = 4000) -> list:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts
