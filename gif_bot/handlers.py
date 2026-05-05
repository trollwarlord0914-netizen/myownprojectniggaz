"""
handlers.py – All aiogram 3.x message and callback-query handlers.

FSM flow
--------
Private chat
  [any state] GIF received
      → download GIF → store file_path in FSM data
      → ask for text  (state = waiting_for_text)

  waiting_for_text: text message received
      → store text → show main menu  (state = configuring)

  waiting_for_text: /notext or button "بدون متن"
      → store text=None → show main menu

  configuring: inline button callbacks
      → update state dict → refresh keyboard

  configuring: "process" button
      → run FFmpeg → send animation → clear state

Group chat
  /gif command (must be a reply to a GIF)
      → download GIF → ask for text (same flow)
"""

import os
import logging
import uuid

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart

from states import GifStates
from keyboards import (
    main_menu_keyboard,
    position_keyboard,
    font_keyboard,
    color_keyboard,
    filter_keyboard,
    advanced_keyboard,
    speed_keyboard,
)
from ffmpeg_utils import process_gif, cleanup
from config import TEMP_DIR, MAX_FILE_SIZE

logger = logging.getLogger(__name__)
router = Router()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _default_state_data() -> dict:
    return {
        "file_path":  None,
        "text":       None,
        "has_text":   False,
        "position":   "bc",
        "font":       "IRANSans",
        "color":      "white",
        "filter":     "normal",
        "speed":      "x1",
        "reverse":    False,
        "mirror":     False,
        "wide":       False,
        # track which sub-menu we're in so "back" works
        "current_menu": "main",
    }


async def _download_gif(bot: Bot, file_id: str) -> str | None:
    """Download a Telegram animation/document and return local path."""
    try:
        file = await bot.get_file(file_id)
        if file.file_size and file.file_size > MAX_FILE_SIZE:
            return None
        local_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.mp4")
        await bot.download_file(file.file_path, destination=local_path)
        return local_path
    except Exception as exc:
        logger.error("Download error: %s", exc)
        return None


async def _show_main_menu(message_or_query, state: FSMContext, bot: Bot):
    """Send (or edit) the main configuration menu."""
    data = await state.get_data()
    keyboard = main_menu_keyboard(data)
    text = "متنو بگو" if data.get("has_text") else "متتنو بگو"

    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.edit_text(text, reply_markup=keyboard)
    else:
        await message_or_query.answer(text, reply_markup=keyboard)

    await state.set_state(GifStates.configuring)
    await state.update_data(current_menu="main")


# ── /start ────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "گیف بده بعدشم متن\nتوی گروه ها هم میتونی ادم کنی"
    )
    await state.set_state(GifStates.waiting_for_gif)


# ── /cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    data = await state.get_data()
    cleanup(data.get("file_path"))
    await state.clear()
    await message.answer("کنسل شد ✅")


# ── /gif (group command: reply to a GIF) ─────────────────────────────────────

@router.message(Command("gif"))
async def cmd_gif(message: Message, state: FSMContext, bot: Bot):
    # Must be a reply to a message that contains an animation
    if not message.reply_to_message:
        await message.reply("روی گیف ریپلی کن")
        return

    replied = message.reply_to_message
    animation = replied.animation or (
        replied.document if replied.document and
        replied.document.mime_type == "video/mp4" else None
    )
    if not animation:
        await message.reply("روی گیف ریپلی کن")
        return

    processing_msg = await message.reply("⏳ در حال دانلود...")
    local_path = await _download_gif(bot, animation.file_id)
    await processing_msg.delete()

    if not local_path:
        await message.reply("❌ فایل خیلی بزرگه یا خطا در دانلود.")
        return

    data = _default_state_data()
    data["file_path"] = local_path
    await state.set_data(data)
    await state.set_state(GifStates.waiting_for_text)

    await message.reply(
        "متتنو بگو",
        reply_markup=main_menu_keyboard({**data, "has_text": True}),
    )


# ── Receive GIF in private chat ───────────────────────────────────────────────

@router.message(
    GifStates.waiting_for_gif,
    F.animation | (F.document & F.document.mime_type == "video/mp4"),
)
async def receive_gif(message: Message, state: FSMContext, bot: Bot):
    anim = message.animation or message.document
    processing_msg = await message.answer("⏳ در حال دانلود...")
    local_path = await _download_gif(bot, anim.file_id)
    await processing_msg.delete()

    if not local_path:
        await message.answer("❌ فایل خیلی بزرگه (حداکثر 20MB) یا خطا در دانلود.")
        return

    data = _default_state_data()
    data["file_path"] = local_path
    await state.set_data(data)
    await state.set_state(GifStates.waiting_for_text)

    await message.answer("متتنو بگو")


