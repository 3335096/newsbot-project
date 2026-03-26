from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models.llm_task import LLMTask
from app.db.session import get_db
from app.metrics import record_llm_task
from app.services.queue_dispatcher import enqueue_llm_task, requeue_llm_task
from app.services.llm_preset_service import LLMPresetService
from app.services.llm_task_service import LLMTaskService

router = APIRouter(prefix="/llm", tags=["llm"])

preset_service = LLMPresetService()
task_service = LLMTaskService()


class PresetOut(BaseModel):
    name: str
    task_type: str
    system_prompt: str
    user_prompt_template: str
    default_model: str | None
    enabled: bool


class PresetUpdatePayload(BaseModel):
    system_prompt: str | None = None
    user_prompt_template: str | None = None
    default_model: str | None = None
    enabled: bool | None = None


class RunTaskPayload(BaseModel):
    draft_id: int
    task_type: str
    preset: str
    model: str | None = None
    max_len: int = 700


class LLMTaskOut(BaseModel):
    id: int
    draft_id: int | None
    task_type: str
    preset: str | None
    model: str | None
    status: str
    result: str | None
    error: str | None


class RetryTaskPayload(BaseModel):
    max_len: int = 700


def _task_to_out(task: LLMTask) -> dict:
    return {
        "id": task.id,
        "draft_id": task.draft_id,
        "task_type": task.task_type,
        "preset": task.preset,
        "model": task.model,
        "status": task.status,
        "result": task.result,
        "error": task.error,
    }


@router.get("/presets", response_model=list[PresetOut])
async def list_presets(db: Session = Depends(get_db)):
    presets = preset_service.list_presets(db)
    return [
        {
            "name": p.name,
            "task_type": p.task_type,
            "system_prompt": p.system_prompt,
            "user_prompt_template": p.user_prompt_template,
            "default_model": p.default_model,
            "enabled": p.enabled,
        }
        for p in presets
    ]


@router.post("/presets/{preset_name}", response_model=PresetOut)
async def update_preset(
    preset_name: str,
    payload: PresetUpdatePayload,
    db: Session = Depends(get_db),
):
    try:
        preset = preset_service.update_preset(
            db,
            name=preset_name,
            system_prompt=payload.system_prompt,
            user_prompt_template=payload.user_prompt_template,
            default_model=payload.default_model,
            enabled=payload.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "name": preset.name,
        "task_type": preset.task_type,
        "system_prompt": preset.system_prompt,
        "user_prompt_template": preset.user_prompt_template,
        "default_model": preset.default_model,
        "enabled": preset.enabled,
    }


@router.post("/tasks", response_model=LLMTaskOut)
async def run_llm_task(payload: RunTaskPayload, db: Session = Depends(get_db)):
    try:
        task = task_service.create_task(
            db,
            draft_id=payload.draft_id,
            task_type=payload.task_type,
            preset_name=payload.preset,
            model=payload.model,
            max_len=payload.max_len,
        )
        job_id = enqueue_llm_task(db, task, max_len=payload.max_len)
        db.refresh(task)
    except ValueError as exc:
        record_llm_task(task_type=payload.task_type, status="invalid_request")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _task_to_out(task)


@router.get("/tasks/{task_id}", response_model=LLMTaskOut)
async def get_llm_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(LLMTask).filter(LLMTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_out(task)


@router.post("/tasks/{task_id}/retry", response_model=LLMTaskOut)
async def retry_llm_task(task_id: int, payload: RetryTaskPayload, db: Session = Depends(get_db)):
    task = db.query(LLMTask).filter(LLMTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in {"error", "success"}:
        raise HTTPException(status_code=409, detail="Task cannot be retried in current state")
    if not task.draft_id or not task.task_type or not task.preset:
        raise HTTPException(status_code=400, detail="Task payload is incomplete for retry")

    task.result = None
    task.error = None
    task.status = "queued"
    db.commit()
    db.refresh(task)
    enqueue_llm_task(db, task, max_len=payload.max_len)
    db.refresh(task)
    return _task_to_out(task)


@router.post("/tasks/{task_id}/requeue", response_model=LLMTaskOut)
async def requeue_failed_llm_task(task_id: int, payload: RetryTaskPayload, db: Session = Depends(get_db)):
    task = db.query(LLMTask).filter(LLMTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "error":
        raise HTTPException(status_code=409, detail="Only errored tasks can be requeued")
    if not task.draft_id or not task.task_type or not task.preset:
        raise HTTPException(status_code=400, detail="Task payload is incomplete for requeue")

    if requeue_llm_task(db, task, max_len=payload.max_len) is None:
        raise HTTPException(status_code=409, detail="Task was not requeued")
    db.refresh(task)
    return _task_to_out(task)

