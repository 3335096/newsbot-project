from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import httpx

from core.config import settings

router = Router()


class PresetEditState(StatesGroup):
    waiting_for_system_prompt = State()
    waiting_for_user_template = State()

def _admin_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="LLM-пресеты", callback_data="admin_llm_presets")],
            [types.InlineKeyboardButton(text="Правила модерации", callback_data="admin_moderation_rules")],
        ]
    )


def _preset_action_keyboard(preset_name: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Изменить system prompt",
                    callback_data=f"admin_preset_edit_system_{preset_name}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Изменить user template",
                    callback_data=f"admin_preset_edit_user_{preset_name}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Вкл/выкл",
                    callback_data=f"admin_preset_toggle_{preset_name}",
                )
            ],
        ]
    )


@router.message(Command("admin"), F.from_user.id.in_(settings.admin_ids))
async def admin_panel(message: types.Message):
    await message.answer("Панель администратора.", reply_markup=_admin_keyboard())


@router.callback_query(F.data == "admin_llm_presets", F.from_user.id.in_(settings.admin_ids))
async def admin_llm_presets(callback: types.CallbackQuery):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.APP_BASE_URL}/api/llm/presets")
        if response.status_code != 200:
            await callback.message.answer(f"Не удалось загрузить пресеты: {response.text}")
            await callback.answer()
            return
        presets = response.json()

    if not presets:
        await callback.message.answer("Пресеты не найдены.")
        await callback.answer()
        return

    for preset in presets:
        text = (
            f"Пресет: {preset['name']}\n"
            f"Тип задачи: {preset['task_type']}\n"
            f"Модель: {preset.get('default_model') or '-'}\n"
            f"Включен: {preset['enabled']}"
        )
        await callback.message.answer(
            text,
            reply_markup=_preset_action_keyboard(preset["name"]),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_moderation_rules", F.from_user.id.in_(settings.admin_ids))
async def admin_moderation_rules(callback: types.CallbackQuery):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.APP_BASE_URL}/api/moderation/rules")
        if response.status_code != 200:
            await callback.message.answer(f"Не удалось загрузить правила модерации: {response.text}")
            await callback.answer()
            return
        rules = response.json()

    if not rules:
        await callback.message.answer(
            "Правила модерации ещё не добавлены.\n"
            "Используйте:\n"
            "/rule_add <kind> <pattern> <action> [comment]\n"
            "Типы правил: domain_blacklist | keyword_blacklist\n"
            "Действия: block | flag"
        )
        await callback.answer()
        return

    for rule in rules:
        text = (
            f"Правило #{rule['id']}\n"
            f"Тип: {rule['kind']}\n"
            f"Шаблон: {rule['pattern']}\n"
            f"Действие: {rule['action']}\n"
            f"Включено: {rule['enabled']}\n"
            f"Комментарий: {rule.get('comment') or '-'}"
        )
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Переключить правило",
                        callback_data=f"admin_rule_toggle_{rule['id']}",
                    )
                ]
            ]
        )
        await callback.message.answer(text, reply_markup=kb)

    await callback.message.answer(
        "Команда добавления правила:\n"
        "/rule_add <kind> <pattern> <action> [comment]\n"
        "Пример:\n"
        "/rule_add keyword_blacklist bitcoin block Спам по крипте"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_rule_toggle_"), F.from_user.id.in_(settings.admin_ids))
async def admin_toggle_rule(callback: types.CallbackQuery):
    rule_id = callback.data.replace("admin_rule_toggle_", "", 1)
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{settings.APP_BASE_URL}/api/moderation/rules/{rule_id}/toggle")
        if response.status_code != 200:
            await callback.message.answer(f"Не удалось переключить правило: {response.text}")
            await callback.answer()
            return
        rule = response.json()
    await callback.message.answer(
        f"Правило #{rule['id']} включено: {rule['enabled']}\n"
        f"{rule['kind']} | {rule['action']} | {rule['pattern']}"
    )
    await callback.answer()


@router.message(Command("rule_add"), F.from_user.id.in_(settings.admin_ids))
async def admin_rule_add(message: types.Message):
    # /rule_add <kind> <pattern> <action> [comment]
    parts = message.text.split(maxsplit=4) if message.text else []
    if len(parts) < 4:
        await message.answer(
            "Использование:\n"
            "/rule_add <kind> <pattern> <action> [comment]\n"
            "Типы правил: domain_blacklist | keyword_blacklist\n"
            "Действия: block | flag"
        )
        return
    kind, pattern, action = parts[1], parts[2], parts[3]
    comment = parts[4] if len(parts) > 4 else None

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/moderation/rules",
            json={
                "kind": kind,
                "pattern": pattern,
                "action": action,
                "enabled": True,
                "comment": comment,
            },
        )
        if response.status_code != 200:
            await message.answer(f"Ошибка: {response.text}")
            return
        rule = response.json()
        await message.answer(
            f"Правило создано #{rule['id']}: {rule['kind']} | {rule['action']} | {rule['pattern']}"
        )


