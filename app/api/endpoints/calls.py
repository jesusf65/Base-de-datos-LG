from fastapi import APIRouter, Request, HTTPException
import json
import http.client
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("webhook_logger")

LEADCONNECTOR_API_KEY = "Bearer pit-6cd3fee8-5d37-47e4-b2ea-0cc628ceb84f"
LEADCONNECTOR_HOST = "services.leadconnectorhq.com"
LEADCONNECTOR_VERSION = "2021-04-15"

async def get_inbound_messages(conversation_id: str, limit: int = 20):  # Aumentamos el límite para asegurar encontrar inbound
    """Obtiene SOLO mensajes entrantes (inbound) de una conversación"""
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
        
        messages_data = json.loads(response_data)
        
        # Filtrar solo mensajes inbound
        inbound_messages = [
            msg for msg in messages_data.get("messages", [])
            if msg.get("direction") == "inbound"
        ]
        
        logger.info(f"📨 Mensajes inbound encontrados: {len(inbound_messages)}")
        return inbound_messages
    
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
        
        # 4. Procesar cada conversación
        results = []
        for conv in conversations.get("conversations", []):
            conversation_id = conv["id"]
            inbound_messages = await get_inbound_messages(conversation_id)
            
            if inbound_messages:  # Solo agregar conversaciones con mensajes inbound
                results.append({
                    "conversation_id": conversation_id,
                    "contact_name": conv.get("contactName", ""),
                    "phone": conv.get("phone", ""),
                    "inbound_messages": inbound_messages,
                    "total_inbound": len(inbound_messages),
                    "last_inbound": inbound_messages[0] if inbound_messages else None  # El más reciente primero
                })
        
        # 5. Preparar respuesta
        response_data = {
            "status": "success",
            "contact_id": contact_id,
            "total_conversations": len(results),
            "conversations_with_inbound": results,
            "message": "Mensajes inbound obtenidos exitosamente"
        }
        
        logger.info("✅ Procesamiento completado. Mensajes inbound encontrados: %d", 
                   sum(len(conv["inbound_messages"]) for conv in results))
        return response_data

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Formato JSON inválido")
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")