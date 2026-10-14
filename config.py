import os
from dataclasses import dataclass
from enum import Enum


class MType(str, Enum):
    TEXT = "text"
    POSTER = "poster"
    MUSIC = "music"


PLAN_RANK = {"free": 0, "basic": 1, "standard": 2, "premium": 3}  # free kept for DB compat

PAGE_SIZE = 8


@dataclass
class Material:
    name: str
    mtype: MType
    min_plan: str
    name_ru: str = ""
    # "text" = plain text, "visual" = text + illustration, "pptx" = PowerPoint file,
    # "notes" = text + sheet music image
    output: str = "text"


# ─── Мектеп: 37 materials ────────────────────────────────────────────────────
# Мектеп 37 + Балабақша 41 = 78 materials in total

MEKTEP_MATERIALS = [
    # ── Basic (30 text) ──
    Material("Көрнекілік",         MType.TEXT,   "basic",    "Наглядное пособие", output="visual"),
    Material("Презентация",        MType.TEXT,   "basic",    "Презентация", output="pptx"),
    Material("Тест сұрақтары",     MType.TEXT,   "basic",    "Тест"),
    Material("ҚМЖ/КТЖ",           MType.TEXT,   "basic",    "КТП/КСП"),
    Material("Сабақ жоспары",      MType.TEXT,   "basic",    "План урока"),
    Material("Рубрика",            MType.TEXT,   "basic",    "Рубрика"),
    Material("Ноталар",            MType.TEXT,   "basic",    "Ноты", output="notes"),
    Material("Музыкалық диктант",  MType.TEXT,   "basic",    "Музыкальный диктант", output="notes"),
    Material("Дауыс жаттығулары",  MType.TEXT,   "basic",    "Вокальные упражнения", output="notes"),
    Material("Сергіту сәті",       MType.TEXT,   "basic",    "Физминутка"),
    Material("Сәлемдесу ойыны",    MType.TEXT,   "basic",    "Приветствие"),
    Material("Музыкалық ойын",     MType.TEXT,   "basic",    "Музыкальная игра"),
    Material("Саусақ ойыны",       MType.TEXT,   "basic",    "Пальчиковая игра"),
    Material("Демалыс сәті",       MType.TEXT,   "basic",    "Отдых"),
    Material("Ән сөздері",         MType.TEXT,   "basic",    "Текст песни", output="notes"),
    Material("Балалар әндері",     MType.TEXT,   "basic",    "Детские песни", output="notes"),
    Material("Репертуар тізімі",   MType.TEXT,   "basic",    "Репертуар"),
    Material("Хор жоспары",        MType.TEXT,   "basic",    "Хоровой план"),
    Material("Ата-анаға хат",      MType.TEXT,   "basic",    "Письмо родителям"),
    Material("Викторина",          MType.TEXT,   "basic",    "Викторина"),
    Material("Кросворд",           MType.TEXT,   "basic",    "Кроссворд"),
    Material("📜 Композитор биографиясы", MType.TEXT, "basic", "Биография композитора"),
    Material("🎹 Аспап таныстыру",        MType.TEXT, "basic", "Знакомство с инструментом"),
    Material("📊 Оқушы бағалау парағы",   MType.TEXT, "basic", "Оценочный лист ученика"),
    Material("Ашық сабақ жоспары",        MType.TEXT, "basic", "План открытого урока"),
    Material("Сабақты өзін-өзі талдау",   MType.TEXT, "basic", "Самоанализ урока"),
    Material("Үйірме жоспары",            MType.TEXT, "basic", "План кружка"),
    Material("Сыныптан тыс іс-шара",      MType.TEXT, "basic", "Внеклассное мероприятие"),
    Material("Музыкалық терминдер сөздігі", MType.TEXT, "basic", "Словарь музыкальных терминов"),
    Material("Жұмбақтар",                 MType.TEXT, "basic", "Загадки"),
    # ── Standard ──
    Material("Сурет",              MType.POSTER, "standard", "Рисунок DALL-E 3"),
    Material("Портфолио",          MType.TEXT,   "standard", "Портфолио"),
    # ── Premium ──
    Material("Музыка MP3",         MType.MUSIC,  "premium",  "Музыка MP3 Suno"),
    Material("Рефлексия",          MType.TEXT,   "premium",  "Рефлексия"),
    Material("Дифф. тапсырма",     MType.TEXT,   "premium",  "Дифф. задание"),
    Material("Конкурс жоспары",    MType.TEXT,   "premium",  "План конкурса"),
    Material("Флешмоб сценарийі",  MType.TEXT,   "premium",  "Сценарий флешмоба"),
]

# ─── Балабақша: 41 materials ─────────────────────────────────────────────────

