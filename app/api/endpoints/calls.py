from fastapi import APIRouter, Request, HTTPException
import json
import http.client
from app.utils.logger import setup_logger
from datetime import datetime, timedelta
import jwt  # pip install pyjwt

router = APIRouter()
logger = setup_logger("webhook_logger")

# Configuración
LOCATION_ID = "fwnI1qTmRiENU4TmxNZ4"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2NhdGlvbl9pZCI6ImZ3bkkxcVRtUmlFTlU0VG14Tlo0IiwidmVyc2lvbiI6MSwiaWF0IjoxNzM5ODkzMzcwNzIzLCJzdWIiOiJyTjlhazB3czJ1YWJUa2tQQllVYiJ9._ES_ynLDP_VKOXvFfNvPgazpdzxxZu41pMkNMDHeCEY"  # Reemplaza con tu API Key real
LEADCONNECTOR_HOST = "services.leadconnectorhq.com"
LEADCONNECTOR_VERSION = "2021-04-15"

def generate_jwt_token():
    """Genera un nuevo JWT token válido"""
    payload = {
        "location_id": LOCATION_ID,
        "version": 1,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=55),  # 55 minutos de validez
        "sub": API_KEY
    }
    return jwt.encode(payload, API_KEY, algorithm="HS256")

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        # 1. Recibir y parsear el payload
        body = await request.body()
        data = json.loads(body)
        
        # 2. Extraer el contact_id
        contact_id = data.get("contact_id")
        if not contact_id:
            raise HTTPException(status_code=400, detail="contact_id es requerido")

        # 3. Generar nuevo token JWT
        token = generate_jwt_token()
        headers = {
            'Accept': 'application/json',
            'Authorization': f"Bearer {token}",
            'Version': LEADCONNECTOR_VERSION
        }

        # 4. Realizar petición
        conn = http.client.HTTPSConnection(LEADCONNECTOR_HOST)
        endpoint = f"/conversations/search?contactId={contact_id}"
        conn.request("GET", endpoint, headers=headers)
        
        response = conn.getresponse()
        response_data = json.loads(response.read().decode("utf-8"))

        if response.status >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Error en LeadConnector: {response_data.get('message')}"
            )
        
        return {
            "status": "success",
            "contact_id": contact_id,
            "conversations": response_data
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))