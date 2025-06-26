from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from app.controllers.call_save import call__save_controller

router = APIRouter()

@router.post("/webhooks/aircall")
async def aircall_webhook(request: Request):
    try:
        data = await request.json()

        call_id = data.get("id")
        contact = data.get("contact", {})
        first_name = contact.get("first_name", "Desconocido")
        last_name = contact.get("last_name", "Desconocido")
        phone = contact.get("phone_numbers", [""])[0]  # Primer número

        await call__save_controller.save_call_from_webhook(call_id, first_name, last_name, phone)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Webhook recibido y guardado"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e)}
        )