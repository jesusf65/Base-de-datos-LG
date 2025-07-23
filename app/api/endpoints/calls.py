from fastapi import APIRouter, Request, HTTPException
from datetime import datetime 
import logging

router = APIRouter()

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@router.api_route("/webhook/call", methods=["GET", "POST"])
async def log_facebook_webhook(request: Request):
    """
    Endpoint simple para loggear todo lo que envía Facebook
    """
    try:
        # Obtener método HTTP
        method = request.method
        
        # Obtener headers
        headers = dict(request.headers)
        
        # Obtener parámetros de query (para GET)
        query_params = dict(request.query_params)
        
        # Obtener body (para POST)
        body = await request.body()
        
        # Intentar parsear JSON si existe
        try:
            json_data = await request.json() if body else None
        except:
            json_data = None
        
        # Loggear toda la información recibida
        logger.info(f"\n{'='*40}\n"
                   f"Método: {method}\n"
                   f"Headers: {headers}\n"
                   f"Query Params: {query_params}\n"
                   f"Body (raw): {body}\n"
                   f"Body (JSON): {json_data}\n"
                   f"{'='*40}")
        
        # Si es una solicitud GET de verificación
        if method == "GET" and "hub.mode" in query_params:
            verify_token = "fb_wh_verify_7Xq9!pL2$zR#mY4v"  # Cambiar por tu token real
            if query_params.get("hub.verify_token") == verify_token:
                challenge = query_params.get("hub.challenge", "")
                return PlainTextResponse(content=challenge)
            else:
                raise HTTPException(status_code=403, detail="Token de verificación incorrecto")
        
        # Para solicitudes POST, simplemente responder OK
        return JSONResponse(content={"status": "received"})
    
    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
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