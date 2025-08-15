from fastapi import APIRouter, Request, HTTPException
import json
import http.client
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("webhook_logger")

LEADCONNECTOR_API_KEY = "Bearer pit-6cd3fee8-5d37-47e4-b2ea-0cc628ceb84f"
LEADCONNECTOR_HOST = "services.leadconnectorhq.com"
LEADCONNECTOR_VERSION = "2021-04-15"

async def get_inbound_messages(conversation_id: str):
    """Obtiene SOLO mensajes inbound de una conversación"""
    try:
        conn = http.client.HTTPSConnection(LEADCONNECTOR_HOST)
        endpoint = f"/conversations/{conversation_id}/messages?limit=50"
        headers = {
            'Accept': 'application/json',
            'Version': LEADCONNECTOR_VERSION,
            'Authorization': LEADCONNECTOR_API_KEY
        }
        
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode("utf-8")
        
        # Asegurarse de parsear correctamente el JSON
        try:
            messages_data = json.loads(response_data)
        except json.JSONDecodeError:
            logger.error(f"Respuesta no es JSON válido: {response_data}")
            return None
            
        if response.status >= 400:
            logger.error(f"Error en API: {response.status} - {messages_data.get('message')}")
            return None
        
        # Verificar estructura esperada
        if not isinstance(messages_data, dict) or 'messages' not in messages_data:
            logger.error(f"Estructura inesperada en respuesta: {messages_data}")
            return None
            
        # Filtrar SOLO mensajes inbound
        inbound_messages = [
            msg for msg in messages_data['messages']
            if isinstance(msg, dict) and msg.get("direction") == "inbound"
        ]
        
        logger.info(f"📨 Mensajes inbound encontrados: {len(inbound_messages)}")
        return inbound_messages
    
    except Exception as e:
        logger.error(f"Error al obtener mensajes: {str(e)}", exc_info=True)
        return None

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        # 1. Procesar payload
        body = await request.body()
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="JSON inválido")

        # 2. Validar contact_id
        contact_id = data.get("contact_id")
        if not contact_id:
            raise HTTPException(status_code=400, detail="contact_id es requerido")

        # 3. Obtener conversaciones
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
        
        try:
            conversations = json.loads(response_data)
        except json.JSONDecodeError:
            logger.error(f"Respuesta de conversaciones no es JSON válido: {response_data}")
            raise HTTPException(status_code=502, detail="Error en formato de respuesta")
        
        if not isinstance(conversations, dict) or not conversations.get("conversations"):
            return {
                "status": "success",
                "message": "No se encontraron conversaciones",
                "contact_id": contact_id,
                "inbound_messages": []
            }

        # 4. Procesar cada conversación
        all_inbound_messages = []
        for conv in conversations["conversations"]:
            if not isinstance(conv, dict):
                continue
                
            messages = await get_inbound_messages(conv.get("id"))
            if messages:
                all_inbound_messages.extend(messages)
        
        # 5. Ordenar mensajes por fecha (más reciente primero)
        sorted_messages = sorted(
            [msg for msg in all_inbound_messages if isinstance(msg, dict)],
            key=lambda x: x.get("dateAdded", ""),
            reverse=True
        )
        
        # 6. Formatear respuesta
        return {
            "status": "success",
            "contact_id": contact_id,
            "total_inbound_messages": len(sorted_messages),
            "inbound_messages": sorted_messages
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")