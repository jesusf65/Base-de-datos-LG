from fastapi import APIRouter, Request
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/telnyx")
async def telnyx_webhook(request: Request):
    payload = await request.json()
    logger.info(f"📞 Evento Telnyx recibido: {payload}")

    event_type = payload.get("data", {}).get("event_type")
    call_control_id = payload.get("data", {}).get("payload", {}).get("call_control_id")

    # Aquí podrías reaccionar a eventos específicos
    if event_type == "call.initiated":
        logger.info(f"📞 Llamada iniciada - Call Control ID: {call_control_id}")
    elif event_type == "call.answered":
        logger.info(f"✅ Llamada respondida - Call Control ID: {call_control_id}")
    elif event_type == "call.hangup":
        logger.info(f"❌ Llamada finalizada - Call Control ID: {call_control_id}")
    else:
        logger.info(f"📡 Evento no manejado: {event_type}")

    return {"status": "ok"}