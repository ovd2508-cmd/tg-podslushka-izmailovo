import asyncio
import logging
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

import db
import texts
from config import ADMIN_CHAT_ID, BOT_TOKEN, CHANNEL_LINK, MINI_APP_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()


class SuggestionStates(StatesGroup):
    waiting_for_suggestion = State()


class AdminMessageStates(StatesGroup):
    waiting_for_admin_message = State()


MOSCOW_TZ = timezone(timedelta(hours=3))


def msk_now() -> str:
    return datetime.now(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")


def author_text(user) -> str:
    if user.username:
        return f"@{user.username} (ID: {user.id})"
    return f"без username (ID: {user.id})"


async def set_bot_commands() -> None:
    """Настройка команд меню бота (кнопка «Меню» слева от поля ввода)."""
    commands = [
        BotCommand(command="start", description="👋 Главное меню"),
        BotCommand(command="suggest", description="📝 Отправить предложение"),
        BotCommand(command="contact", description="💬 Связаться с админами"),
        BotCommand(command="stats", description="📊 Статистика и рейтинг"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands set")


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню с inline-кнопками и кнопкой WebApp."""
    keyboard_buttons = [
        [
            InlineKeyboardButton(
                text="📝 Отправить предложение",
                callback_data="send_suggestion",
            )
        ],
        [
            InlineKeyboardButton(
                text="💬 Связаться с админами",
                callback_data="contact_admins",
            )
        ],
    ]

    # Кнопка Mini App (если задан URL)
    if MINI_APP_URL:
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="📊 Статистика и рейтинг",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(texts.START_TEXT, reply_markup=get_start_keyboard())
    logger.info("user_id=%s type=start", message.from_user.id)


@dp.message(Command("suggest"))
async def cmd_suggest(message: Message, state: FSMContext):
    """Команда /suggest — сразу переводит в FSM ожидания предложения."""
    await state.set_state(SuggestionStates.waiting_for_suggestion)
    await message.answer(texts.SEND_SUGGESTION_TEXT)
    logger.info("user_id=%s type=command_suggest", message.from_user.id)


@dp.message(Command("contact"))
async def cmd_contact(message: Message, state: FSMContext):
    """Команда /contact — сразу переводит в FSM сообщения админам."""
    await state.set_state(AdminMessageStates.waiting_for_admin_message)
    await message.answer(texts.CONTACT_ADMINS_TEXT)
    logger.info("user_id=%s type=command_contact", message.from_user.id)


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Команда /stats — открывает Mini App."""
    if MINI_APP_URL:
        await message.answer(
            texts.MINI_APP_TEXT,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📊 Открыть статистику",
                            web_app=WebAppInfo(url=MINI_APP_URL),
                        )
                    ]
                ]
            ),
        )
    else:
        await message.answer("Mini App пока не настроен. Обратитесь к администратору.")
    logger.info("user_id=%s type=command_stats", message.from_user.id)


@dp.callback_query(F.data == "send_suggestion")
async def cb_send_suggestion(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SuggestionStates.waiting_for_suggestion)
    await callback.message.answer(texts.SEND_SUGGESTION_TEXT)
    logger.info("user_id=%s type=callback_send_suggestion", callback.from_user.id)


@dp.callback_query(F.data == "contact_admins")
async def cb_contact_admins(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminMessageStates.waiting_for_admin_message)
    await callback.message.answer(texts.CONTACT_ADMINS_TEXT)
    logger.info("user_id=%s type=callback_contact_admins", callback.from_user.id)


@dp.message(SuggestionStates.waiting_for_suggestion)
async def process_suggestion(message: Message, state: FSMContext):
    user_id = message.from_user.id
    content_type = message.content_type
    now_ts = datetime.now(MOSCOW_TZ).timestamp()

    last_sent = await db.get_last_sent_at(user_id)
    if last_sent is not None and now_ts - last_sent < 30:
        await message.answer(texts.FLOOD_TEXT)
        return

    logger.info("user_id=%s type=suggestion content=%s", user_id, content_type)

    # Копируем сообщение пользователя в админ-группу (сохраняем медиа и форматирование)
    await bot.copy_message(
        chat_id=ADMIN_CHAT_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )

    # Отправляем отдельное сообщение с подписью — на него админы будут делать реплаи
    author = author_text(message.from_user)
    caption = texts.ADMIN_SUGGESTION_CAPTION.format(
        author=author,
        time=msk_now(),
    )
    caption_message = await bot.send_message(ADMIN_CHAT_ID, caption)

    # Сохраняем соответствие message_id в админке -> user_id
    await db.save_admin_message(caption_message.message_id, user_id)

    # Обновляем время последней отправки (антифлуд)
    await db.update_cooldown(user_id, now_ts)

    # Инкрементируем счётчик предложений для статистики/топа
    await db.increment_suggestion_count(user_id)

    # Отвечаем пользователю
    await message.answer(
        texts.THANKS_SUGGESTION.format(channel_link=CHANNEL_LINK)
    )

    await state.clear()


@dp.message(AdminMessageStates.waiting_for_admin_message)
async def process_admin_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    content_type = message.content_type
    logger.info("user_id=%s type=admin_message content=%s", user_id, content_type)

    # Копируем сообщение в админ-группу
    await bot.copy_message(
        chat_id=ADMIN_CHAT_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )

    # Отправляем подпись
    author = author_text(message.from_user)
    caption = texts.ADMIN_MESSAGE_CAPTION.format(author=author)
    caption_message = await bot.send_message(ADMIN_CHAT_ID, caption)

    await db.save_admin_message(caption_message.message_id, user_id)

    await message.answer(
        texts.THANKS_ADMIN_MESSAGE.format(channel_link=CHANNEL_LINK)
    )

    await state.clear()


@dp.message(F.chat.id == ADMIN_CHAT_ID)
async def admin_reply_handler(message: Message):
    # Обрабатываем только реплаи на сообщения бота; остальное в админ-чате игнорируем
    if not message.reply_to_message or not message.from_user:
        return

    reply_to_id = message.reply_to_message.message_id
    user_id = await db.get_user_id_by_admin_message(reply_to_id)
    if not user_id:
        return

    # Пересылаем ответ админа пользователю в личку
    if message.content_type == "text":
        await bot.send_message(
            user_id,
            f"{message.text}\n\n📢 {CHANNEL_LINK}",
        )
    else:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await bot.send_message(user_id, f"📢 {CHANNEL_LINK}")

    logger.info(
        "user_id=%s type=admin_reply content=%s", user_id, message.content_type
    )


@dp.message(F.chat.id != ADMIN_CHAT_ID)
async def fallback(message: Message):
    if not message.from_user:
        return
    logger.info(
        "user_id=%s type=fallback content=%s",
        message.from_user.id,
        message.content_type,
    )
    await message.answer(texts.NO_STATE_TEXT)