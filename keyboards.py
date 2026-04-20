from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import SECTIONS, PAGE_SIZE, TARIFFS


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏫 Мектеп", callback_data="section:mektep")],
        [InlineKeyboardButton("🎪 Балабақша", callback_data="section:balabaqsha")],
        [InlineKeyboardButton("💰 Тариф", callback_data="tarif")],
    ])


def material_list_kb(section: str, page: int) -> InlineKeyboardMarkup:
    materials = SECTIONS[section]["materials"]
    total = len(materials)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    rows = []
    for idx in range(start, end):
        rows.append([InlineKeyboardButton(
            f"{idx + 1}. {materials[idx]}",
            callback_data=f"material:{section}:{idx}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Алдыңғы", callback_data=f"page:{section}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Келесі ▶️", callback_data=f"page:{section}:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🏠 Басты мәзір", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def back_to_list_kb(section: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Бас тарту", callback_data=f"page:{section}:{page}")],
        [InlineKeyboardButton("🏠 Басты мәзір", callback_data="main_menu")],
    ])


def tarif_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Басты мәзір", callback_data="main_menu")],
    ])
