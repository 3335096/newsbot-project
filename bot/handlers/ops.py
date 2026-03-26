from __future__ import annotations

from aiogram import F, Router, types
from aiogram.types import CallbackQuery
import httpx

from core.config import settings

router = Router()
MAX_FAILED_MARKERS_TO_SHOW = 10


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
            [
                types.InlineKeyboardButton(
                    text="Показать failed jobs",
                    callback_data="ops_failed_list",
                )
            ],
        ]
    )


def _failed_jobs_keyboard(job_ids: list[str]) -> types.InlineKeyboardMarkup:
    rows: list[list[types.InlineKeyboardButton]] = []
    for job_id in job_ids[:MAX_FAILED_MARKERS_TO_SHOW]:
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"Requeue {job_id}",
                    callback_data=f"ops_requeue_failed:{job_id}",
                )
            ]
        )
    rows.append(
        [
            types.InlineKeyboardButton(
                text="Назад в операции",
                callback_data="show_ops",
            )
        ]
    )
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


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


@router.callback_query(F.data == "ops_failed_list")
async def ops_failed_list(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.message.answer("Раздел доступен только администраторам.")
        await callback.answer()
        return
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.APP_BASE_URL}/api/queue/failed")
        if resp.status_code != 200:
            await callback.message.answer(f"Ошибка получения списка failed jobs: {resp.text}")
            await callback.answer()
            return
        rows = resp.json()
    job_ids = [row.get("original_job_id") for row in rows if row.get("original_job_id")]
    if not job_ids:
        await callback.message.answer(
            "В failed queue сейчас нет marker jobs.",
            reply_markup=_ops_keyboard(),
        )
        await callback.answer()
        return
    await callback.message.answer(
        "Последние failed jobs (requeue по кнопке):",
        reply_markup=_failed_jobs_keyboard(job_ids),
    )
    await callback.answer()


@router.message(F.text.startswith("/requeue_failed"))
async def requeue_failed_command(message: types.Message):
    if not message.from_user or not _is_admin(message.from_user.id):
        await message.answer("Раздел доступен только администраторам.")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /requeue_failed <job_id>")
        return
    job_id = parts[1].strip()
    if not job_id:
        await message.answer("Использование: /requeue_failed <job_id>")
        return
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{settings.APP_BASE_URL}/api/queue/failed/{job_id}/requeue")
        if resp.status_code != 200:
            await message.answer(f"Не удалось requeue job {job_id}: {resp.text}")
            return
    await message.answer(f"Job {job_id} успешно поставлен на повторную обработку.")


@router.callback_query(F.data.startswith("ops_requeue_failed:"))
async def ops_requeue_failed(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.message.answer("Раздел доступен только администраторам.")
        await callback.answer()
        return
    job_id = callback.data.split(":", 1)[1]
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{settings.APP_BASE_URL}/api/queue/failed/{job_id}/requeue")
        if resp.status_code != 200:
            await callback.message.answer(f"Не удалось requeue job {job_id}: {resp.text}")
            await callback.answer()
            return
    await callback.message.answer(
        f"Job {job_id} успешно поставлен на повторную обработку.",
        reply_markup=_ops_keyboard(),
    )
    await callback.answer()
