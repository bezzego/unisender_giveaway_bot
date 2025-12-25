from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def kb_retry_check() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Проверить ещё раз", callback_data="check_again")],
        ]
    )


def kb_main(is_admin: bool) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    if not is_admin:
        return ReplyKeyboardRemove()
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Админ панель")],
        ],
        resize_keyboard=True,
        selective=True,
    )


def kb_admin_main() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Тексты"), KeyboardButton(text="🎟 Промокоды")],
            [KeyboardButton(text="🎯 Лимит"), KeyboardButton(text="👥 Пользователи")],
            [KeyboardButton(text="🧹 Очистить пользователей")],
            [KeyboardButton(text="↩️ Назад")],
        ],
        resize_keyboard=True,
        selective=True,
    )


def kb_admin_texts() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Список ключей")],
            [KeyboardButton(text="↩️ Назад")],
        ],
        resize_keyboard=True,
        selective=True,
    )


def kb_admin_promos() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить промокоды"), KeyboardButton(text="♻️ Заменить промокоды")],
            [KeyboardButton(text="📊 Статистика промокодов")],
            [KeyboardButton(text="↩️ Назад")],
        ],
        resize_keyboard=True,
        selective=True,
    )


def kb_admin_confirm_clear() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Очистить пользователей")],
            [KeyboardButton(text="✅ Очистить пользователей + промокоды")],
            [KeyboardButton(text="↩️ Назад")],
        ],
        resize_keyboard=True,
        selective=True,
    )


def kb_remove() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
