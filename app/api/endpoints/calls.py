from fastapi import APIRouter, Request, HTTPException
import json
import http.client
import re
from app.utils.logger import setup_logger

# Configuración de router y logger
router = APIRouter()
logger = setup_logger("webhook_logger")

# Configuración LeadConnector
LEADCONNECTOR_API_KEY = "Bearer pit-6cd3fee8-5d37-47e4-b2ea-0cc628ceb84f"
LEADCONNECTOR_HOST = "services.leadconnectorhq.com"
LEADCONNECTOR_VERSION = "2021-04-15"


async def get_conversation_messages(conversation_id: str, limit: int = 10):
    """
    Obtiene los mensajes de una conversación específica desde LeadConnector.
    """
    try:
        conn = http.client.HTTPSConnection(LEADCONNECTOR_HOST)
        endpoint = f"/conversations/{conversation_id}/messages?limit={limit}"
        headers = {
            "Accept": "application/json",
            "Version": LEADCONNECTOR_VERSION,
            "Authorization": LEADCONNECTOR_API_KEY
        }

        logger.info(f"📩 Obteniendo últimos {limit} mensajes para conversación: {conversation_id}")
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
    """
    Webhook que recibe un contact_id, obtiene todas sus conversaciones,
    analiza los mensajes inbound y extrae los sourceId encontrados.
    """
    try:
        body = await request.body()
        data = json.loads(body)

        contact_id = data.get("contact_id")
        if not contact_id:
            raise HTTPException(status_code=400, detail="El campo contact_id es requerido")

        # Obtener las conversaciones de este contacto
        conn = http.client.HTTPSConnection(LEADCONNECTOR_HOST)
        endpoint = f"/conversations/search?contactId={contact_id}"
        headers = {
            "Accept": "application/json",
            "Authorization": LEADCONNECTOR_API_KEY,
            "Version": LEADCONNECTOR_VERSION
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
                logger.info(f"📨 Estructura de mensajes recibida: {json.dumps(messages_data['messages'], indent=2, ensure_ascii=False)}")

                for msg in messages_data["messages"]:
                    if isinstance(msg, dict) and msg.get("direction") == "inbound":
                        inbound_messages.append(msg)
                        body = msg.get("body", "")
                        
                        logger.info(f"🔍 Analizando mensaje inbound: {msg.get('id', 'sin-id')} - Body: {body[:100]}...")
                        
                        patterns = [
                            r"sourceId\s*:\s*(\S+)",           # sourceId: valor
                            r"sourceid\s*:\s*(\S+)",          # sourceid: valor (case insensitive)
                            r"source_id\s*:\s*(\S+)",         # source_id: valor
                        ]
                        
                        source_id_found = None
                        for pattern in patterns:
                            match = re.search(pattern, body, re.IGNORECASE)
                            if match:
                                source_id_found = match.group(1)
                                logger.info(f"🎯 SOURCE ID encontrado con patrón '{pattern}': {source_id_found}")
                                break
                        
                        if source_id_found:
                            source_ids_found.append(source_id_found)
                            all_source_ids.add(source_id_found)
                            # No hacer break aquí - seguir procesando para encontrar todos
                    
                    # Caso: mensaje es texto plano (por si acaso)
                    elif isinstance(msg, str):
                        logger.info(f"🔍 Mensaje en formato string: {msg[:100]}...")
                        patterns = [
                            r"sourceId\s*:\s*(\S+)",
                            r"sourceid\s*:\s*(\S+)",
                            r"source_id\s*:\s*(\S+)",
                        ]
                        
                        source_id_found = None
                        for pattern in patterns:
                            match = re.search(pattern, msg, re.IGNORECASE)
                            if match:
                                source_id_found = match.group(1)
                                logger.info(f"🎯 SOURCE ID encontrado en string: {source_id_found}")
                                break
                        
                        if source_id_found:
                            source_ids_found.append(source_id_found)
                            all_source_ids.add(source_id_found)

            # Si encontramos múltiples sourceIds, tomar el último (más antiguo)
            final_source_ids = source_ids_found[-1:] if source_ids_found else []

            enriched_conversations.append({
                "conversation_id": conversation_id,
                "last_message": conversation.get("lastMessageBody"),
                "last_message_date": conversation.get("lastMessageDate"),
                "contact_name": conversation.get("contactName"),
                "phone": conversation.get("phone"),
                "messages": inbound_messages,
                "source_ids": final_source_ids,
                "total_inbound_messages": len(inbound_messages)
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
            logger.info(f"🔍 SOURCE ID(s) del contacto encontrado(s): {', '.join(all_source_ids)}")
        else:
            logger.info("⚠️ No se encontró ningún SOURCE ID en los mensajes inbound.")

        logger.info(f"✅ Procesamiento completado para contact_id: {contact_id}")
        return response_data

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Formato JSON inválido")
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")