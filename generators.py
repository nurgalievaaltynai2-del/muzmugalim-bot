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

# Extra structure requirements per material: name -> (kazakh, russian)
MATERIAL_HINTS = {
    "Ашық сабақ жоспары": (
        "Ашық сабақтың толық жоспары: тақырып, мақсаты мен міндеттері, құрал-жабдық, сабақ кезеңдері "
        "(ұйымдастыру, жаңа материал, бекіту, қорытынды, рефлексия) уақытымен, мұғалім мен оқушы әрекеті, бағалау.",
        "Полный план открытого урока: тема, цель и задачи, оборудование, этапы урока "
        "(организация, новый материал, закрепление, итог, рефлексия) с таймингом, деятельность учителя и учеников, оценивание.",
    ),
    "Сабақты өзін-өзі талдау": (
        "Музыка сабағын өзін-өзі талдау: мақсатқа жету, сабақ құрылымы, әдіс-тәсілдер, оқушылардың белсенділігі, "
        "күшті жақтары, қиындықтар, түзету жолдары, қорытынды.",
        "Самоанализ урока музыки: достижение цели, структура урока, методы и приёмы, активность учеников, "
        "сильные стороны, затруднения, пути коррекции, вывод.",
    ),
    "Үйірме жоспары": (
        "Музыкалық үйірменің жылдық/тоқсандық жоспары: мақсаты, жас ерекшелігі, апта-апта сабақ тақырыптары, "
        "репертуар, күтілетін нәтиже, есеп беру концерті.",
        "План музыкального кружка на год/четверть: цель, возраст, темы занятий по неделям, "
        "репертуар, ожидаемые результаты, отчётный концерт.",
    ),
    "Сыныптан тыс іс-шара": (
        "Сыныптан тыс музыкалық іс-шара сценарийі: атауы, мақсаты, безендіру, жүргізушінің сөзі, "
        "нөмірлердің ретімен тізімі, ойын-сайыс, қорытынды.",
        "Сценарий внеклассного музыкального мероприятия: название, цель, оформление, слова ведущего, "
        "порядок номеров, игры-конкурсы, итог.",
    ),
    "Музыкалық терминдер сөздігі": (
        "Тақырып бойынша музыкалық терминдер сөздігі: 15–20 термин, әрқайсысына қысқа түсініктеме мен мысал; әліпби ретімен.",
        "Словарь музыкальных терминов по теме: 15–20 терминов, к каждому краткое объяснение и пример; по алфавиту.",
    ),
    "Жұмбақтар": (
        "Тақырып бойынша 10–12 музыкалық жұмбақ, әрқайсысының жауабымен. Оқушыға түсінікті, рифмалы болсын.",
        "10–12 музыкальных загадок по теме, каждая с ответом. Понятные ученикам, по возможности в рифму.",
    ),
    "Конкурс жоспары": (
        "Музыкалық конкурс жоспары: мақсаты, номинациялар, қатысушылар, қазылар алқасы, бағалау критерийлері мен балл кестесі, "
        "өткізу реті, марапаттау.",
        "План музыкального конкурса: цель, номинации, участники, жюри, критерии оценивания и таблица баллов, "
        "порядок проведения, награждение.",
    ),
    "Флешмоб сценарийі": (
        "Музыкалық флешмоб сценарийі: идеясы, қатысушылар саны, музыка таңдауы, қимыл-қозғалыс (санамен), "
        "орын мен уақыт, қауіпсіздік, дайындық кезеңдері.",
        "Сценарий музыкального флешмоба: идея, число участников, выбор музыки, движения (по счётам), "
        "место и время, безопасность, этапы подготовки.",
    ),
    "Шу оркестрі": (
        "Балабақша үшін шу оркестрі: қарапайым аспаптар (қасық, сылдырмақ, бубен, барабан), "
        "әр аспаптың партиясы ырғақпен, жүргізу тәсілі, әуен таңдауы, ойын элементі.",
        "Шумовой оркестр для детского сада: простые инструменты (ложки, погремушки, бубен, барабан), "
        "партия каждого инструмента в ритме, приёмы дирижирования, выбор мелодии, игровые элементы.",
    ),
    "Наурыз сценарийі": (
        "Балабақшада Наурыз мерекесі сценарийі: кейіпкерлер, ән-би, ұлттық ойындар, көрмелер, "
        "сөздері мен ремарка, музыкалық нөмірлер тізімі.",
        "Сценарий праздника Наурыз в детском саду: персонажи, песни и танцы, национальные игры, "
        "слова и ремарки, список музыкальных номеров.",
    ),
    "Жаңа жыл сценарийі": (
        "Балабақшада Жаңа жыл мерекесі сценарийі: Аяз ата, Қарқыз, кейіпкерлер, ән-би, ойындар, "
        "сөздері мен ремарка, сыйлық беру сәті.",
        "Сценарий новогоднего утренника в детском саду: Дед Мороз, Снегурочка, персонажи, песни и танцы, игры, "
        "слова и ремарки, вручение подарков.",
    ),
    "Туған күн сценарийі": (
        "Балабақшада туған күн мерекесі сценарийі: жүргізуші, ойындар, әндер, тілек, торт сәті, "
        "бала мен ата-анаға арналған нөмірлер.",
        "Сценарий дня рождения в детском саду: ведущий, игры, песни, пожелания, момент с тортом, "
        "номера для именинника и родителей.",
    ),
    "Бітіру кеші": (
        "Балабақшаны бітіру кеші сценарийі: салтанатты кіріспе, балалардың өлеңдері мен әндері, би, "
        "тәрбиешілерге алғыс, ата-аналарға сөз, куәлік тапсыру, қоштасу.",
        "Сценарий выпускного в детском саду: торжественное начало, стихи и песни детей, танец, "
        "благодарность воспитателям, слово родителям, вручение свидетельств, прощание.",
    ),
    "Утренник": (
        "Балабақша утреннигінің сценарийі: тақырыбы, кейіпкерлер, кезең-кезеңімен өту, ән, би, ойын, "
        "костюм мен безендіру, музыкалық сүйемелдеу.",
        "Сценарий утренника в детском саду: тема, персонажи, ход по этапам, песни, танцы, игры, "
        "костюмы и оформление, музыкальное сопровождение.",
    ),
    "Ашық есік күні": (
        "Балабақшаның Ашық есік күні жоспары: ата-аналарды қарсы алу, музыкалық сабақ көрсетілімі, "
        "балалар нөмірлері, ата-анамен бірге ойындар, пікір алу.",
        "План Дня открытых дверей в детском саду: встреча родителей, показ музыкального занятия, "
        "номера детей, совместные игры с родителями, обратная связь.",
    ),
    "Ата-ана жиналысы": (
        "Музыкалық тәрбие бойынша ата-ана жиналысы: күн тәртібі, баяндама, балалардың жетістіктері, "
        "ата-аналарға кеңес, тәжірибелік тапсырма, шешім жобасы.",
        "Родительское собрание по музыкальному воспитанию: повестка, доклад, достижения детей, "
        "советы родителям, практическое задание, проект решения.",
    ),
}


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
    hint = MATERIAL_HINTS.get(material_name)
    if hint:
        instruction += (
            f"\n\nМіндетті құрылым: {hint[0]}" if lang != "ru"
            else f"\n\nОбязательная структура: {hint[1]}"
        )
    response = await asyncio.to_thread(
        _gemini.models.generate_content,
        model="gemini-2.5-flash",
        contents=instruction,
    )
    return response.text


# ─── AI assistant ("💬 Сұрақ қою") ────────────────────────────────────────────

_ASK_MAX_QUESTION = 2000


async def gen_answer(question: str) -> str:
    """Answer a music teacher's free-form question in the language it was written in."""
    instruction = (
        "Сен — MuzMugalim Bot, Қазақстандағы музыка мұғалімдеріне арналған AI көмекші. "
        "Ты — AI-помощник учителей музыки в Казахстане.\n"
        "Жауапты пайдаланушы сұрақты қай тілде жазса, сол тілде бер (қазақша немесе орысша). / "
        "Отвечай на том языке, на котором написан вопрос.\n"
        "Тек музыка сабағы, музыкалық тәрбие және оқыту әдістемесі бойынша нақты, қысқа әрі пайдалы жауап бер. "
        "Тақырыптан тыс сұраққа сыпайы түрде музыка мұғаліміне қатысты тақырыпқа бағыттап жауап бер.\n\n"
        f"Сұрақ / Вопрос:\n{question[:_ASK_MAX_QUESTION]}"
    )
    response = await asyncio.to_thread(
        _gemini.models.generate_content,
        model="gemini-2.5-flash",
        contents=instruction,
    )
    answer = (response.text or "").strip()
    if not answer:
        raise ValueError("Gemini бос жауап қайтарды")
    return answer


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


# ─── Image (DALL-E 3 / Gemini) ────────────────────────────────────────────────

class ImageGenError(Exception):
    """Image generation failed. `user_message` explains the reason to the teacher."""

    def __init__(self, user_message: str, detail: str = ""):
        super().__init__(detail or user_message)
        self.user_message = user_message


class NoImageReturned(ValueError):
    """The image model answered but did not return a picture (usually a safety filter)."""


def _error_status(exc: Exception):
    """HTTP status of an API failure (httpx or google-genai), or None."""
    resp = getattr(exc, "response", None)
    status = getattr(resp, "status_code", None)
    if isinstance(status, int):
        return status
    code = getattr(exc, "code", None)
    return code if isinstance(code, int) else None


def _error_body(exc: Exception) -> str:
    """Body/message of an API failure for the log."""
    resp = getattr(exc, "response", None)
    text = getattr(resp, "text", None)
    if isinstance(text, str) and text:
        return text[:2000]
    message = getattr(exc, "message", None)
    return str(message)[:2000] if message else ""


