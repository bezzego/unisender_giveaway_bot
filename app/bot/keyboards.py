from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb_retry_check() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Проверить ещё раз", callback_data="check_again")],
        ]
    )