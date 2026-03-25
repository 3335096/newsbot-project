from aiogram import F, Router, types
from aiogram.filters import Command
import httpx

from core.config import settings

router = Router()

def _admin_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="LLM Presets", callback_data="admin_llm_presets")],
            [types.InlineKeyboardButton(text="Moderation Rules", callback_data="admin_moderation_rules")],
        ]
    )


def _preset_action_keyboard(preset_name: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Edit system prompt",
                    callback_data=f"admin_preset_edit_system_{preset_name}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Edit user template",
                    callback_data=f"admin_preset_edit_user_{preset_name}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Toggle enabled",
                    callback_data=f"admin_preset_toggle_{preset_name}",
                )
            ],
        ]
    )


@router.message(Command("admin"), F.from_user.id.in_(settings.admin_ids))
async def admin_panel(message: types.Message):
    await message.answer("Welcome to the admin panel!", reply_markup=_admin_keyboard())


@router.callback_query(F.data == "admin_llm_presets", F.from_user.id.in_(settings.admin_ids))
async def admin_llm_presets(callback: types.CallbackQuery):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.APP_BASE_URL}/api/llm/presets")
        if response.status_code != 200:
            await callback.message.answer(f"Failed to load presets: {response.text}")
            await callback.answer()
            return
        presets = response.json()

    if not presets:
        await callback.message.answer("No presets available.")
        await callback.answer()
        return

    for preset in presets:
        text = (
            f"Preset: {preset['name']}\n"
            f"Task type: {preset['task_type']}\n"
            f"Model: {preset.get('default_model') or '-'}\n"
            f"Enabled: {preset['enabled']}"
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
            await callback.message.answer(f"Failed to load moderation rules: {response.text}")
            await callback.answer()
            return
        rules = response.json()

    if not rules:
        await callback.message.answer(
            "No moderation rules yet.\n"
            "Use:\n"
            "/rule_add <kind> <pattern> <action> [comment]\n"
            "kind: domain_blacklist|keyword_blacklist\n"
            "action: block|flag"
        )
        await callback.answer()
        return

    for rule in rules:
        text = (
            f"Rule #{rule['id']}\n"
            f"kind: {rule['kind']}\n"
            f"pattern: {rule['pattern']}\n"
            f"action: {rule['action']}\n"
            f"enabled: {rule['enabled']}\n"
            f"comment: {rule.get('comment') or '-'}"
        )
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Toggle rule",
                        callback_data=f"admin_rule_toggle_{rule['id']}",
                    )
                ]
            ]
        )
        await callback.message.answer(text, reply_markup=kb)

    await callback.message.answer(
        "Add rule command:\n"
        "/rule_add <kind> <pattern> <action> [comment]\n"
        "Example:\n"
        "/rule_add keyword_blacklist bitcoin block Спам по крипте"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_rule_toggle_"), F.from_user.id.in_(settings.admin_ids))
async def admin_toggle_rule(callback: types.CallbackQuery):
    rule_id = callback.data.replace("admin_rule_toggle_", "", 1)
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{settings.APP_BASE_URL}/api/moderation/rules/{rule_id}/toggle")
        if response.status_code != 200:
            await callback.message.answer(f"Failed to toggle rule: {response.text}")
            await callback.answer()
            return
        rule = response.json()
    await callback.message.answer(
        f"Rule #{rule['id']} enabled={rule['enabled']}\n"
        f"{rule['kind']} | {rule['action']} | {rule['pattern']}"
    )
    await callback.answer()


@router.message(Command("rule_add"), F.from_user.id.in_(settings.admin_ids))
async def admin_rule_add(message: types.Message):
    # /rule_add <kind> <pattern> <action> [comment]
    parts = message.text.split(maxsplit=4) if message.text else []
    if len(parts) < 4:
        await message.answer(
            "Usage:\n"
            "/rule_add <kind> <pattern> <action> [comment]\n"
            "kind: domain_blacklist|keyword_blacklist\n"
            "action: block|flag"
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
            await message.answer(f"Failed: {response.text}")
            return
        rule = response.json()
        await message.answer(
            f"Rule created #{rule['id']}: {rule['kind']} | {rule['action']} | {rule['pattern']}"
        )


@router.callback_query(F.data.startswith("admin_preset_toggle_"), F.from_user.id.in_(settings.admin_ids))
async def admin_toggle_preset(callback: types.CallbackQuery):
    preset_name = callback.data.replace("admin_preset_toggle_", "", 1)
    async with httpx.AsyncClient() as client:
        presets_resp = await client.get(f"{settings.APP_BASE_URL}/api/llm/presets")
        if presets_resp.status_code != 200:
            await callback.message.answer(f"Failed to load preset: {presets_resp.text}")
            await callback.answer()
            return
        preset = next((p for p in presets_resp.json() if p["name"] == preset_name), None)
        if not preset:
            await callback.message.answer(f"Preset '{preset_name}' not found.")
            await callback.answer()
            return

        update_resp = await client.post(
            f"{settings.APP_BASE_URL}/api/llm/presets/{preset_name}",
            json={"enabled": not preset["enabled"]},
        )
        if update_resp.status_code != 200:
            await callback.message.answer(f"Failed to update preset: {update_resp.text}")
            await callback.answer()
            return
        updated = update_resp.json()

    await callback.message.answer(
        f"Preset '{preset_name}' enabled={updated['enabled']}",
        reply_markup=_preset_action_keyboard(preset_name),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin_preset_edit_system_"), F.from_user.id.in_(settings.admin_ids)
)
async def admin_edit_system_hint(callback: types.CallbackQuery):
    preset_name = callback.data.replace("admin_preset_edit_system_", "", 1)
    await callback.message.answer(
        f"To update system prompt run:\n"
        f"/preset_system {preset_name} <new prompt text>"
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin_preset_edit_user_"), F.from_user.id.in_(settings.admin_ids)
)
async def admin_edit_user_hint(callback: types.CallbackQuery):
    preset_name = callback.data.replace("admin_preset_edit_user_", "", 1)
    await callback.message.answer(
        f"To update user template run:\n"
        f"/preset_user {preset_name} <new template text>"
    )
    await callback.answer()


@router.message(Command("preset_system"), F.from_user.id.in_(settings.admin_ids))
async def admin_update_system_prompt(message: types.Message):
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.answer("Usage: /preset_system <preset_name> <new system prompt>")
        return
    preset_name, new_prompt = parts[1], parts[2]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/llm/presets/{preset_name}",
            json={"system_prompt": new_prompt},
        )
        if response.status_code != 200:
            await message.answer(f"Failed: {response.text}")
            return
        await message.answer(f"System prompt updated for preset '{preset_name}'.")


@router.message(Command("preset_user"), F.from_user.id.in_(settings.admin_ids))
async def admin_update_user_template(message: types.Message):
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.answer("Usage: /preset_user <preset_name> <new user template>")
        return
    preset_name, new_template = parts[1], parts[2]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/llm/presets/{preset_name}",
            json={"user_prompt_template": new_template},
        )
        if response.status_code != 200:
            await message.answer(f"Failed: {response.text}")
            return
        await message.answer(f"User template updated for preset '{preset_name}'.")


@router.message(Command("admin"))
async def admin_panel_denied(message: types.Message):
    await message.answer("Команда доступна только администраторам.")

# More admin functionalities will be added here
