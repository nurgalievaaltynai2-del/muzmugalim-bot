import os
from dataclasses import dataclass
from enum import Enum


class MType(str, Enum):
    TEXT = "text"
    POSTER = "poster"
    MUSIC = "music"


PLAN_RANK = {"free": 0, "basic": 1, "standard": 2, "premium": 3, "full": 4}  # free kept for DB compat

PAGE_SIZE = 8


@dataclass
class Material:
    name: str
    mtype: MType
    min_plan: str
    name_ru: str = ""


# ─── Мектеп: 29 materials (31 features) ─────────────────────────────────────
# 31 features: surat50 = Сурет at Premium quota, surat100+muzyka20 = Full quota

MEKTEP_MATERIALS = [
    # ── Basic (21 text) ──
    Material("Көрнекілік",         MType.TEXT,   "basic",    "Наглядное пособие"),
    Material("Презентация",        MType.TEXT,   "basic",    "Презентация"),
    Material("Тест сұрақтары",     MType.TEXT,   "basic",    "Тест"),
    Material("ҚМЖ/КТЖ",           MType.TEXT,   "basic",    "КТП/КСП"),
    Material("Сабақ жоспары",      MType.TEXT,   "basic",    "План урока"),
    Material("Рубрика",            MType.TEXT,   "basic",    "Рубрика"),
    Material("Ноталар",            MType.TEXT,   "basic",    "Ноты"),
    Material("Музыкалық диктант",  MType.TEXT,   "basic",    "Музыкальный диктант"),
    Material("Дауыс жаттығулары",  MType.TEXT,   "basic",    "Вокальные упражнения"),
    Material("Сергіту сәті",       MType.TEXT,   "basic",    "Физминутка"),
    Material("Сәлемдесу ойыны",    MType.TEXT,   "basic",    "Приветствие"),
    Material("Музыкалық ойын",     MType.TEXT,   "basic",    "Музыкальная игра"),
    Material("Саусақ ойыны",       MType.TEXT,   "basic",    "Пальчиковая игра"),
    Material("Демалыс сәті",       MType.TEXT,   "basic",    "Отдых"),
    Material("Ән сөздері",         MType.TEXT,   "basic",    "Текст песни"),
    Material("Балалар әндері",     MType.TEXT,   "basic",    "Детские песни"),
    Material("Репертуар тізімі",   MType.TEXT,   "basic",    "Репертуар"),
    Material("Хор жоспары",        MType.TEXT,   "basic",    "Хоровой план"),
    Material("Ата-анаға хат",      MType.TEXT,   "basic",    "Письмо родителям"),
    Material("Викторина",          MType.TEXT,   "basic",    "Викторина"),
    Material("Кросворд",           MType.TEXT,   "basic",    "Кроссворд"),
    # ── Standard ──
    Material("Сурет",              MType.POSTER, "standard", "Рисунок DALL-E 3"),
    Material("Портфолио",          MType.TEXT,   "standard", "Портфолио"),
    # ── Premium ──
    Material("Музыка MP3",         MType.MUSIC,  "premium",  "Музыка MP3 Suno"),
    Material("Рефлексия",          MType.TEXT,   "premium",  "Рефлексия"),
    Material("Дифф. тапсырма",     MType.TEXT,   "premium",  "Дифф. задание"),
    # ── Full ──
    Material("Мерекелік сценарий", MType.TEXT,   "full",     "Праздничный сценарий"),
    Material("Конкурс жоспары",    MType.TEXT,   "full",     "План конкурса"),
    Material("Флешмоб сценарийі",  MType.TEXT,   "full",     "Флешмоб"),
]

# ─── Балабақша: 46 materials (47 features) ───────────────────────────────────
# 47th feature = Сурет at Premium tier (higher quota), same Material object

BALABAQSHA_MATERIALS = [
    # ── Basic (27 text) ──
    Material("Жылдық жоспар",     MType.TEXT,   "basic",    "Годовой план"),
    Material("Айлық жоспар",      MType.TEXT,   "basic",    "Месячный план"),
    Material("Аптасабақ",         MType.TEXT,   "basic",    "Недельный план"),
    Material("Циклограмма",       MType.TEXT,   "basic",    "Циклограмма"),
    Material("Көрнекілік",        MType.TEXT,   "basic",    "Наглядное пособие"),
    Material("Ән сөздері",        MType.TEXT,   "basic",    "Текст песни"),
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
    Material("Ұйқы алдындағы ән", MType.TEXT,   "basic",    "Колыбельная"),
    Material("Таңғы ән",          MType.TEXT,   "basic",    "Утренняя песня"),
    Material("Репертуар тізімі",  MType.TEXT,   "basic",    "Репертуар"),
    Material("Ата-анаға хат",     MType.TEXT,   "basic",    "Письмо родителям"),
    Material("Үй тапсырмасы",     MType.TEXT,   "basic",    "Домашнее задание"),
    # ── Standard ──
    Material("Сурет",             MType.POSTER, "standard", "Рисунок DALL-E 3"),
    Material("Портфолио",         MType.TEXT,   "standard", "Портфолио"),
    # ── Premium ──
    Material("Музыка MP3",        MType.MUSIC,  "premium",  "Музыка MP3 Suno"),
    Material("Музыка терапия",    MType.TEXT,   "premium",  "Музыкотерапия"),
    Material("Бейімдеу",          MType.TEXT,   "premium",  "Адаптация"),
    Material("Даму картасы",      MType.TEXT,   "premium",  "Карта развития"),
    # ── Full (13 scenarios) ──
    Material("Мерекелік сценарий",MType.TEXT,   "full",     "Праздничный сценарий"),
    Material("Наурыз сценарийі",  MType.TEXT,   "full",     "Сценарий Наурыз"),
    Material("Жаңа жыл",          MType.TEXT,   "full",     "Новый год"),
    Material("8 Наурыз",          MType.TEXT,   "full",     "8 Марта"),
    Material("1 Маусым",          MType.TEXT,   "full",     "1 Июня"),
    Material("Туған күн",         MType.TEXT,   "full",     "День рождения"),
    Material("Ертегі",            MType.TEXT,   "full",     "Сказка"),
    Material("Музыкалық ертегі",  MType.TEXT,   "full",     "Музыкальная сказка"),
    Material("Қуыршақ театры",    MType.TEXT,   "full",     "Кукольный театр"),
    Material("Бітіру",            MType.TEXT,   "full",     "Выпускной"),
    Material("Утренник",          MType.TEXT,   "full",     "Утренник"),
    Material("Ашық есік",         MType.TEXT,   "full",     "День открытых дверей"),
    Material("Ата-ана жиналысы",  MType.TEXT,   "full",     "Родительское собрание"),
]

SECTIONS = {
    "mektep":     {"label": "🏫 Мектеп",    "materials": MEKTEP_MATERIALS},
    "balabaqsha": {"label": "🎪 Балабақша", "materials": BALABAQSHA_MATERIALS},
}

# ─── Tariffs ──────────────────────────────────────────────────────────────────
# text/poster/music: None = unlimited, 0 = no access, N = monthly limit

TARIFFS = {
    "basic":    {"name": "Базалық",  "price": 4490,  "text": None, "poster": 0,    "music": 0},
    "standard": {"name": "Стандарт", "price": 6990,  "text": None, "poster": 30,   "music": 0},
    "premium":  {"name": "Премиум",  "price": 10990, "text": None, "poster": 50,   "music": 10},
    "full":     {"name": "Толық",    "price": 14990, "text": None, "poster": 100,  "music": 20},
}

ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
USERS_FILE = "users.json"
