from __future__ import annotations

import csv
import io
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, BufferedInputFile
from sqlalchemy import delete, select, update

from app.config import settings
from app.db import SessionMaker
from app.models import Participant, PromoCode
from app.repositories.bot_texts import BotTextRepo
from app.repositories.bot_config import BotConfigRepo
from app.repositories.participants import ParticipantRepo
from app.repositories.promo_codes import PromoCodeRepo
from app.services.texts import TextService
from app.bot.keyboards import (
    kb_main,
    kb_admin_main,
    kb_admin_texts,
    kb_admin_promos,
    kb_admin_confirm_clear,
)

log = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_text_key = State()
    waiting_text_value = State()
    waiting_limit = State()
    waiting_promo_list = State()
    confirm_clear_users = State()


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.admin_ids


def parse_codes(raw: str) -> list[str]:
    codes: list[str] = []
    for line in raw.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        if len(parts) == 1:
            code = parts[0]
        else:
            code = "".join(parts)
        codes.append(code)
    return codes


async def route_admin_action(m: Message, state: FSMContext) -> bool:
    text = (m.text or "").strip()
    if text == "↩️ Назад":
        await admin_back(m, state)
        return True
    if text == "Админ панель":
        await admin_start_button(m, state)
        return True
    if text == "📝 Тексты":
        await admin_texts(m, state)
        return True
    if text == "🎟 Промокоды":
        await admin_promos(m, state)
        return True
    if text == "🎯 Лимит":
        await admin_limit(m, state)
        return True
    if text == "👥 Пользователи":
        await admin_users_list(m)
        return True
    if text == "🧹 Очистить пользователей":
        await admin_users_clear(m, state)
        return True
    if text == "📊 Статистика промокодов":
        await admin_promos_stats(m)
        return True
    if text in {"➕ Добавить промокоды", "♻️ Заменить промокоды"}:
        await admin_promos_mode(m, state)
        return True
    return False


