import asyncio
import os
import httpx

from google import genai

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


# ─── Image (DALL-E 3) ─────────────────────────────────────────────────────────

async def gen_poster(section: str, material_name: str, topic: str) -> bytes:
    if not _OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY орнатылмаған")

    section_label = "school music class" if section == "mektep" else "kindergarten music class"
    prompt = (
        f"Educational cartoon-style poster for a {section_label} in Kazakhstan. "
        f"Topic: {topic}. Bright, child-friendly, colorful illustration. "
        f"Include musical notes, instruments, and Kazakh cultural elements. "
        f"High quality, clean design suitable for classroom display."
    )

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
