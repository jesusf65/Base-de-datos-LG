from fastapi import APIRouter, Request
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/telnyx", status_code=200)
async def webhook_telnyx(request: Request):
    payload = await request.json()
    event_type = payload.get("data", {}).get("event_type")
    logger.info(f"Evento Telnyx: {event_type}")

    if event_type == "call.answered":
        logger.info("✅ La llamada fue contestada")
    elif event_type == "call.hangup":
        logger.info("📴 La llamada fue colgada")

    return {"status": "ok"}