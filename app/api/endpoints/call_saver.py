from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import json
router = APIRouter()

@router.post("/webhooks/aircall")
async def aircall_webhook(request: Request):
    try:
        body = await request.body()
        print("🔍 Raw body:")
        print(body.decode("utf-8"))
        data = json.loads(body)

        print("✅ Webhook recibido:")
        print(data)

        return JSONResponse(
            status_code=200,
            content={"message": "Webhook recibido correctamente"}
        )
    except Exception as e:
        print("❌ Error al procesar webhook:", e)
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )