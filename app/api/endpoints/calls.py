from fastapi import APIRouter, Request, HTTPException
import json
import http.client
import re
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("webhook_logger")

LEADCONNECTOR_API_KEY = "Bearer pit-6cd3fee8-5d37-47e4-b2ea-0cc628ceb84f"
LEADCONNECTOR_HOST = "services.leadconnectorhq.com"
LEADCONNECTOR_VERSION = "2021-04-15"

async def get_conversation_messages(conversation_id: str, limit: int = 10):
    """Obtiene los mensajes de una conversación específica"""
    try:
        conn = http.client.HTTPSConnection(LEADCONNECTOR_HOST)
        endpoint = f"/conversations/{conversation_id}/messages?limit={limit}"
        headers = {
            'Accept': 'application/json',
            'Version': LEADCONNECTOR_VERSION,
            'Authorization': LEADCONNECTOR_API_KEY
        }
        
        logger.info(f"📩 Obteniendo últimos {limit} mensajes para conversación: {conversation_id}")
        conn.request("GET", endpoint, headers=headers)
        
        response = conn.getresponse()
        response_data = response.read().decode("utf-8")
        
        if response.status >= 400:
            logger.error(f"❌ Error al obtener mensajes: {response.status} - {response_data}")
            return None
        
        messages_data = json.loads(response_data)
        return messages_data
    
    except Exception as e:
        logger.error(f"🔥 Error al obtener mensajes: {str(e)}", exc_info=True)
        return None

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        body = await request.body()
        data = json.loads(body)

        contact_id = data.get("contact_id")
        if not contact_id:
            raise HTTPException(status_code=400, detail="El campo contact_id es requerido")

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
        logger.info(f"🗂 Conversaciones encontradas: {json.dumps(conversations, indent=2, ensure_ascii=False)}")
        
        if not conversations.get("conversations"):
            return {
                "status": "success",
                "message": "No se encontraron conversaciones",
                "contact_id": contact_id,
                "conversations": []
            }
        
        enriched_conversations = []
        all_source_ids = set()

        for conversation in conversations["conversations"]:
            conversation_id = conversation["id"]
            messages_data = await get_conversation_messages(conversation_id)

            inbound_messages = []
            source_ids_found = []

            if messages_data and "messages" in messages_data:
                for msg in messages_data["messages"]:
                    if msg.get("direction") == "inbound":
                        inbound_messages.append(msg)

                        # Buscar sourceId en el cuerpo del mensaje
                        body = msg.get("body", "")
                        match = re.search(r"sourceId:\s*(\S+)", body)
                        if match:
                            sid = match.group(1)
                            source_ids_found.append(sid)
                            all_source_ids.add(sid)

            enriched_conversations.append({
                "conversation_id": conversation_id,
                "last_message": conversation.get("lastMessageBody"),
                "last_message_date": conversation.get("lastMessageDate"),
                "contact_name": conversation.get("contactName"),
                "phone": conversation.get("phone"),
                "messages": inbound_messages,
                "source_ids": source_ids_found
            })

        response_data = {
            "status": "success",
            "contact_id": contact_id,
            "source_ids_contact": list(all_source_ids),
            "conversations": enriched_conversations,
            "total_conversations": len(enriched_conversations),
            "message": "Chat obtenido exitosamente"
        }

        if all_source_ids:
            logger.info(f"🔍 Los SOURCE ID del contacto son: {', '.join(all_source_ids)}")
        else:
            logger.info("⚠️ No se encontró un SOURCE ID en los mensajes inbound.")

        logger.info("✅ Procesamiento completado para contact_id: %s", contact_id)
        return response_data

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Formato JSON inválido")
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
