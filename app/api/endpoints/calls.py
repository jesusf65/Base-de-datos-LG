
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.controllers.gohighlevel import obtener_contacto
from app.controllers.telnyx import hacer_llamada 
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class LlamadaRequest(BaseModel):
    contact_id: str

@router.post("/llamar-contacto")
async def llamar_contacto(payload: LlamadaRequest):
    contacto = await obtener_contacto(payload.contact_id)
    if not contacto:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    telefono = contacto.get("phone")
    if not telefono:
        raise HTTPException(status_code=400, detail="El contacto no tiene número")

    resultado = await hacer_llamada(to_number=telefono)
    return {
        "status": "llamada iniciada",
        "telefono": telefono,
        "detalle": resultado
    }

    
@router.get("/webhook/call/health") #Para ver si está vivo
async def health_check():

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Webhook funcionando correctamente"
    }

@router.post("/webhooks/aircall/debug", status_code=200)
async def debug_aircall_webhook(request: Request):
    try:
        original_json = await request.json()
        logger.info(f"DEBUG - Full webhook data: {original_json}")
        return {"received": original_json}
    except Exception as e:
        logger.error(f"DEBUG - Error: {str(e)}")
        return {"error": str(e)}