from __future__ import annotations

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
import httpx

from core.config import settings

router = Router()


class SourceCreateState(StatesGroup):
    waiting_for_name = State()
    waiting_for_type = State()
    waiting_for_url = State()
    waiting_for_cron = State()


class SourceEditState(StatesGroup):
    waiting_for_name = State()
    waiting_for_cron = State()
    waiting_for_type = State()
    waiting_for_url = State()
    waiting_for_default_language = State()


def _is_allowed_user(user_id: int) -> bool:
    return user_id in settings.allowed_user_ids


async def _ensure_allowed_message(message: types.Message, state: FSMContext) -> bool:
    if not message.from_user or not _is_allowed_user(message.from_user.id):
        await message.answer("Доступ запрещен.")
        await state.clear()
        return False
    return True


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
                    text="Изменить название",
                    callback_data=f"source_edit_name_{source_id}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Изменить cron",
                    callback_data=f"source_edit_cron_{source_id}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Изменить тип",
                    callback_data=f"source_edit_type_{source_id}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Изменить URL",
                    callback_data=f"source_edit_url_{source_id}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Переключить перевод",
                    callback_data=f"source_edit_translate_{source_id}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Изменить язык по умолчанию",
                    callback_data=f"source_edit_lang_{source_id}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Запустить парсинг сейчас",
                    callback_data=f"source_parse_now_{source_id}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Вкл/выкл источник",
                    callback_data=f"source_toggle:{source_id}:{int(bool(source.get('enabled')))}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Удалить источник",
                    callback_data=f"source_delete_{source_id}",
                )
            ],
        ]
    )


def _sources_actions_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Добавить источник",
                    callback_data="source_create_start",
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
            "Можно создать прямо в боте.",
            reply_markup=_sources_actions_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.answer("Управление источниками:", reply_markup=_sources_actions_keyboard())
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


@router.callback_query(F.data.startswith("source_toggle:"))
async def source_toggle(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    _, source_id, enabled_flag = callback.data.split(":", 2)
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


@router.callback_query(F.data == "source_create_start")
async def source_create_start(callback: CallbackQuery, state: FSMContext):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    await state.clear()
    await callback.message.answer("Создание источника.\nВведите название:")
    await state.set_state(SourceCreateState.waiting_for_name)
    await callback.answer()


@router.message(SourceCreateState.waiting_for_name)
async def source_create_name(message: types.Message, state: FSMContext):
    if not await _ensure_allowed_message(message, state):
        return
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым. Введите название:")
        return
    await state.update_data(name=name)
    await message.answer("Введите тип источника: rss или site")
    await state.set_state(SourceCreateState.waiting_for_type)


@router.message(SourceCreateState.waiting_for_type)
async def source_create_type(message: types.Message, state: FSMContext):
    if not await _ensure_allowed_message(message, state):
        return
    source_type = (message.text or "").strip().lower()
    if source_type not in {"rss", "site"}:
        await message.answer("Неверный тип. Введите: rss или site")
        return
    await state.update_data(type=source_type)
    await message.answer("Введите URL источника:")
    await state.set_state(SourceCreateState.waiting_for_url)


@router.message(SourceCreateState.waiting_for_url)
async def source_create_url(message: types.Message, state: FSMContext):
    if not await _ensure_allowed_message(message, state):
        return
    url = (message.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("URL должен начинаться с http:// или https://")
        return
    await state.update_data(url=url)
    await message.answer("Введите cron расписание или '-' чтобы пропустить (пример: */15 * * * *)")
    await state.set_state(SourceCreateState.waiting_for_cron)


@router.message(SourceCreateState.waiting_for_cron)
async def source_create_cron(message: types.Message, state: FSMContext):
    if not await _ensure_allowed_message(message, state):
        return
    cron = (message.text or "").strip()
    if cron == "-":
        cron = None
    payload = await state.get_data()
    request_payload = {
        "name": payload["name"],
        "type": payload["type"],
        "url": payload["url"],
        "enabled": True,
        "schedule_cron": cron,
        "translate_enabled": True,
        "default_target_language": "ru",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/sources",
            json=request_payload,
        )
        if response.status_code != 200:
            await message.answer(f"Не удалось создать источник: {response.text}")
            return
        source = response.json()
    await message.answer(
        "Источник создан:\n"
        f"{_source_text(source)}",
        reply_markup=_source_keyboard(source),
    )
    await state.clear()


@router.callback_query(F.data.startswith("source_edit_name_"))
async def source_edit_name_start(callback: CallbackQuery, state: FSMContext):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    source_id = callback.data.replace("source_edit_name_", "", 1)
    await state.clear()
    await state.update_data(source_id=source_id)
    await callback.message.answer(f"Введите новое название для источника #{source_id}:")
    await state.set_state(SourceEditState.waiting_for_name)
    await callback.answer()


@router.message(SourceEditState.waiting_for_name)
async def source_edit_name_finish(message: types.Message, state: FSMContext):
    if not await _ensure_allowed_message(message, state):
        return
    new_name = (message.text or "").strip()
    if not new_name:
        await message.answer("Название не может быть пустым. Введите новое название:")
        return
    data = await state.get_data()
    source_id = data.get("source_id")
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.APP_BASE_URL}/api/sources/{source_id}",
            json={"name": new_name},
        )
        if response.status_code != 200:
            await message.answer(f"Не удалось обновить источник: {response.text}")
            return
        source = response.json()
    await message.answer(
        "Источник обновлен:\n"
        f"{_source_text(source)}",
        reply_markup=_source_keyboard(source),
    )
    await state.clear()


