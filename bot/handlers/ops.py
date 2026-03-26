from __future__ import annotations

from aiogram import F, Router, types
from aiogram.types import CallbackQuery
import httpx

from core.config import settings

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


def _format_queue_stats(payload: dict) -> str:
    redis_ok = bool(payload.get("redis_ok"))
    worker_alive = bool(payload.get("worker_alive"))
    worker_seen = payload.get("worker_last_seen_iso") or "—"
    lines = [
        "Состояние очередей:",
        f"Redis: {'OK' if redis_ok else 'ERROR'}",
        f"Worker: {'alive' if worker_alive else 'down'}",
        f"Worker last seen: {worker_seen}",
        "",
        "Очереди:",
    ]
    for queue in payload.get("queues", []):
        lines.append(
            f"- {queue.get('name')}: "
            f"queued={queue.get('queued', 0)}, "
            f"started={queue.get('started', 0)}, "
            f"failed={queue.get('failed', 0)}, "
            f"scheduled={queue.get('scheduled', 0)}"
        )
    return "\n".join(lines)


def _format_ready(payload: dict) -> str:
    redis_ok = bool((payload.get("redis") or {}).get("ok"))
    worker_payload = payload.get("worker") or {}
    worker_alive = bool(worker_payload.get("alive"))
    worker_seen = worker_payload.get("last_seen")
    return (
        "Readiness:\n"
        f"status={payload.get('status')}\n"
        f"redis_ok={redis_ok}\n"
        f"worker_alive={worker_alive}\n"
        f"worker_last_seen={worker_seen}"
    )


def _ops_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Обновить queue stats",
                    callback_data="ops_queue_stats",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Проверить readiness",
                    callback_data="ops_readiness",
                )
            ],
        ]
    )


@router.callback_query(F.data == "show_ops")
async def show_ops(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.message.answer("Раздел доступен только администраторам.")
        await callback.answer()
        return
    await callback.message.answer(
        "Операционный раздел.\nВыберите действие:",
        reply_markup=_ops_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "ops_queue_stats")
async def ops_queue_stats(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.message.answer("Раздел доступен только администраторам.")
        await callback.answer()
        return
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.APP_BASE_URL}/api/queue/stats")
        if resp.status_code != 200:
            await callback.message.answer(f"Ошибка queue stats: {resp.text}")
            await callback.answer()
            return
        payload = resp.json()
    await callback.message.answer(_format_queue_stats(payload), reply_markup=_ops_keyboard())
    await callback.answer()


@router.callback_query(F.data == "ops_readiness")
async def ops_readiness(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.message.answer("Раздел доступен только администраторам.")
        await callback.answer()
        return
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.APP_BASE_URL}/health/ready")
        if resp.status_code != 200:
            await callback.message.answer(f"Ошибка readiness: {resp.text}")
            await callback.answer()
            return
        payload = resp.json()
    await callback.message.answer(_format_ready(payload), reply_markup=_ops_keyboard())
    await callback.answer()
