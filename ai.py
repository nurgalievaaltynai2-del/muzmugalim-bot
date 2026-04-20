import os
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "").strip())

SYSTEM_BASE = (
    "Сен — MuzMugalim Bot, Қазақстандағы музыка мұғалімдеріне арналған AI көмекші. "
    "Барлық жауапты тек қазақ тілінде бер. Нақты, пайдаланылуға дайын материал жаса. "
    "Форматтау анық болсын: тақырыптар, нөмірлер, бөлімдер қолдан."
)


def build_prompt(section: str, material_name: str, topic: str) -> str:
    section_label = "мектепке" if section == "mektep" else "балабақшаға"
    return (
        f"{SYSTEM_BASE}\n\n"
        f"Мұғалімнің бөлімі: {section_label} арналған материал.\n"
        f"Материал түрі: {material_name}\n"
        f"Тақырып: {topic}\n\n"
        f"Осы тақырыпқа «{material_name}» дайында. Тек қазақша жауап бер."
    )


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


async def generate(section: str, material_name: str, topic: str) -> str:
    prompt = build_prompt(section, material_name, topic)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text