# ── Also accept GIFs in waiting_for_text (user sends a new GIF) ───────────────

@router.message(
    GifStates.waiting_for_text,
    F.animation | (F.document & F.document.mime_type == "video/mp4"),
)
async def replace_gif(message: Message, state: FSMContext, bot: Bot):
    """User sent another GIF while we were waiting for text – replace it."""
    old_data = await state.get_data()
    cleanup(old_data.get("file_path"))

    anim = message.animation or message.document
    processing_msg = await message.answer("⏳ در حال دانلود...")
    local_path = await _download_gif(bot, anim.file_id)
    await processing_msg.delete()

    if not local_path:
        await message.answer("❌ خطا در دانلود فایل جدید.")
        return

    data = _default_state_data()
    data["file_path"] = local_path
    await state.set_data(data)
    await message.answer("متتنو بگو")


# ── Receive text ──────────────────────────────────────────────────────────────

@router.message(GifStates.waiting_for_text, F.text)
async def receive_text(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(text=text, has_text=True)
    data = await state.get_data()
    await state.set_state(GifStates.configuring)
    await message.answer("متتنو بگو", reply_markup=main_menu_keyboard(data))


# ── Callback: "بدون متن" (no text) ───────────────────────────────────────────

@router.callback_query(GifStates.configuring, F.data == "notext")
@router.callback_query(GifStates.waiting_for_text, F.data == "notext")
async def cb_notext(query: CallbackQuery, state: FSMContext):
    await state.update_data(text=None, has_text=False)
    data = await state.get_data()
    await state.set_state(GifStates.configuring)
    await query.message.edit_text(
        "بدون متن 🚫 – تنظیمات را انتخاب کن:",
        reply_markup=main_menu_keyboard(data),
    )
    await query.answer()


# ── Callback: Cancel ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel")
async def cb_cancel(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cleanup(data.get("file_path"))
    await state.clear()
    await query.message.edit_text("کنسل شد ✅")
    await query.answer()


# ── Callback: Back to main menu ───────────────────────────────────────────────

@router.callback_query(GifStates.configuring, F.data == "back")
async def cb_back(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(current_menu="main")
    await query.message.edit_text(
        "متتنو بگو" if data.get("has_text") else "تنظیمات:",
        reply_markup=main_menu_keyboard(data),
    )
    await query.answer()


# ── Callback: Open sub-menus ──────────────────────────────────────────────────

@router.callback_query(GifStates.configuring, F.data == "menu:pos")
async def cb_menu_pos(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(current_menu="pos")
    await query.message.edit_text("جای متن", reply_markup=position_keyboard(data.get("position", "bc")))
    await query.answer()


@router.callback_query(GifStates.configuring, F.data == "menu:font")
async def cb_menu_font(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(current_menu="font")
    await query.message.edit_text("فونت", reply_markup=font_keyboard(data.get("font", "IRANSans")))
    await query.answer()


@router.callback_query(GifStates.configuring, F.data == "menu:color")
async def cb_menu_color(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(current_menu="color")
    await query.message.edit_text("رنگ متن", reply_markup=color_keyboard(data.get("color", "white")))
    await query.answer()


@router.callback_query(GifStates.configuring, F.data == "menu:filter")
async def cb_menu_filter(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(current_menu="filter")

    filter_labels = {
        "normal":   "🌈 <= عادی",
        "bw":       "♟ <= سیاه سفید",
        "negative": "🔄 <= نگاتیو",
    }
    label_text = "\n".join(
        f"{'✅' if k == data.get('filter','normal') else ''} {v}"
        for k, v in filter_labels.items()
    )
    await query.message.edit_text(
        f"فیلتر گیف\n{label_text}",
        reply_markup=filter_keyboard(data.get("filter", "normal")),
    )
    await query.answer()


@router.callback_query(GifStates.configuring, F.data == "menu:adv")
async def cb_menu_adv(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(current_menu="adv")
    await query.message.edit_text("تنظیمات دیگر", reply_markup=advanced_keyboard(data))
    await query.answer()


@router.callback_query(GifStates.configuring, F.data == "menu:speed")
async def cb_menu_speed(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(current_menu="speed")
    await query.message.edit_text("سرعت", reply_markup=speed_keyboard(data.get("speed", "x1")))
    await query.answer()


# ── Callback: Set position ────────────────────────────────────────────────────

@router.callback_query(GifStates.configuring, F.data.startswith("pos:"))
async def cb_set_position(query: CallbackQuery, state: FSMContext):
    pos = query.data.split(":")[1]
    await state.update_data(position=pos)
    data = await state.get_data()
    await query.message.edit_reply_markup(reply_markup=position_keyboard(pos))
    await query.answer(f"✅ جای متن: {pos}")


# ── Callback: Set font ────────────────────────────────────────────────────────

@router.callback_query(GifStates.configuring, F.data.startswith("font:"))
async def cb_set_font(query: CallbackQuery, state: FSMContext):
    font = query.data.split(":")[1]
    await state.update_data(font=font)
    await query.message.edit_reply_markup(reply_markup=font_keyboard(font))
    await query.answer(f"✅ فونت: {font}")


# ── Callback: Set color ───────────────────────────────────────────────────────

@router.callback_query(GifStates.configuring, F.data.startswith("color:"))
async def cb_set_color(query: CallbackQuery, state: FSMContext):
    color = query.data.split(":")[1]
    await state.update_data(color=color)
    await query.message.edit_reply_markup(reply_markup=color_keyboard(color))
    await query.answer(f"✅ رنگ: {color}")


# ── Callback: Set filter ──────────────────────────────────────────────────────

@router.callback_query(GifStates.configuring, F.data.startswith("filter:"))
async def cb_set_filter(query: CallbackQuery, state: FSMContext):
    fil = query.data.split(":")[1]
    await state.update_data(filter=fil)
    await query.message.edit_reply_markup(reply_markup=filter_keyboard(fil))
    await query.answer(f"✅ فیلتر: {fil}")


# ── Callback: Set speed ───────────────────────────────────────────────────────

@router.callback_query(GifStates.configuring, F.data.startswith("speed:"))
async def cb_set_speed(query: CallbackQuery, state: FSMContext):
    speed = query.data.split(":")[1]
    await state.update_data(speed=speed)
    await query.message.edit_reply_markup(reply_markup=speed_keyboard(speed))
    await query.answer(f"✅ سرعت: {speed}")


# ── Callback: Toggle (reverse / mirror / wide) ────────────────────────────────

@router.callback_query(GifStates.configuring, F.data.startswith("toggle:"))
async def cb_toggle(query: CallbackQuery, state: FSMContext):
    key = query.data.split(":")[1]       # "reverse" | "mirror" | "wide"
    data = await state.get_data()
    new_val = not data.get(key, False)
    await state.update_data(**{key: new_val})
    data = await state.get_data()
    await query.message.edit_reply_markup(reply_markup=advanced_keyboard(data))
    status = "✅" if new_val else "❌"
    await query.answer(f"{status} {key}")


# ── Callback: Process GIF ─────────────────────────────────────────────────────

@router.callback_query(GifStates.configuring, F.data == "process")
async def cb_process(query: CallbackQuery, state: FSMContext, bot: Bot):
    await query.answer("⏳ در حال پردازش...")
    data = await state.get_data()

    input_path = data.get("file_path")
    if not input_path or not os.path.exists(input_path):
        await query.message.edit_text("❌ فایل پیدا نشد. لطفاً دوباره گیف بفرست.")
        await state.clear()
        return

    processing_msg = await query.message.edit_text("⏳ در حال پردازش گیف...")

    output_path = None
    try:
        output_path = await process_gif(input_path, data)

        caption = data.get("text") or ""
        await bot.send_animation(
            chat_id=query.message.chat.id,
            animation=FSInputFile(output_path),
            caption=caption,
        )
        await processing_msg.delete()

    except RuntimeError as exc:
        logger.error("Processing error: %s", exc)
        await processing_msg.edit_text(f"❌ خطا در پردازش:\n{exc}")

    except Exception as exc:
        logger.exception("Unexpected error during processing: %s", exc)
        await processing_msg.edit_text("❌ خطای ناشناخته. لطفاً دوباره تلاش کن.")

    finally:
        cleanup(input_path, output_path)
        await state.clear()
        await state.set_state(GifStates.waiting_for_gif)


# ── Fallback: non-GIF message while waiting for GIF ──────────────────────────

@router.message(GifStates.waiting_for_gif)
async def fallback_waiting_gif(message: Message):
    await message.answer("لطفاً یک GIF بفرست.")


# ── Fallback: unknown callback ────────────────────────────────────────────────

@router.callback_query()
async def fallback_callback(query: CallbackQuery):
    await query.answer("❓ دکمه نامعتبر")
