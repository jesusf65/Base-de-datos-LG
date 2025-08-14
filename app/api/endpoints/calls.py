from fastapi import APIRouter, Request, HTTPException
import json
import http.client
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("webhook_logger")

LEADCONNECTOR_API_KEY = "Bearer pit-6cd3fee8-5d37-47e4-b2ea-0cc628ceb84f"
LEADCONNECTOR_HOST = "services.leadconnectorhq.com"
LEADCONNECTOR_VERSION = "2021-04-15"

async def get_conversation_messages(conversation_id: str, limit: int = 2):
    """Obtiene los mensajes de una conversación específica"""
    try:
        conn = http.client.HTTPSConnection(LEADCONNECTOR_HOST)
        endpoint = f"/conversations/{conversation_id}/messages?limit={limit}"
        headers = {
            'Accept': 'application/json',
            'Version': LEADCONNECTOR_VERSION,
            'Authorization': LEADCONNECTOR_API_KEY
        }
        
        logger.info(f"📩 Obteniendo mensajes para conversación: {conversation_id}")
        conn.request("GET", endpoint, headers=headers)
        
        response = conn.getresponse()
        response_data = response.read().decode("utf-8")
        
        if response.status >= 400:
            logger.error(f"❌ Error al obtener mensajes: {response.status} - {response_data}")
            return None
        
        return json.loads(response_data)
    
    except Exception as e:
        logger.error(f"🔥 Error al obtener mensajes: {str(e)}", exc_info=True)
        return None

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        # 1. Recibir y parsear el payload
        body = await request.body()
        data = json.loads(body)
        logger.info("📥 Payload recibido:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

        # 2. Extraer el contact_id
        contact_id = data.get("contact_id")
        if not contact_id:
            raise HTTPException(status_code=400, detail="El campo contact_id es requerido")

        # 3. Obtener conversaciones del contacto
        conn = http.client.HTTPSConnection(LEADCONNECTOR_HOST)
        endpoint = f"/conversations/search?contactId={contact_id}"
        headers = {
            'Accept': 'application/json',
            'Authorization': LEADCONNECTOR_API_KEY,
            'Version': LEADCONNECTOR_VERSION
        }
        
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode("utf-8")
        
        if response.status >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Error al consultar conversaciones: {response.status}"
            )
        
        conversations = json.loads(response_data)
        
        # 4. Verificar si hay conversaciones
        if not conversations.get("conversations"):
            return {
                "status": "success",
                "message": "No se encontraron conversaciones",
                "contact_id": contact_id,
                "messages": []
            }
        
        # 5. Obtener la primera conversación y sus mensajes
        first_conversation = conversations["conversations"][0]
        conversation_id = first_conversation["id"]
        
        messages = await get_conversation_messages(conversation_id)
        
        # 6. Preparar respuesta
        response_data = {
            "status": "success",
            "contact_id": contact_id,
            "conversation_id": conversation_id,
            "messages": messages if messages else [],
            "conversation_details": {
                "last_message": first_conversation.get("lastMessageBody"),
                "last_message_date": first_conversation.get("lastMessageDate"),
                "contact_name": first_conversation.get("contactName"),
                "phone": first_conversation.get("phone")
            }
        }
        
        logger.info("✅ Procesamiento completado para contact_id: %s", contact_id)
        return response_data

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Formato JSON inválido")
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")