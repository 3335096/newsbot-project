from fastapi import APIRouter

router = APIRouter(prefix="/bot", tags=["bot"])


@router.post("/webhook")
async def bot_webhook() -> dict[str, str]:
    # Webhook integration will be wired in later iterations.
    return {"status": "accepted"}
