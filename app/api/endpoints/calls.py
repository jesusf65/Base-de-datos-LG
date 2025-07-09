from fastapi import APIRouter, Request
import json

router = APIRouter()

@router.post("/webhook/lead")
async def receive_webhook(request: Request):
    payload = await request.json()

    # 👉 Extraemos los datos relevantes del payload
    first_name = payload.get("first_name")
    last_name = payload.get("last_name")
    contact_id = payload.get("contact_id")
    created_at = payload.get("date_created")
    location = payload.get("location", {})
    location_name = location.get("name")
    address = location.get("fullAddress", "")

    print("📥 Nuevo lead recibido:")
    print(f"Nombre: {first_name} {last_name}")
    print(f"ID de contacto: {contact_id}")
    print(f"Fecha de creación: {created_at}")
    print(f"Ubicación: {location_name}")
    print(f"Dirección: {address}")
    print("\nPayload completo:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    return {"status": "ok", "message": "Webhook recibido y logueado correctamente"}
