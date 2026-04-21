import os
from dataclasses import dataclass
from enum import Enum


class MType(str, Enum):
    TEXT = "text"
    POSTER = "poster"
    MUSIC = "music"


PLAN_RANK = {"free": 0, "basic": 1, "standard": 2, "premium": 3, "full": 4}


@dataclass
class Material:
    name: str
    mtype: MType
    min_plan: str


PAGE_SIZE = 8

MEKTEP_MATERIALS = [
    # basic (22)
    Material("Көрнекілік", MType.TEXT, "basic"),
    Material("Презентация", MType.TEXT, "basic"),
    Material("Тест", MType.TEXT, "basic"),
    Material("ҚМЖ", MType.TEXT, "basic"),
    Material("КТЖ", MType.TEXT, "basic"),
    Material("Сабақ жоспары", MType.TEXT, "basic"),
    Material("Рубрика", MType.TEXT, "basic"),
    Material("Ноталар", MType.TEXT, "basic"),
    Material("Диктант", MType.TEXT, "basic"),
    Material("Дауыс жаттығулары", MType.TEXT, "basic"),
    Material("Сергіту", MType.TEXT, "basic"),
    Material("Сәлемдесу", MType.TEXT, "basic"),
    Material("Ойын", MType.TEXT, "basic"),
    Material("Саусақ ойыны", MType.TEXT, "basic"),
    Material("Демалыс", MType.TEXT, "basic"),
    Material("Ән сөздері", MType.TEXT, "basic"),
    Material("Балалар әндері", MType.TEXT, "basic"),
    Material("Репертуар", MType.TEXT, "basic"),
    Material("Хор жоспары", MType.TEXT, "basic"),
    Material("Ата-анаға хат", MType.TEXT, "basic"),
    Material("Викторина", MType.TEXT, "basic"),
    Material("Кросворд", MType.TEXT, "basic"),
    # standard (2)
    Material("Постер", MType.POSTER, "standard"),
    Material("Портфолио", MType.TEXT, "standard"),
    # premium (3)
    Material("Музыка MP3", MType.MUSIC, "premium"),
    Material("Рефлексия", MType.TEXT, "premium"),
    Material("Дифф.тапсырма", MType.TEXT, "premium"),
    # full (3)
    Material("Сценарий", MType.TEXT, "full"),
    Material("Конкурс", MType.TEXT, "full"),
    Material("Флешмоб", MType.TEXT, "full"),
]

BALABAQSHA_MATERIALS = [
    # basic (27)
    Material("Жылдық жоспар", MType.TEXT, "basic"),
    Material("Айлық жоспар", MType.TEXT, "basic"),
    Material("Аптасабақ", MType.TEXT, "basic"),
    Material("Циклограмма", MType.TEXT, "basic"),
    Material("Көрнекілік", MType.TEXT, "basic"),
    Material("Ән сөздері", MType.TEXT, "basic"),
    Material("Би жоспары", MType.TEXT, "basic"),
    Material("Таңғы гимнастика", MType.TEXT, "basic"),
    Material("Логоритмика", MType.TEXT, "basic"),
    Material("Сергіту", MType.TEXT, "basic"),
    Material("Сәлемдесу", MType.TEXT, "basic"),
    Material("Демалыс", MType.TEXT, "basic"),
    Material("Музыкалық ойын", MType.TEXT, "basic"),
    Material("Дидактикалық ойын", MType.TEXT, "basic"),
    Material("Дамытушы ойын", MType.TEXT, "basic"),
    Material("Саусақ ойыны", MType.TEXT, "basic"),
    Material("Аң дыбыстары", MType.TEXT, "basic"),
    Material("Қол соғу", MType.TEXT, "basic"),
    Material("Тыныш-шулы ойыны", MType.TEXT, "basic"),
    Material("Музыкалық орындық", MType.TEXT, "basic"),
    Material("Түс пен дыбыс", MType.TEXT, "basic"),
    Material("Викторина", MType.TEXT, "basic"),
    Material("Ұйқы алдындағы ән", MType.TEXT, "basic"),
    Material("Таңғы ән", MType.TEXT, "basic"),
    Material("Репертуар", MType.TEXT, "basic"),
    Material("Ата-анаға хат", MType.TEXT, "basic"),
    Material("Үй тапсырмасы", MType.TEXT, "basic"),
    # standard (2)
    Material("Постер", MType.POSTER, "standard"),
    Material("Портфолио", MType.TEXT, "standard"),
    # premium (4)
    Material("Музыка MP3", MType.MUSIC, "premium"),
    Material("Музыка терапия", MType.TEXT, "premium"),
    Material("Бейімдеу", MType.TEXT, "premium"),
    Material("Даму картасы", MType.TEXT, "premium"),
    # full (13)
    Material("Сценарий", MType.TEXT, "full"),
    Material("Туған күн", MType.TEXT, "full"),
    Material("Ертегі", MType.TEXT, "full"),
    Material("Музыкалық ертегі", MType.TEXT, "full"),
    Material("Қуыршақ театры", MType.TEXT, "full"),
    Material("Наурыз", MType.TEXT, "full"),
    Material("Жаңа жыл", MType.TEXT, "full"),
    Material("8 Наурыз", MType.TEXT, "full"),
    Material("1 Маусым", MType.TEXT, "full"),
    Material("Бітіру", MType.TEXT, "full"),
    Material("Утренник", MType.TEXT, "full"),
    Material("Ашық есік күні", MType.TEXT, "full"),
    Material("Ата-ана жиналысы", MType.TEXT, "full"),
]

SECTIONS = {
    "mektep": {"label": "🏫 Мектеп", "materials": MEKTEP_MATERIALS},
    "balabaqsha": {"label": "🎪 Балабақша", "materials": BALABAQSHA_MATERIALS},
}

TARIFFS = {
    "free":     {"name": "Тегін",    "price": 0,     "text": 3,    "poster": 0,    "music": 0},
    "basic":    {"name": "Базалық",  "price": 3990,  "text": None, "poster": 0,    "music": 0},
    "standard": {"name": "Стандарт", "price": 5990,  "text": None, "poster": 30,   "music": 0},
    "premium":  {"name": "Премиум",  "price": 10990, "text": None, "poster": 50,   "music": 10},
    "full":     {"name": "Толық",    "price": 14990, "text": None, "poster": None, "music": None},
}

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
USERS_FILE = "users.json"
