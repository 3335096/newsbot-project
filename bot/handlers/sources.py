from __future__ import annotations

from aiogram import F, Router, types
from aiogram.types import CallbackQuery
import httpx

from core.config import settings

router = Router()


def _is_allowed_user(user_id: int) -> bool:
    return user_id in settings.allowed_user_ids


def _source_text(source: dict) -> str:
    return (
        f"Источник #{source['id']}\n"
        f"Название: {source['name']}\n"
        f"Тип: {source['type']}\n"
        f"URL: {source['url']}\n"
        f"Включен: {source['enabled']}\n"
        f"Cron: {source.get('schedule_cron') or '—'}\n"
        f"Перевод: {source.get('translate_enabled')}\n"
        f"Язык по умолчанию: {source.get('default_target_language') or 'ru'}"
    )


def _source_keyboard(source: dict) -> types.InlineKeyboardMarkup:
    source_id = source["id"]
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Запустить парсинг сейчас",
                    callback_data=f"source_parse_now_{source_id}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Вкл/выкл источник",
                    callback_data=f"source_toggle_{source_id}_{int(bool(source.get('enabled')))}",
                )
            ],
        ]
    )


@router.callback_query(F.data == "show_sources")
async def show_sources(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.APP_BASE_URL}/api/sources")
        if response.status_code != 200:
            await callback.message.answer(f"Не удалось загрузить источники: {response.text}")
            await callback.answer()
            return
        sources = response.json()

    if not sources:
        await callback.message.answer(
            "Источников пока нет.\n"
            "Создайте источник через API: POST /api/sources"
        )
        await callback.answer()
        return

    for source in sources:
        await callback.message.answer(_source_text(source), reply_markup=_source_keyboard(source))
    await callback.answer()


@router.callback_query(F.data.startswith("source_parse_now_"))
async def source_parse_now(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    source_id = callback.data.replace("source_parse_now_", "", 1)
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{settings.APP_BASE_URL}/api/sources/{source_id}/parse-now")
        if response.status_code != 200:
            await callback.message.answer(f"Не удалось запустить парсинг: {response.text}")
            await callback.answer()
            return
        stats = response.json()

    await callback.message.answer(
        f"Парсинг источника #{stats['source_id']} завершен.\n"
        f"processed={stats['processed']}, created={stats['created']}, drafts_created={stats['drafts_created']}"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("source_toggle_"))
async def source_toggle(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    _, _, source_id, enabled_flag = callback.data.split("_", 3)
    current_enabled = enabled_flag == "1"

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.APP_BASE_URL}/api/sources/{source_id}",
            json={"enabled": not current_enabled},
        )
        if response.status_code != 200:
            await callback.message.answer(f"Не удалось обновить источник: {response.text}")
            await callback.answer()
            return
        source = response.json()

    await callback.message.answer(
        f"Источник #{source['id']} обновлен: enabled={source['enabled']}\n"
        f"cron={source.get('schedule_cron') or '—'}"
    )
    await callback.answer()
