from fastapi import APIRouter, Request, HTTPException
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/telnyx", status_code=200)
async def telnyx_webhook(request: Request):
    try:
        # 1. Capturar datos en crudo y headers
        raw_body = await request.body()
        headers = dict(request.headers)
        
        # 2. Loggear información para diagnóstico
        logger.info(f"\n📝 Headers recibidos: {headers}")
        logger.info(f"\n📦 Cuerpo en crudo: {raw_body.decode('utf-8')}")

        # 3. Parsear el JSON manualmente
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error decodificando JSON: {str(e)}")
            raise HTTPException(status_code=400, detail="JSON inválido")

        # 5. Procesar el evento
        event_type = payload.get("data", {}).get("event_type")
        logger.info(f"\n🎉 Evento recibido: {event_type}")
        
        # Aquí tu lógica de negocio...
        # Ejemplo: if event_type == "call.answered": ...

        return {"status": "webhook procesado"}

    except HTTPException:
        raise  # Re-lanzar excepciones controladas
    
    except Exception as e:
        logger.error(f"🔥 Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")