def describe_image_error(exc: Exception) -> str:
    """Plain-language reason (Kazakh / Russian) why a picture could not be made."""
    status = _error_status(exc)
    body = _error_body(exc).lower()
    if isinstance(exc, (httpx.TimeoutException, TimeoutError, asyncio.TimeoutError)):
        return "AI сервисі уақытында жауап бермеді. Бірнеше минуттан кейін қайталаңыз.\n_Сервис не ответил вовремя, повторите позже._"
    if isinstance(exc, NoImageReturned) or "content_policy" in body or "safety" in body:
        return (
            "AI бұл тақырыпқа сурет жасамады (қауіпсіздік сүзгісі). Тақырыпты басқаша жазып көріңіз.\n"
            "_ИИ не нарисовал картинку (фильтр безопасности). Переформулируйте тему._"
        )
    if status in (401, 403):
        return (
            "Сурет сервисіне қолжетімділік жоқ (API кілті жарамсыз). Әкімшіге хабарласыңыз: @muzmugalim.\n"
            "_Нет доступа к сервису картинок (неверный API-ключ). Напишите @muzmugalim._"
        )
    if status == 429 or "quota" in body or "billing" in body:
        return (
            "Сурет сервисінің лимиті/квотасы толды. Кейінірек қайталаңыз.\n"
            "_Лимит сервиса картинок исчерпан, повторите позже._"
        )
    if status is not None and status >= 500:
        return (
            "Сурет сервисі уақытша істемей тұр. Бірнеше минуттан кейін қайталаңыз.\n"
            "_Сервис картинок временно недоступен, повторите позже._"
        )
    if status == 400:
        return (
            "Сурет сұранысы қабылданбады. Тақырыпты қысқартып, басқаша жазып көріңіз.\n"
            "_Запрос отклонён. Попробуйте переформулировать тему._"
        )
    return (
        "Сурет жасау кезінде күтпеген қате шықты. Кейінірек қайталаңыз.\n"
        "_Непредвиденная ошибка при создании картинки, повторите позже._"
    )


def _log_image_failure(provider: str, section: str, topic: str, exc: Exception):
    logger.error(
        "image generation failed: provider=%s section=%s topic=%r exc=%s: %s status=%s body=%s",
        provider, section, topic, type(exc).__name__, exc, _error_status(exc), _error_body(exc),
        exc_info=exc,
    )


async def _gen_image_gemini(prompt: str) -> bytes:
    from google.genai import types

    response = await asyncio.to_thread(
        _gemini.models.generate_content,
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    texts = []
    for cand in response.candidates or []:
        for part in (cand.content.parts if cand.content and cand.content.parts else []):
            if part.inline_data and part.inline_data.data:
                return part.inline_data.data
            if getattr(part, "text", None):
                texts.append(part.text)
    finish = [str(getattr(c, "finish_reason", "")) for c in response.candidates or []]
    raise NoImageReturned(
        f"Gemini сурет қайтармады: finish_reason={finish} "
        f"prompt_feedback={getattr(response, 'prompt_feedback', None)} text={' '.join(texts)[:500]!r}"
    )


async def _gen_image_openai(prompt: str) -> bytes:
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


async def gen_poster(section: str, material_name: str, topic: str, kind: str = "poster") -> bytes:
    """Generate a picture. On failure logs the full cause and raises ImageGenError."""
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

    # No OpenAI key configured: use Gemini image generation instead
    provider = "openai" if _OPENAI_KEY else "gemini"
    try:
        if provider == "gemini":
            return await _gen_image_gemini(prompt)
        return await _gen_image_openai(prompt)
    except Exception as e:
        _log_image_failure(provider, section, topic, e)
        raise ImageGenError(describe_image_error(e), detail=f"{type(e).__name__}: {e}") from e


async def gen_slide_images(section: str, topic: str, slides: list, max_content: int = 4) -> tuple[dict, str]:
    """Pictures for a presentation: cover (-1) plus the first `max_content` slides.

    Returns ({index: png_bytes} for the ones that succeeded, reason shown to the user if none did).
    """
    targets = [(-1, topic)] + [
        (i, f"{topic}: {slides[i]['title']}") for i in range(min(max_content, len(slides)))
    ]
    sem = asyncio.Semaphore(3)

    async def one(idx, subject):
        async with sem:
            return idx, await gen_poster(section, "", subject, kind="visual")

    results = await asyncio.gather(*(one(i, t) for i, t in targets), return_exceptions=True)
    images, reason = {}, ""
    for r in results:
        if isinstance(r, Exception):
            # gen_poster already logged the full cause
            reason = getattr(r, "user_message", "") or describe_image_error(r)
        else:
            images[r[0]] = r[1]
    return images, ("" if images else reason)

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
