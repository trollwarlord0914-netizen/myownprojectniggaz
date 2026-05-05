"""
keyboards.py – All inline keyboard builders for the GIF bot.

Button callback_data format:
  "action:value"
  e.g.  "pos:tl"  |  "font:Vazir"  |  "color:red"  |  "filter:bw"
        "speed:x2" | "toggle:reverse" | "toggle:mirror" | "toggle:wide"
        "notext"   | "process"        | "cancel"
        "menu:pos" | "menu:font" | "menu:color" | "menu:filter" | "menu:adv"
        "back"
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ── helpers ─────────────────────────────────────────────────────────────────

def _check(active: bool) -> str:
    return "✅" if active else "❌"


# ── Main menu ────────────────────────────────────────────────────────────────

def main_menu_keyboard(state: dict) -> InlineKeyboardMarkup:
    """
    Main editing menu.

    state keys used:
        font        str   current font name
        color       str   current color key
        filter      str   "normal" | "bw" | "negative"
        reverse     bool
        mirror      bool
        speed       str   "x0.5" | "x1" | "x2" | "x4"
        wide        bool
        has_text    bool  whether text was provided
    """
    font = state.get("font", "IRANSans")
    color_icon = _color_icon(state.get("color", "white"))
    filter_icon = _filter_icon(state.get("filter", "normal"))

    builder = InlineKeyboardBuilder()

    if state.get("has_text"):
        builder.row(
            InlineKeyboardButton(text=f"جای متن <= ⊥", callback_data="menu:pos"),
            InlineKeyboardButton(text=f"رنگ متن <= {color_icon}", callback_data="menu:color"),
        )
        builder.row(
            InlineKeyboardButton(text=f"فیلتر گیف <= {filter_icon}", callback_data="menu:filter"),
        )
        builder.row(
            InlineKeyboardButton(text=f"{font}", callback_data="menu:font"),
            InlineKeyboardButton(text="تنظیمات دیگر", callback_data="menu:adv"),
        )
        builder.row(
            InlineKeyboardButton(text="لغو", callback_data="cancel"),
            InlineKeyboardButton(text="بدون متن 🚫", callback_data="notext"),
        )
    else:
        # No-text path: hide text-specific items
        builder.row(
            InlineKeyboardButton(text=f"فیلتر گیف <= {filter_icon}", callback_data="menu:filter"),
        )
        builder.row(
            InlineKeyboardButton(text="تنظیمات دیگر", callback_data="menu:adv"),
        )
        builder.row(
            InlineKeyboardButton(text="لغو", callback_data="cancel"),
        )

    builder.row(
        InlineKeyboardButton(text="🎬 ساخت گیف", callback_data="process"),
    )

    return builder.as_markup()


# ── Sub-menu: Text Position ──────────────────────────────────────────────────

_POS_ICONS = {
    "tl": "⌜", "tc": "⊤", "tr": "⌝",
    "ml": "⊣", "mc": "⊕", "mr": "⊢",
    "bl": "⌞", "bc": "⊥", "br": "⌟",
}

def position_keyboard(current_pos: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    positions = [
        ("tl", "tc", "tr"),
        ("ml", "mc", "mr"),
        ("bl", "bc", "br"),
    ]
    for row in positions:
        buttons = []
        for pos in row:
            icon = _POS_ICONS[pos]
            mark = "●" if pos == current_pos else ""
            buttons.append(
                InlineKeyboardButton(
                    text=f"{mark}{icon}{mark}",
                    callback_data=f"pos:{pos}",
                )
            )
        builder.row(*buttons)

    builder.row(
        InlineKeyboardButton(text="لغو", callback_data="cancel"),
        InlineKeyboardButton(text="برگشت", callback_data="back"),
    )
    return builder.as_markup()


# ── Sub-menu: Font ───────────────────────────────────────────────────────────

def font_keyboard(current_font: str) -> InlineKeyboardMarkup:
    fonts = ["IRANSans", "aviny", "ZahraRoosta", "Vazir"]
    builder = InlineKeyboardBuilder()
    for f in fonts:
        mark = "✅ " if f == current_font else ""
        builder.row(InlineKeyboardButton(text=f"{mark}{f}", callback_data=f"font:{f}"))
    builder.row(
        InlineKeyboardButton(text="لغو", callback_data="cancel"),
        InlineKeyboardButton(text="برگشت", callback_data="back"),
    )
    return builder.as_markup()


# ── Sub-menu: Text Color ─────────────────────────────────────────────────────

_COLOR_BUTTONS = [
    ("⬜", "white"),
    ("⬛", "black"),
    ("🟥", "red"),
    ("🟦", "blue"),
    ("🌈", "rainbow"),  # special: cycling rainbow (treated as white with outline)
]

def _color_icon(color_key: str) -> str:
    mapping = {
        "white": "⬜", "black": "⬛",
        "red": "🟥", "blue": "🟦", "rainbow": "🌈",
    }
    return mapping.get(color_key, "⬜")

def color_keyboard(current_color: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    row1 = []
    row2 = []
    for i, (icon, key) in enumerate(_COLOR_BUTTONS):
        mark = "✅" if key == current_color else ""
        btn = InlineKeyboardButton(
            text=f"{mark}{icon}",
            callback_data=f"color:{key}",
        )
        if i < 2:
            row1.append(btn)
        elif i < 4:
            row2.append(btn)
        else:
            builder.row(btn)  # rainbow alone
    builder.row(*row1)
    builder.row(*row2)
    builder.row(
        InlineKeyboardButton(text="لغو", callback_data="cancel"),
        InlineKeyboardButton(text="برگشت", callback_data="back"),
    )
    return builder.as_markup()


# ── Sub-menu: GIF Filter ─────────────────────────────────────────────────────

def _filter_icon(filter_key: str) -> str:
    return {"normal": "🌈", "bw": "♟", "negative": "🔄"}.get(filter_key, "🌈")

def filter_keyboard(current_filter: str) -> InlineKeyboardMarkup:
    filters = [
        ("🌈", "normal",   "عادی"),
        ("♟", "bw",       "سیاه سفید"),
        ("🔄", "negative", "نگاتیو"),
    ]
    builder = InlineKeyboardBuilder()
    row = []
    for icon, key, _ in filters:
        mark = "✅" if key == current_filter else ""
        row.append(
            InlineKeyboardButton(
                text=f"{mark}{icon}",
                callback_data=f"filter:{key}",
            )
        )
    builder.row(*row)
    builder.row(
        InlineKeyboardButton(text="لغو", callback_data="cancel"),
        InlineKeyboardButton(text="برگشت", callback_data="back"),
    )
    return builder.as_markup()


# ── Sub-menu: Advanced Settings ───────────────────────────────────────────────

def advanced_keyboard(state: dict) -> InlineKeyboardMarkup:
    reverse = state.get("reverse", False)
    mirror  = state.get("mirror", False)
    speed   = state.get("speed", "x1")
    wide    = state.get("wide", False)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"معکوس <= {_check(reverse)} 🔄",
            callback_data="toggle:reverse",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"آینه <= {_check(mirror)} 🪞",
            callback_data="toggle:mirror",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"سرعت <= {speed}",
            callback_data="menu:speed",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"wide <= {_check(wide)}",
            callback_data="toggle:wide",
        )
    )
    builder.row(
        InlineKeyboardButton(text="لغو", callback_data="cancel"),
        InlineKeyboardButton(text="برگشت", callback_data="back"),
    )
    return builder.as_markup()


# ── Sub-menu: Speed ───────────────────────────────────────────────────────────

def speed_keyboard(current_speed: str) -> InlineKeyboardMarkup:
    speeds = ["x0.5", "x1", "x2", "x4"]
    builder = InlineKeyboardBuilder()
    row1 = []
    row2 = []
    for i, s in enumerate(speeds):
        mark = "✅ " if s == current_speed else ""
        btn = InlineKeyboardButton(text=f"{mark}{s}", callback_data=f"speed:{s}")
        if i < 2:
            row1.append(btn)
        else:
            row2.append(btn)
    builder.row(*row1)
    builder.row(*row2)
    builder.row(
        InlineKeyboardButton(text="لغو", callback_data="cancel"),
        InlineKeyboardButton(text="برگشت", callback_data="back"),
    )
    return builder.as_markup()