BALABAQSHA_MATERIALS = [
    # ── Basic (28 text) ──
    Material("Жылдық жоспар",     MType.TEXT,   "basic",    "Годовой план"),
    Material("Айлық жоспар",      MType.TEXT,   "basic",    "Месячный план"),
    Material("Аптасабақ",         MType.TEXT,   "basic",    "Недельный план"),
    Material("Циклограмма",       MType.TEXT,   "basic",    "Циклограмма"),
    Material("Көрнекілік",        MType.TEXT,   "basic",    "Наглядное пособие", output="visual"),
    Material("Ән сөздері",        MType.TEXT,   "basic",    "Текст песни", output="notes"),
    Material("Би жоспары",        MType.TEXT,   "basic",    "План танца"),
    Material("Таңғы гимнастика",  MType.TEXT,   "basic",    "Утренняя гимнастика"),
    Material("Логоритмика",       MType.TEXT,   "basic",    "Логоритмика"),
    Material("Сергіту",           MType.TEXT,   "basic",    "Физминутка"),
    Material("Сәлемдесу",         MType.TEXT,   "basic",    "Приветствие"),
    Material("Демалыс",           MType.TEXT,   "basic",    "Отдых"),
    Material("Музыкалық ойын",    MType.TEXT,   "basic",    "Музыкальная игра"),
    Material("Дидактикалық ойын", MType.TEXT,   "basic",    "Дидактическая игра"),
    Material("Дамытушы ойын",     MType.TEXT,   "basic",    "Развивающая игра"),
    Material("Саусақ ойыны",      MType.TEXT,   "basic",    "Пальчиковая игра"),
    Material("Аң дыбыстары",      MType.TEXT,   "basic",    "Звуки животных"),
    Material("Қол соғу",          MType.TEXT,   "basic",    "Хлопки"),
    Material("Тыныш-шулы",        MType.TEXT,   "basic",    "Тихо-громко"),
    Material("Музыкалық орындық", MType.TEXT,   "basic",    "Музыкальный стул"),
    Material("Түс пен дыбыс",     MType.TEXT,   "basic",    "Цвет и звук"),
    Material("Музыкалық викторина",MType.TEXT,  "basic",    "Музыкальная викторина"),
    Material("Ұйқы алдындағы ән", MType.TEXT,   "basic",    "Колыбельная", output="notes"),
    Material("Таңғы ән",          MType.TEXT,   "basic",    "Утренняя песня", output="notes"),
    Material("Репертуар тізімі",  MType.TEXT,   "basic",    "Репертуар"),
    Material("Ата-анаға хат",     MType.TEXT,   "basic",    "Письмо родителям"),
    Material("Үй тапсырмасы",     MType.TEXT,   "basic",    "Домашнее задание"),
    Material("Шу оркестрі",       MType.TEXT,   "basic",    "Шумовой оркестр"),
    # ── Standard ──
    Material("Сурет",             MType.POSTER, "standard", "Рисунок DALL-E 3"),
    Material("Портфолио",         MType.TEXT,   "standard", "Портфолио"),
    # ── Premium ──
    Material("Музыка MP3",        MType.MUSIC,  "premium",  "Музыка MP3 Suno"),
    Material("Музыка терапия",    MType.TEXT,   "premium",  "Музыкотерапия"),
    Material("Бейімдеу",          MType.TEXT,   "premium",  "Адаптация"),
    Material("Даму картасы",      MType.TEXT,   "premium",  "Карта развития"),
    Material("Наурыз сценарийі",  MType.TEXT,   "premium",  "Сценарий Наурыза"),
    Material("Жаңа жыл сценарийі", MType.TEXT,  "premium",  "Сценарий Нового года"),
    Material("Туған күн сценарийі", MType.TEXT, "premium",  "Сценарий дня рождения"),
    Material("Бітіру кеші",       MType.TEXT,   "premium",  "Выпускной утренник"),
    Material("Утренник",          MType.TEXT,   "premium",  "Утренник"),
    Material("Ашық есік күні",    MType.TEXT,   "premium",  "День открытых дверей"),
    Material("Ата-ана жиналысы",  MType.TEXT,   "premium",  "Родительское собрание"),
]

SECTIONS = {
    "mektep":     {"label": "🏫 Мектеп",    "materials": MEKTEP_MATERIALS},
    "balabaqsha": {"label": "🎪 Балабақша", "materials": BALABAQSHA_MATERIALS},
}

# ─── Tariffs ──────────────────────────────────────────────────────────────────
# text/poster/music: None = unlimited, 0 = no access, N = monthly limit

TARIFFS = {
    "basic":    {"name": "Базалық",  "price": 6990,  "text": None, "poster": 0,    "music": 0},
    "standard": {"name": "Стандарт", "price": 8990,  "text": None, "poster": 30,   "music": 0},
    "premium":  {"name": "Премиум",  "price": 14990, "text": None, "poster": 50,   "music": 10},
}

# "💬 Сұрақ қою" (AI assistant): available on every paid tariff, N questions per day
ASK_DAILY_LIMIT = 30

ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
USERS_FILE = "users.json"
