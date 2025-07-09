from fastapi import APIRouter, Request
import json

router = APIRouter()

@router.post("/webhook/lead")
async def receive_webhook(request: Request):
    payload = await request.json()
    
    print("📥 Webhook recibido:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))  # Log bonito en consola

    return {"status": "ok", "message": "Payload recibido correctamente"}