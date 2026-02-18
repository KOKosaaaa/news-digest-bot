"""
📰 News Digest Bot
Персональный новостной дайджест с AI-суммаризацией

Запуск: python bot.py
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand,
)
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

from config import (
    BOT_TOKEN, PRESET_TOPICS, LANGUAGE_LEVELS, READING_TIMES,
)
from database import (
    init_db, ensure_user, update_enabled_topics, update_custom_topics,
    update_language_level, update_reading_time, update_digest_lang,
    update_last_viewed, reset_last_viewed,
)
from news_engine import get_news_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

router = Router()

# Состояния для ввода текста (простой вариант без FSM)
waiting_custom_topic: dict[int, bool] = {}


# ===================== КЛАВИАТУРЫ =====================

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📰 Получить новости", callback_data="get_news")],
        [InlineKeyboardButton(text="🔥 Только важное", callback_data="important_news")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
    ])


def settings_kb() -> InlineKeyboardMarkup:
    """Меню настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Темы", callback_data="topics_menu")],
        [InlineKeyboardButton(text="➕ Мои темы", callback_data="custom_topics_menu")],
        [InlineKeyboardButton(text="📖 Уровень языка", callback_data="language_menu")],
        [InlineKeyboardButton(text="⏱ Время чтения", callback_data="reading_time_menu")],
        [InlineKeyboardButton(text="🌐 Язык дайджеста", callback_data="digest_lang_menu")],
        [InlineKeyboardButton(text="🔄 Сбросить историю", callback_data="reset_history")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


def topics_kb(enabled: list, page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    """Клавиатура выбора тем с пагинацией"""
    topic_ids = list(PRESET_TOPICS.keys())
    total_pages = (len(topic_ids) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_topics = topic_ids[start:end]

    buttons = []
    for topic_id in page_topics:
        topic = PRESET_TOPICS[topic_id]
        is_on = topic_id in enabled
        mark = "✅" if is_on else "❌"
        text = f"{mark} {topic['emoji']} {topic['name_ru']}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"toggle_topic:{topic_id}")])

    # Пагинация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"topics_page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"topics_page:{page + 1}"))
    if nav:
        buttons.append(nav)

    # Быстрые действия
    buttons.append([
        InlineKeyboardButton(text="✅ Все", callback_data="topics_all_on"),
        InlineKeyboardButton(text="❌ Сбросить", callback_data="topics_all_off"),
    ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="settings")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def custom_topics_kb(custom_topics: list) -> InlineKeyboardMarkup:
    """Клавиатура кастомных тем"""
    buttons = []

    if custom_topics:
        for i, topic in enumerate(custom_topics):
            buttons.append([
                InlineKeyboardButton(text=f"🏷 {topic}", callback_data="noop"),
                InlineKeyboardButton(text="🗑", callback_data=f"del_custom:{i}"),
            ])
    else:
        buttons.append([InlineKeyboardButton(text="Пока пусто", callback_data="noop")])

    buttons.append([InlineKeyboardButton(text="➕ Добавить тему", callback_data="add_custom_topic")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="settings")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def language_level_kb(current: str) -> InlineKeyboardMarkup:
    """Выбор уровня языка"""
    buttons = []
    for level_id, level in LANGUAGE_LEVELS.items():
        mark = "▸ " if level_id == current else "  "
        text = f"{mark}{level['emoji']} {level['name_ru']}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"set_lang_level:{level_id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def reading_time_kb(current: int) -> InlineKeyboardMarkup:
    """Выбор времени чтения"""
    buttons = []
    for minutes in READING_TIMES:
        mark = "▸ " if minutes == current else "  "
        text = f"{mark}⏱ {minutes} мин"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"set_reading_time:{minutes}")])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def digest_lang_kb(current: str) -> InlineKeyboardMarkup:
    """Выбор языка дайджеста"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'▸ ' if current == 'ru' else '  '}🇷🇺 Русский",
            callback_data="set_digest_lang:ru"
        )],
        [InlineKeyboardButton(
            text=f"{'▸ ' if current == 'en' else '  '}🇬🇧 English",
            callback_data="set_digest_lang:en"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings")],
    ])


def importance_level_kb() -> InlineKeyboardMarkup:
    """Выбор уровня фильтрации важности"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все значимые (10-15)", callback_data="important:low")],
        [InlineKeyboardButton(text="⚡ Только важные (5-7)", callback_data="important:medium")],
        [InlineKeyboardButton(text="🔥 Топ дня (3-5)", callback_data="important:high")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


# ===================== ХЭНДЛЕРЫ =====================

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Команда /start"""
    await ensure_user(message.from_user.id)
    await message.answer(
        "👋 <b>Привет! Я твой персональный новостной бот.</b>\n\n"
        "Я ищу новости по всему интернету, фильтрую воду и "
        "выдаю только проверенные факты в удобном формате.\n\n"
        "Для начала настрой темы в ⚙️ <b>Настройки</b>, "
        "а потом жми 📰 <b>Получить новости</b>!",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Команда /menu"""
    await ensure_user(message.from_user.id)
    await message.answer("📋 <b>Главное меню</b>", reply_markup=main_menu_kb(), parse_mode=ParseMode.HTML)


# --- Главное меню ---

@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 <b>Главное меню</b>",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


# --- Получить новости ---

@router.callback_query(F.data == "get_news")
async def get_news(callback: CallbackQuery):
    user = await ensure_user(callback.from_user.id)
    topics = user["enabled_topics"]
    custom = user["custom_topics"]

    if not topics and not custom:
        await callback.answer("⚠️ Сначала выбери темы в настройках!", show_alert=True)
        return

    # Показываем информацию о последнем просмотре
    last_viewed = user.get("last_viewed_at")
    status_text = "⏳ <b>Собираю новости...</b>\n\n"
    if last_viewed:
        status_text += f"📅 Последний просмотр: {last_viewed}\n🔍 Ищу только свежие новости!\n\n"
    status_text += "Это займёт 30-60 секунд."

    await callback.message.edit_text(status_text, parse_mode=ParseMode.HTML)

    try:
        digest = await get_news_digest(
            enabled_topics=topics,
            custom_topics=custom,
            language_level=user["language_level"],
            reading_time=user["reading_time"],
            digest_lang=user["digest_lang"],
            last_viewed_at=last_viewed,
        )

        # Обновляем время последнего просмотра
        await update_last_viewed(callback.from_user.id)

        # Telegram ограничивает сообщения 4096 символами — разбиваем если нужно
        await send_long_message(callback.message, digest)
    except Exception as e:
        logger.error(f"Ошибка получения новостей: {e}")
        await callback.message.edit_text(f"❌ Произошла ошибка: {e}")


# --- Только важное ---

@router.callback_query(F.data == "important_news")
async def important_news(callback: CallbackQuery):
    user = await ensure_user(callback.from_user.id)
    topics = user["enabled_topics"]
    custom = user["custom_topics"]

    if not topics and not custom:
        await callback.answer("⚠️ Сначала выбери темы в настройках!", show_alert=True)
        return

    await callback.message.edit_text(
        "🔥 <b>Только важное</b>\n\nВыбери уровень фильтрации:",
        reply_markup=importance_level_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("important:"))
async def important_with_level(callback: CallbackQuery):
    level = callback.data.split(":")[1]
    user = await ensure_user(callback.from_user.id)
    last_viewed = user.get("last_viewed_at")

    status_text = "⏳ <b>Ищу самое важное...</b>\n\n"
    if last_viewed:
        status_text += f"📅 Последний просмотр: {last_viewed}\n"
    status_text += "Фильтрую шум, оставляю только главное."

    await callback.message.edit_text(status_text, parse_mode=ParseMode.HTML)

    try:
        digest = await get_news_digest(
            enabled_topics=user["enabled_topics"],
            custom_topics=user["custom_topics"],
            language_level=user["language_level"],
            reading_time=user["reading_time"],
            digest_lang=user["digest_lang"],
            important_only=True,
            importance_level=level,
            last_viewed_at=last_viewed,
        )

        # Обновляем время последнего просмотра
        await update_last_viewed(callback.from_user.id)

        await send_long_message(callback.message, digest)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {e}")


# --- Настройки ---

@router.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery):
    user = await ensure_user(callback.from_user.id)
    topics_count = len(user["enabled_topics"]) + len(user["custom_topics"])
    level_name = LANGUAGE_LEVELS.get(user["language_level"], {}).get("name_ru", "?")

    text = (
        f"⚙️ <b>Настройки</b>\n\n"
        f"📋 Тем выбрано: <b>{topics_count}</b>\n"
        f"📖 Язык: <b>{level_name}</b>\n"
        f"⏱ Чтение: <b>{user['reading_time']} мин</b>\n"
        f"🌐 Дайджест: <b>{'Русский' if user['digest_lang'] == 'ru' else 'English'}</b>"
    )

    await callback.message.edit_text(text, reply_markup=settings_kb(), parse_mode=ParseMode.HTML)


# --- Темы ---

@router.callback_query(F.data == "topics_menu")
async def topics_menu(callback: CallbackQuery):
    user = await ensure_user(callback.from_user.id)
    await callback.message.edit_text(
        "📋 <b>Выбери интересные темы</b>\n\n✅ — включена, ❌ — выключена",
        reply_markup=topics_kb(user["enabled_topics"]),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("topics_page:"))
async def topics_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    user = await ensure_user(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=topics_kb(user["enabled_topics"], page))


@router.callback_query(F.data.startswith("toggle_topic:"))
async def toggle_topic(callback: CallbackQuery):
    topic_id = callback.data.split(":")[1]
    user = await ensure_user(callback.from_user.id)
    topics = user["enabled_topics"]

    if topic_id in topics:
        topics.remove(topic_id)
    else:
        topics.append(topic_id)

    await update_enabled_topics(callback.from_user.id, topics)

    # Определяем текущую страницу
    all_ids = list(PRESET_TOPICS.keys())
    idx = all_ids.index(topic_id) if topic_id in all_ids else 0
    page = idx // 8

    await callback.message.edit_reply_markup(reply_markup=topics_kb(topics, page))
    await callback.answer()


@router.callback_query(F.data == "topics_all_on")
async def topics_all_on(callback: CallbackQuery):
    all_topics = list(PRESET_TOPICS.keys())
    await update_enabled_topics(callback.from_user.id, all_topics)
    await callback.message.edit_reply_markup(reply_markup=topics_kb(all_topics))
    await callback.answer("✅ Все темы включены")


@router.callback_query(F.data == "topics_all_off")
async def topics_all_off(callback: CallbackQuery):
    await update_enabled_topics(callback.from_user.id, [])
    await callback.message.edit_reply_markup(reply_markup=topics_kb([]))
    await callback.answer("❌ Все темы сброшены")


# --- Кастомные темы ---

@router.callback_query(F.data == "custom_topics_menu")
async def custom_topics_menu(callback: CallbackQuery):
    user = await ensure_user(callback.from_user.id)
    await callback.message.edit_text(
        "🏷 <b>Мои темы</b>\n\nДобавляй свои темы для поиска новостей:",
        reply_markup=custom_topics_kb(user["custom_topics"]),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "add_custom_topic")
async def add_custom_topic_prompt(callback: CallbackQuery):
    waiting_custom_topic[callback.from_user.id] = True
    await callback.message.edit_text(
        "✏️ <b>Напиши тему</b>\n\n"
        "Например: <i>Flipper Zero</i>, <i>эмиграция в Германию</i>, <i>Unreal Engine</i>\n\n"
        "Отправь /cancel для отмены.",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("cancel"))
async def cancel_input(message: Message):
    if message.from_user.id in waiting_custom_topic:
        del waiting_custom_topic[message.from_user.id]
    await message.answer("❌ Отменено", reply_markup=main_menu_kb())


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_input(message: Message):
    """Обработка текстового ввода (для добавления кастомных тем)"""
    user_id = message.from_user.id

    if user_id not in waiting_custom_topic:
        # Если пользователь просто пишет текст — показываем меню
        await message.answer("Используй кнопки меню 👇", reply_markup=main_menu_kb())
        return

    del waiting_custom_topic[user_id]
    topic_text = message.text.strip()

    if len(topic_text) > 100:
        await message.answer("⚠️ Слишком длинное название. Максимум 100 символов.")
        return

    user = await ensure_user(user_id)
    custom = user["custom_topics"]

    if len(custom) >= 20:
        await message.answer("⚠️ Максимум 20 кастомных тем. Удали что-нибудь.")
        return

    if topic_text.lower() in [t.lower() for t in custom]:
        await message.answer("⚠️ Такая тема уже есть!")
        return

    custom.append(topic_text)
    await update_custom_topics(user_id, custom)
    await message.answer(
        f"✅ Тема <b>«{topic_text}»</b> добавлена!",
        reply_markup=custom_topics_kb(custom),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("del_custom:"))
async def delete_custom_topic(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    user = await ensure_user(callback.from_user.id)
    custom = user["custom_topics"]

    if 0 <= idx < len(custom):
        removed = custom.pop(idx)
        await update_custom_topics(callback.from_user.id, custom)
        await callback.answer(f"🗑 «{removed}» удалена")

    await callback.message.edit_reply_markup(reply_markup=custom_topics_kb(custom))


# --- Уровень языка ---

@router.callback_query(F.data == "language_menu")
async def language_menu(callback: CallbackQuery):
    user = await ensure_user(callback.from_user.id)
    await callback.message.edit_text(
        "📖 <b>Уровень сложности языка</b>\n\n"
        "😊 Простой — как другу объясняешь\n"
        "📝 Средний — обычный новостной стиль\n"
        "📊 Продвинутый — терминология и детали\n"
        "🎯 Экспертный — цифры, факты, без упрощений",
        reply_markup=language_level_kb(user["language_level"]),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("set_lang_level:"))
async def set_language_level(callback: CallbackQuery):
    level = callback.data.split(":")[1]
    await update_language_level(callback.from_user.id, level)
    user = await ensure_user(callback.from_user.id)
    level_name = LANGUAGE_LEVELS[level]["name_ru"]
    await callback.answer(f"✅ Уровень: {level_name}")
    await callback.message.edit_reply_markup(reply_markup=language_level_kb(level))


# --- Время чтения ---

@router.callback_query(F.data == "reading_time_menu")
async def reading_time_menu(callback: CallbackQuery):
    user = await ensure_user(callback.from_user.id)
    await callback.message.edit_text(
        "⏱ <b>Время чтения дайджеста</b>\n\nВыбери сколько минут ты готов потратить:",
        reply_markup=reading_time_kb(user["reading_time"]),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("set_reading_time:"))
async def set_reading_time(callback: CallbackQuery):
    minutes = int(callback.data.split(":")[1])
    await update_reading_time(callback.from_user.id, minutes)
    await callback.answer(f"✅ Время чтения: {minutes} мин")
    await callback.message.edit_reply_markup(reply_markup=reading_time_kb(minutes))


# --- Язык дайджеста ---

@router.callback_query(F.data == "digest_lang_menu")
async def digest_lang_menu(callback: CallbackQuery):
    user = await ensure_user(callback.from_user.id)
    await callback.message.edit_text(
        "🌐 <b>Язык дайджеста</b>",
        reply_markup=digest_lang_kb(user["digest_lang"]),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("set_digest_lang:"))
async def set_digest_lang(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    await update_digest_lang(callback.from_user.id, lang)
    await callback.answer(f"✅ Язык: {'Русский' if lang == 'ru' else 'English'}")
    await callback.message.edit_reply_markup(reply_markup=digest_lang_kb(lang))


# --- Сброс истории ---

@router.callback_query(F.data == "reset_history")
async def reset_history(callback: CallbackQuery):
    await reset_last_viewed(callback.from_user.id)
    await callback.answer("✅ История сброшена! Теперь получишь все новости.", show_alert=True)


# --- Утилита для noop кнопок ---

@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


# ===================== УТИЛИТЫ =====================

async def send_long_message(message: Message, text: str):
    """Отправка длинного сообщения с разбивкой"""
    # Удаляем сообщение "ожидание"
    try:
        await message.delete()
    except Exception:
        pass

    max_len = 4096
    if len(text) <= max_len:
        try:
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb())
        except Exception:
            # Если HTML невалидный — отправляем без форматирования
            await message.answer(text, reply_markup=main_menu_kb())
        return

    # Разбиваем по абзацам
    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            parts.append(current)
            current = line
        else:
            current += ("\n" if current else "") + line
    if current:
        parts.append(current)

    for i, part in enumerate(parts):
        try:
            if i == len(parts) - 1:
                await message.answer(part, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb())
            else:
                await message.answer(part, parse_mode=ParseMode.HTML)
        except Exception:
            if i == len(parts) - 1:
                await message.answer(part, reply_markup=main_menu_kb())
            else:
                await message.answer(part)
        await asyncio.sleep(0.3)


# ===================== ЗАПУСК =====================

async def main():
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Устанавливаем команды
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="cancel", description="Отмена ввода"),
    ])

    logger.info("🚀 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