@router.callback_query(F.data.startswith("source_edit_cron_"))
async def source_edit_cron_start(callback: CallbackQuery, state: FSMContext):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    source_id = callback.data.replace("source_edit_cron_", "", 1)
    await state.clear()
    await state.update_data(source_id=source_id)
    await callback.message.answer(
        f"Введите новый cron для источника #{source_id} или '-' чтобы очистить:"
    )
    await state.set_state(SourceEditState.waiting_for_cron)
    await callback.answer()


@router.message(SourceEditState.waiting_for_cron)
async def source_edit_cron_finish(message: types.Message, state: FSMContext):
    if not await _ensure_allowed_message(message, state):
        return
    cron = (message.text or "").strip()
    if cron == "-":
        cron = None
    data = await state.get_data()
    source_id = data.get("source_id")
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.APP_BASE_URL}/api/sources/{source_id}",
            json={"schedule_cron": cron},
        )
        if response.status_code != 200:
            await message.answer(f"Не удалось обновить cron: {response.text}")
            return
        source = response.json()
    await message.answer(
        "Источник обновлен:\n"
        f"{_source_text(source)}",
        reply_markup=_source_keyboard(source),
    )
    await state.clear()


@router.callback_query(F.data.startswith("source_edit_type_"))
async def source_edit_type_start(callback: CallbackQuery, state: FSMContext):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    source_id = callback.data.replace("source_edit_type_", "", 1)
    await state.clear()
    await state.update_data(source_id=source_id)
    await callback.message.answer(
        f"Введите новый тип для источника #{source_id}: rss или site"
    )
    await state.set_state(SourceEditState.waiting_for_type)
    await callback.answer()


@router.message(SourceEditState.waiting_for_type)
async def source_edit_type_finish(message: types.Message, state: FSMContext):
    if not await _ensure_allowed_message(message, state):
        return
    source_type = (message.text or "").strip().lower()
    if source_type not in {"rss", "site"}:
        await message.answer("Неверный тип. Введите: rss или site")
        return
    data = await state.get_data()
    source_id = data.get("source_id")
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.APP_BASE_URL}/api/sources/{source_id}",
            json={"type": source_type},
        )
        if response.status_code != 200:
            await message.answer(f"Не удалось обновить тип: {response.text}")
            return
        source = response.json()
    await message.answer(
        "Источник обновлен:\n"
        f"{_source_text(source)}",
        reply_markup=_source_keyboard(source),
    )
    await state.clear()


