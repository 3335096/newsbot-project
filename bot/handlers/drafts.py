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
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Approve", callback_data=f"approve_draft_{draft['id']}")],
            [types.InlineKeyboardButton(text="Reject", callback_data=f"reject_draft_{draft['id']}")]
        ])
        await callback.message.answer(f"Draft ID: {draft['id']}\nTitle: {draft['title_translated']}\nStatus: {draft['status']}", reply_markup=keyboard)
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
