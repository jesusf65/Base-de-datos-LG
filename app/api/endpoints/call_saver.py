from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/webhooks/aircall")
async def aircall_webhook(request: Request):
    try:
        data = await request.json()
        print("📞 Webhook recibido:")
        print(data)  # Mostrar todos los datos del webhook

        return JSONResponse(
            status_code=200,
            content={"message": "✅ Webhook recibido correctamente"}
        )
    except Exception as e:
        print("❌ Error al procesar webhook:", e)
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
