
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.controllers.gohighlevel import buscar_contacto_por_telefono
from app.controllers.telnyx import hacer_llamada 
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class LlamadaRequest(BaseModel):
    contact_id: str

@router.post("/llamar-por-telefono")
async def llamar_por_telefono(payload: dict):
    telefono = payload.get("telefono")
    if not telefono:
        raise HTTPException(status_code=400, detail="Falta el número de teléfono")

    contacto = await buscar_contacto_por_telefono(telefono)
    if not contacto:
        raise HTTPException(status_code=404, detail="No se encontró ningún contacto con ese número")

    contact_id = contacto.get("id")
    resultado = await hacer_llamada(to_number=telefono)

    return {
        "status": "llamada iniciada",
        "contact_id": contact_id,
        "telefono": telefono,
        "detalle": resultado
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