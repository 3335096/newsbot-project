from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
import httpx
from core.config import settings

router = Router()

class DraftsState(StatesGroup):
    waiting_for_rejection_reason = State()


def _is_allowed_user(user_id: int) -> bool:
    return user_id in settings.allowed_user_ids


def _card_text(draft: dict, view_mode: str) -> str:
    is_original = view_mode == "original"
    title = (
        draft.get("title_original")
        if is_original
        else draft.get("title_translated")
    ) or "—"
    content = (
        draft.get("content_original")
        if is_original
        else draft.get("content_translated")
    ) or "—"
    lang_line = f"{draft.get('source_language') or 'unknown'} → {draft.get('target_language') or 'ru'}"
    mode_label = "ORIGINAL" if is_original else "TRANSLATION"
    flags = draft.get("flags") or []
    flags_block = ""
    if flags:
        lines = []
        for item in flags[:5]:
            lines.append(
                f"- {item.get('kind')} | {item.get('action')} | {item.get('pattern')}"
            )
        flags_block = "\n\nModeration flags:\n" + "\n".join(lines)
    return (
        f"Draft ID: {draft['id']}\n"
        f"Status: {draft['status']}\n"
        f"Language: {lang_line}\n"
        f"Mode: {mode_label}\n\n"
        f"Title: {title}\n\n"
        f"Content: {content}"
        f"{flags_block}"
    )


def _card_keyboard(draft_id: int, view_mode: str) -> types.InlineKeyboardMarkup:
    switch_label = "Show translation" if view_mode == "original" else "Show original"
    channel_buttons = []
    for channel_key in settings.channel_ids.keys():
        channel_buttons.append(
            [types.InlineKeyboardButton(text=f"Publish now: {channel_key}", callback_data=f"publish_now_{draft_id}_{channel_key}")]
        )
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=switch_label, callback_data=f"toggle_view_{draft_id}_{view_mode}")],
            [types.InlineKeyboardButton(text="Summary", callback_data=f"llm_summary_{draft_id}")],
            [types.InlineKeyboardButton(text="Rewrite style", callback_data=f"llm_rewrite_{draft_id}")],
            [types.InlineKeyboardButton(text="Title/Hashtags", callback_data=f"llm_title_hashtags_{draft_id}")],
            *channel_buttons,
            [types.InlineKeyboardButton(text="Approve", callback_data=f"approve_draft_{draft_id}")],
            [types.InlineKeyboardButton(text="Reject", callback_data=f"reject_draft_{draft_id}")],
        ]
    )

@router.callback_query(F.data == "show_drafts")
async def show_drafts(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.APP_BASE_URL}/api/drafts")
        drafts = response.json()

    if not drafts:
        await callback.message.answer("No drafts available.")
        await callback.answer()
        return

    for draft in drafts:
        await callback.message.answer(
            _card_text(draft, view_mode="translated"),
            reply_markup=_card_keyboard(draft["id"], view_mode="translated"),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_view_"))
async def toggle_view_callback(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    _, _, draft_id_str, current_mode = callback.data.split("_", 3)
    draft_id = int(draft_id_str)
    next_mode = "original" if current_mode == "translated" else "translated"

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.APP_BASE_URL}/api/drafts/{draft_id}")
        if response.status_code != 200:
            await callback.message.answer(f"Failed to load draft {draft_id}: {response.text}")
            await callback.answer()
            return
        draft = response.json()

    await callback.message.edit_text(
        _card_text(draft, view_mode=next_mode),
        reply_markup=_card_keyboard(draft_id, view_mode=next_mode),
    )
    await callback.answer()

@router.callback_query(F.data.startswith("approve_draft_"))
async def approve_draft_callback(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    draft_id = callback.data.split("_")[2]
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{settings.APP_BASE_URL}/api/drafts/{draft_id}/approve")
        if response.status_code == 200:
            await callback.message.answer(f"Draft {draft_id} approved.")
        else:
            await callback.message.answer(f"Failed to approve draft {draft_id}: {response.text}")
    await callback.answer()


@router.callback_query(F.data.startswith("llm_summary_"))
async def llm_summary_callback(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    draft_id = callback.data.split("_")[2]
    await _run_llm_and_report(callback, draft_id=draft_id, task_type="summary", preset="summary")
    await callback.answer()


@router.callback_query(F.data.startswith("llm_rewrite_"))
async def llm_rewrite_callback(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    draft_id = callback.data.split("_")[2]
    await _run_llm_and_report(
        callback,
        draft_id=draft_id,
        task_type="rewrite",
        preset="rewrite_style",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("llm_title_hashtags_"))
async def llm_title_hashtags_callback(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return
    draft_id = callback.data.split("_")[3]
    await _run_llm_and_report(
        callback,
        draft_id=draft_id,
        task_type="title_hashtags",
        preset="title_hashtags",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("publish_now_"))
async def publish_now_callback(callback: CallbackQuery):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    # publish_now_<draft_id>_<channel_key>
    _, _, draft_id, channel_key = callback.data.split("_", 3)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/publications",
            json={
                "draft_id": int(draft_id),
                "channel": channel_key,
                "publish_now": True,
            },
        )
        if response.status_code != 200:
            await callback.message.answer(f"Publish failed: {response.text}")
            await callback.answer()
            return
        publication = response.json()
        await callback.message.answer(
            f"Published: publication_id={publication['id']}, "
            f"status={publication['status']}, message_id={publication.get('message_id')}"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("reject_draft_"))
async def reject_draft_callback(callback: CallbackQuery, state: FSMContext):
    if not _is_allowed_user(callback.from_user.id):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return

    draft_id = callback.data.split("_")[2]
    await state.update_data(draft_id=draft_id)
    await callback.message.answer("Please provide a reason for rejection:")
    await state.set_state(DraftsState.waiting_for_rejection_reason)
    await callback.answer()

@router.message(DraftsState.waiting_for_rejection_reason)
async def process_rejection_reason(message: types.Message, state: FSMContext):
    if not _is_allowed_user(message.from_user.id):
        await message.answer("Доступ запрещен.")
        await state.clear()
        return

    user_data = await state.get_data()
    draft_id = user_data.get("draft_id")
    reason = message.text

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/drafts/{draft_id}/reject",
            json={"reason": reason},
        )
        if response.status_code == 200:
            await message.answer(f"Draft {draft_id} rejected with reason: {reason}")
        else:
            await message.answer(f"Failed to reject draft {draft_id}: {response.text}")
    await state.clear()


async def _run_llm_and_report(
    callback: CallbackQuery,
    *,
    draft_id: str,
    task_type: str,
    preset: str,
) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.APP_BASE_URL}/api/llm/tasks",
            json={
                "draft_id": int(draft_id),
                "task_type": task_type,
                "preset": preset,
            },
        )
        if response.status_code != 200:
            await callback.message.answer(f"LLM task failed: {response.text}")
            return
        task = response.json()
        await callback.message.answer(
            f"LLM task done: id={task['id']}, status={task['status']}\n"
            f"Result:\n{(task.get('result') or '')[:1200]}"
        )
