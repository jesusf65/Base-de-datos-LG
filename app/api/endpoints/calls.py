from fastapi import APIRouter, Request
import json
import datetime
from app.controllers.parse import parse_lead_payload
from app.controllers.archive import build_adf_xml
from app.controllers.email import send_lead_to_multiple_recipients

router = APIRouter()

@router.post("/webhook/lead")
async def receive_webhook(request: Request):
    payload = await request.json()
    print("📥 Webhook recibido:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if "date_created" not in payload:
        payload["date_created"] = datetime.datetime.utcnow().isoformat()

    lead_data = parse_lead_payload(payload)
    adf_xml = build_adf_xml(lead_data)
    await send_lead_to_multiple_recipients(adf_xml)

    print("📨 Lead enviado por correo exitosamment")
    return {"status": "ok", "message": "Lead enviado correctamente a todos los destinatarios"}