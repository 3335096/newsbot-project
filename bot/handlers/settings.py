from __future__ import annotations

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
import httpx

from core.config import settings

router = Router()


class SettingsState(StatesGroup):
    waiting_for_default_language = State()


def _is_allowed_user(user_id: int) -> bool:
    return user_id in settings.allowed_user_ids


def _settings_keyboard(payload: dict) -> types.InlineKeyboardMarkup:
    user_settings = payload.get("settings") or {}
    enable_images = bool(user_settings.get("enable_images", settings.ENABLE_IMAGES))
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Изменить язык по умолчанию",
                    callback_data="settings_edit_default_lang",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=f"Картинки: {'ON' if enable_images else 'OFF'} (переключить)",
                    callback_data="settings_toggle_images",
                )
            ],
        ]
    )


def _settings_text(payload: dict) -> str:
    user_settings = payload.get("settings") or {}
    return (
        "Ваши настройки:\n"
        f"- default_target_language: {user_settings.get('default_target_language')}\n"
        f"- enable_images: {user_settings.get('enable_images')}"
    )


async def _fetch_user_settings(telegram_user_id: int) -> tuple[int, dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.APP_BASE_URL}/api/users/{telegram_user_id}/settings")
        return resp.status_code, (resp.json() if resp.status_code == 200 else {"detail": resp.text})


@router.callback_query(F.data == "show_settings")
async def show_settings(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    code, payload = await _fetch_user_settings(callback.from_user.id)
    if code != 200:
        await callback.message.answer(f"Не удалось загрузить настройки: {payload.get('detail')}")
        await callback.answer()
        return
    await callback.message.answer(
        _settings_text(payload),
        reply_markup=_settings_keyboard(payload),
    )
    await callback.answer()


@router.callback_query(F.data == "settings_toggle_images")
async def settings_toggle_images(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    code, payload = await _fetch_user_settings(callback.from_user.id)
    if code != 200:
        await callback.message.answer(f"Не удалось загрузить настройки: {payload.get('detail')}")
        await callback.answer()
        return

    current = bool((payload.get("settings") or {}).get("enable_images", settings.ENABLE_IMAGES))
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.APP_BASE_URL}/api/users/{callback.from_user.id}/settings",
            json={"enable_images": not current},
        )
        if resp.status_code != 200:
            await callback.message.answer(f"Не удалось обновить настройки: {resp.text}")
            await callback.answer()
            return
        updated = resp.json()

    await callback.message.answer(
        _settings_text(updated),
        reply_markup=_settings_keyboard(updated),
    )
    await callback.answer()


@router.callback_query(F.data == "settings_edit_default_lang")
async def settings_edit_default_lang_start(callback: CallbackQuery, state: FSMContext):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    await state.clear()
    await callback.message.answer("Введите default_target_language (например: ru, en, de):")
    await state.set_state(SettingsState.waiting_for_default_language)
    await callback.answer()


@router.message(SettingsState.waiting_for_default_language)
async def settings_edit_default_lang_finish(message: types.Message, state: FSMContext):
    if not message.from_user or not _is_allowed_user(message.from_user.id):
        await message.answer("Доступ запрещен.")
        await state.clear()
        return
    lang = (message.text or "").strip().lower()
    if len(lang) < 2:
        await message.answer("Код языка слишком короткий. Пример: ru")
        return

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.APP_BASE_URL}/api/users/{message.from_user.id}/settings",
            json={"default_target_language": lang},
        )
        if resp.status_code != 200:
            await message.answer(f"Не удалось обновить настройки: {resp.text}")
            return
        updated = resp.json()

    await message.answer(
        _settings_text(updated),
        reply_markup=_settings_keyboard(updated),
    )
    await state.clear()