@router.message(Command("admin"))
async def admin_start(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        await m.answer("Нет доступа.")
        return
    await state.clear()
    await m.answer("Админ-панель", reply_markup=kb_admin_main())


@router.message(F.text == "Админ панель")
async def admin_start_button(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    await admin_start(m, state)


@router.message(F.text == "↩️ Назад")
async def admin_back(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    await state.clear()
    await m.answer("Главное меню.", reply_markup=kb_main(True))


@router.message(F.text == "📝 Тексты")
async def admin_texts(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    await state.set_state(AdminStates.waiting_text_key)
    await m.answer(
        "Отправьте ключ текста для редактирования. Кнопка ниже покажет список ключей.",
        reply_markup=kb_admin_texts(),
    )


@router.message(F.text == "📋 Список ключей")
async def admin_texts_list(m: Message) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    items = TextService.describe_keys()
    lines = [f"{key} — {desc}" if desc else key for key, desc in items]
    await m.answer("Доступные ключи:\n" + "\n".join(lines), reply_markup=kb_admin_texts())


@router.message(AdminStates.waiting_text_key)
async def admin_text_key(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    if await route_admin_action(m, state):
        return
    key = (m.text or "").strip()
    if key not in TextService.list_keys():
        await m.answer("Неизвестный ключ. Нажмите «Список ключей» и выберите корректный.")
        return
    async with SessionMaker() as session:
        current = await TextService.get_text(session, key)
    await state.update_data(text_key=key)
    await state.set_state(AdminStates.waiting_text_value)
    await m.answer(
        f"Текущий текст для ключа <code>{key}</code>:\n\n{current}\n\nОтправьте новый текст.",
        reply_markup=kb_admin_texts(),
    )


@router.message(AdminStates.waiting_text_value)
async def admin_text_value(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    if await route_admin_action(m, state):
        return
    data = await state.get_data()
    key = data.get("text_key")
    if not key:
        await m.answer("Ключ не найден. Начните заново.")
        await state.set_state(AdminStates.waiting_text_key)
        return
    value = (m.html_text or m.text or "").strip()
    if not value:
        await m.answer("Пустой текст не сохранён. Отправьте новый текст.")
        return
    async with SessionMaker() as session:
        async with session.begin():
            await BotTextRepo.set(session, key, value)
    await m.answer(f"Текст для <code>{key}</code> обновлён.", reply_markup=kb_admin_texts())
    await state.set_state(AdminStates.waiting_text_key)


@router.message(F.text == "🎯 Лимит")
async def admin_limit(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    async with SessionMaker() as session:
        current = await BotConfigRepo.get(session, "cinema_limit")
        current_value = current.value if current else str(settings.cinema_limit)
    await state.set_state(AdminStates.waiting_limit)
    await m.answer(
        f"Текущий лимит: {current_value}\nОтправьте новое число.",
        reply_markup=kb_admin_main(),
    )


@router.message(AdminStates.waiting_limit)
async def admin_limit_value(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    if await route_admin_action(m, state):
        return
    raw = (m.text or "").strip()
    if not raw.isdigit():
        await m.answer("Нужно число. Или нажмите «↩️ Назад».")
        return
    async with SessionMaker() as session:
        async with session.begin():
            await BotConfigRepo.set(session, "cinema_limit", raw)
    await m.answer(f"Лимит обновлён: {raw}")
    await state.clear()


@router.message(F.text == "🎟 Промокоды")
async def admin_promos(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    await state.clear()
    await m.answer("Управление промокодами.", reply_markup=kb_admin_promos())


@router.message(F.text == "📊 Статистика промокодов")
async def admin_promos_stats(m: Message) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    async with SessionMaker() as session:
        stats = await PromoCodeRepo.stats(session, kind="cinema")
    await m.answer(
        f"Промокоды cinema:\n"
        f"Всего: {stats['total']}\n"
        f"Использовано: {stats['used']}\n"
        f"Свободно: {stats['free']}",
        reply_markup=kb_admin_promos(),
    )


@router.message(F.text.in_(["➕ Добавить промокоды", "♻️ Заменить промокоды"]))
async def admin_promos_mode(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    mode = "add" if m.text == "➕ Добавить промокоды" else "replace"
    await state.update_data(promo_mode=mode)
    await state.set_state(AdminStates.waiting_promo_list)
    await m.answer(
        "Отправьте список промокодов (по одному на строку). Формат может быть `80 88151262` или `8088151262`.",
        reply_markup=kb_admin_promos(),
    )


@router.message(AdminStates.waiting_promo_list)
async def admin_promos_list(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    if await route_admin_action(m, state):
        return
    data = await state.get_data()
    mode = data.get("promo_mode", "add")
    codes = parse_codes(m.text or "")
    if not codes:
        await m.answer("Список пуст. Отправьте промокоды ещё раз.")
        return
    inserted = 0
    async with SessionMaker() as session:
        async with session.begin():
            if mode == "replace":
                await session.execute(delete(PromoCode).where(PromoCode.kind == "cinema"))
                existing_codes = set()
            else:
                existing = await session.execute(select(PromoCode.code).where(PromoCode.kind == "cinema"))
                existing_codes = {row[0] for row in existing.fetchall()}
            for code in codes:
                if code in existing_codes:
                    continue
                session.add(PromoCode(kind="cinema", code=code))
                inserted += 1
    await m.answer(
        f"Промокоды обработаны. Добавлено: {inserted} (режим: {mode}).",
        reply_markup=kb_admin_promos(),
    )
    await state.clear()


@router.message(F.text == "👥 Пользователи")
async def admin_users_list(m: Message) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    async with SessionMaker() as session:
        participants = await ParticipantRepo.list_all(session)
    if not participants:
        await m.answer("Пользователей пока нет.", reply_markup=kb_admin_main())
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "telegram_id", "email", "reward_type", "promo_code", "created_at"])
    for p in participants:
        writer.writerow([p.id, p.telegram_id, p.email, p.reward_type, p.promo_code, p.created_at])
    data = BufferedInputFile(output.getvalue().encode("utf-8"), filename="participants.csv")
    await m.answer_document(data, caption="Список пользователей", reply_markup=kb_admin_main())


@router.message(F.text == "🧹 Очистить пользователей")
async def admin_users_clear(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    await state.set_state(AdminStates.confirm_clear_users)
    await m.answer(
        "Это удалит всех пользователей из БД. Подтвердите действие.",
        reply_markup=kb_admin_confirm_clear(),
    )


@router.message(AdminStates.confirm_clear_users, F.text == "✅ Очистить пользователей")
async def admin_users_clear_confirm(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    async with SessionMaker() as session:
        async with session.begin():
            await session.execute(delete(Participant))
    await m.answer("Пользователи удалены.", reply_markup=kb_admin_main())
    await state.clear()


@router.message(AdminStates.confirm_clear_users, F.text == "✅ Очистить пользователей + промокоды")
async def admin_users_clear_confirm_with_promos(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    async with SessionMaker() as session:
        async with session.begin():
            await session.execute(delete(Participant))
            await session.execute(
                update(PromoCode)
                .values(is_used=False, used_by_participant_id=None, used_at=None)
            )
    await m.answer("Пользователи удалены, промокоды сброшены.", reply_markup=kb_admin_main())
    await state.clear()


@router.message(AdminStates.confirm_clear_users)
async def admin_users_clear_cancel(m: Message, state: FSMContext) -> None:
    if not is_admin(m.from_user.id if m.from_user else None):
        return
    if await route_admin_action(m, state):
        return
    await state.clear()
    await m.answer("Отменено.", reply_markup=kb_admin_main())