@router.callback_query(F.data.startswith("admin_preset_toggle_"), F.from_user.id.in_(settings.admin_ids))
async def admin_toggle_preset(callback: types.CallbackQuery):
    preset_name = callback.data.replace("admin_preset_toggle_", "", 1)
    async with httpx.AsyncClient() as client:
        presets_resp = await client.get(f"{settings.APP_BASE_URL}/api/llm/presets")
        if presets_resp.status_code != 200:
            await callback.message.answer(f"Не удалось загрузить пресет: {presets_resp.text}")
            await callback.answer()
            return
        preset = next((p for p in presets_resp.json() if p["name"] == preset_name), None)
        if not preset:
            await callback.message.answer(f"Пресет '{preset_name}' не найден.")
            await callback.answer()
            return

        update_resp = await client.post(
            f"{settings.APP_BASE_URL}/api/llm/presets/{preset_name}",
            json={"enabled": not preset["enabled"]},
        )
        if update_resp.status_code != 200:
            await callback.message.answer(f"Не удалось обновить пресет: {update_resp.text}")
            await callback.answer()
            return
        updated = update_resp.json()

    await callback.message.answer(
        f"Пресет '{preset_name}' включен={updated['enabled']}",
        reply_markup=_preset_action_keyboard(preset_name),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin_preset_edit_system_"), F.from_user.id.in_(settings.admin_ids)
)
async def admin_edit_system_start(callback: types.CallbackQuery, state: FSMContext):
    preset_name = callback.data.replace("admin_preset_edit_system_", "", 1)
    await state.clear()
    await state.update_data(preset_name=preset_name)
    await callback.message.answer(
        f"Введите новый system prompt для пресета '{preset_name}':"
    )
    await state.set_state(PresetEditState.waiting_for_system_prompt)
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin_preset_edit_user_"), F.from_user.id.in_(settings.admin_ids)
)
async def admin_edit_user_start(callback: types.CallbackQuery, state: FSMContext):
    preset_name = callback.data.replace("admin_preset_edit_user_", "", 1)
    await state.clear()
    await state.update_data(preset_name=preset_name)
    await callback.message.answer(
        f"Введите новый user template для пресета '{preset_name}':"
    )
    await state.set_state(PresetEditState.waiting_for_user_template)
    await callback.answer()


@router.message(Command("preset_system"), F.from_user.id.in_(settings.admin_ids))
async def admin_update_system_prompt(message: types.Message):
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.answer("Использование: /preset_system <preset_name> <new system prompt>")
        return
    preset_name, new_prompt = parts[1], parts[2]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/llm/presets/{preset_name}",
            json={"system_prompt": new_prompt},
        )
        if response.status_code != 200:
            await message.answer(f"Ошибка: {response.text}")
            return
        await message.answer(f"System prompt обновлен для пресета '{preset_name}'.")


@router.message(PresetEditState.waiting_for_system_prompt, F.from_user.id.in_(settings.admin_ids))
async def admin_update_system_prompt_fsm(message: types.Message, state: FSMContext):
    new_prompt = (message.text or "").strip()
    if not new_prompt:
        await message.answer("Текст не может быть пустым. Введите новый system prompt:")
        return
    data = await state.get_data()
    preset_name = data.get("preset_name")
    if not preset_name:
        await message.answer("Не удалось определить пресет. Повторите действие.")
        await state.clear()
        return
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/llm/presets/{preset_name}",
            json={"system_prompt": new_prompt},
        )
        if response.status_code != 200:
            await message.answer(f"Ошибка обновления пресета: {response.text}")
            return
    await message.answer(
        f"System prompt обновлен для пресета '{preset_name}'.",
        reply_markup=_preset_action_keyboard(preset_name),
    )
    await state.clear()


@router.message(Command("preset_user"), F.from_user.id.in_(settings.admin_ids))
async def admin_update_user_template(message: types.Message):
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.answer("Использование: /preset_user <preset_name> <new user template>")
        return
    preset_name, new_template = parts[1], parts[2]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/llm/presets/{preset_name}",
            json={"user_prompt_template": new_template},
        )
        if response.status_code != 200:
            await message.answer(f"Ошибка: {response.text}")
            return
        await message.answer(f"User template обновлен для пресета '{preset_name}'.")


@router.message(PresetEditState.waiting_for_user_template, F.from_user.id.in_(settings.admin_ids))
async def admin_update_user_template_fsm(message: types.Message, state: FSMContext):
    new_template = (message.text or "").strip()
    if not new_template:
        await message.answer("Текст не может быть пустым. Введите новый user template:")
        return
    data = await state.get_data()
    preset_name = data.get("preset_name")
    if not preset_name:
        await message.answer("Не удалось определить пресет. Повторите действие.")
        await state.clear()
        return
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/llm/presets/{preset_name}",
            json={"user_prompt_template": new_template},
        )
        if response.status_code != 200:
            await message.answer(f"Ошибка обновления пресета: {response.text}")
            return
    await message.answer(
        f"User template обновлен для пресета '{preset_name}'.",
        reply_markup=_preset_action_keyboard(preset_name),
    )
    await state.clear()


@router.message(Command("admin"))
async def admin_panel_denied(message: types.Message):
    await message.answer("Команда доступна только администраторам.")

# More admin functionalities will be added here