@router.callback_query(F.data.startswith("source_edit_url_"))
async def source_edit_url_start(callback: CallbackQuery, state: FSMContext):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    source_id = callback.data.replace("source_edit_url_", "", 1)
    await state.clear()
    await state.update_data(source_id=source_id)
    await callback.message.answer(f"Введите новый URL для источника #{source_id}:")
    await state.set_state(SourceEditState.waiting_for_url)
    await callback.answer()


@router.message(SourceEditState.waiting_for_url)
async def source_edit_url_finish(message: types.Message, state: FSMContext):
    if not await _ensure_allowed_message(message, state):
        return
    url = (message.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("URL должен начинаться с http:// или https://")
        return
    data = await state.get_data()
    source_id = data.get("source_id")
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.APP_BASE_URL}/api/sources/{source_id}",
            json={"url": url},
        )
        if response.status_code != 200:
            await message.answer(f"Не удалось обновить URL: {response.text}")
            return
        source = response.json()
    await message.answer(
        "Источник обновлен:\n"
        f"{_source_text(source)}",
        reply_markup=_source_keyboard(source),
    )
    await state.clear()


@router.callback_query(F.data.startswith("source_edit_translate_"))
async def source_edit_translate_toggle(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    source_id = callback.data.replace("source_edit_translate_", "", 1)
    async with httpx.AsyncClient() as client:
        current_resp = await client.get(f"{settings.APP_BASE_URL}/api/sources/{source_id}")
        if current_resp.status_code != 200:
            await callback.message.answer(f"Не удалось загрузить источник: {current_resp.text}")
            await callback.answer()
            return
        source = current_resp.json()
        update_resp = await client.put(
            f"{settings.APP_BASE_URL}/api/sources/{source_id}",
            json={"translate_enabled": not bool(source.get("translate_enabled"))},
        )
        if update_resp.status_code != 200:
            await callback.message.answer(f"Не удалось обновить перевод: {update_resp.text}")
            await callback.answer()
            return
        updated = update_resp.json()
    await callback.message.answer(
        "Источник обновлен:\n"
        f"{_source_text(updated)}",
        reply_markup=_source_keyboard(updated),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("source_edit_lang_"))
async def source_edit_lang_start(callback: CallbackQuery, state: FSMContext):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    source_id = callback.data.replace("source_edit_lang_", "", 1)
    await state.clear()
    await state.update_data(source_id=source_id)
    await callback.message.answer(
        f"Введите язык по умолчанию для источника #{source_id} (например: ru, en, de):"
    )
    await state.set_state(SourceEditState.waiting_for_default_language)
    await callback.answer()


@router.message(SourceEditState.waiting_for_default_language)
async def source_edit_lang_finish(message: types.Message, state: FSMContext):
    if not await _ensure_allowed_message(message, state):
        return
    lang = (message.text or "").strip().lower()
    if len(lang) < 2:
        await message.answer("Код языка слишком короткий. Пример: ru")
        return
    data = await state.get_data()
    source_id = data.get("source_id")
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.APP_BASE_URL}/api/sources/{source_id}",
            json={"default_target_language": lang},
        )
        if response.status_code != 200:
            await message.answer(f"Не удалось обновить язык: {response.text}")
            return
        source = response.json()
    await message.answer(
        "Источник обновлен:\n"
        f"{_source_text(source)}",
        reply_markup=_source_keyboard(source),
    )
    await state.clear()


@router.callback_query(F.data.startswith("source_delete_"))
async def source_delete(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    source_id = callback.data.replace("source_delete_", "", 1)
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{settings.APP_BASE_URL}/api/sources/{source_id}")
        if response.status_code != 200:
            await callback.message.answer(f"Не удалось удалить источник: {response.text}")
            await callback.answer()
            return
    await callback.message.answer(f"Источник #{source_id} удален.")
    await callback.answer()
