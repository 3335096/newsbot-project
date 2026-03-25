from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
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
        result = await task_service.run_task(
            db,
            draft_id=payload.draft_id,
            task_type=payload.task_type,
            preset_name=payload.preset,
            model=payload.model,
            max_len=payload.max_len,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task = result.task
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

