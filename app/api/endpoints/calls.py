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

        # DEBUG: Loggear la respuesta RAW completa
        logger.info(f"🔍 DEBUG - Respuesta RAW completa (primeros 2000 chars): {response_data[:2000]}")
        
        # Parsear la respuesta JSON
        parsed_data = json.loads(response_data)
        
        # DEBUG: Loggear la estructura parseada
        logger.info(f"🔍 DEBUG - Respuesta parseada (estructura): {json.dumps(parsed_data, indent=2, ensure_ascii=False)[:3000]}")
        logger.info(f"🔍 DEBUG - Tipo de parsed_data: {type(parsed_data)}")
        logger.info(f"🔍 DEBUG - Keys en parsed_data: {list(parsed_data.keys()) if isinstance(parsed_data, dict) else 'No es dict'}")
        
        return parsed_data

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

            # Inicializar listas separadas por tipo de mensaje
            inbound_messages = []
            outbound_messages = []
            all_messages = []
            source_ids_found = []

            if messages_data:
                logger.info(f"📨 Estructura de messages_data: {type(messages_data)}")
                logger.info(f"📨 Keys disponibles: {list(messages_data.keys()) if isinstance(messages_data, dict) else 'No es dict'}")
                logger.info(f"📨 Contenido completo de messages_data: {json.dumps(messages_data, indent=2, ensure_ascii=False)[:2000]}")
                
                # Manejar diferentes estructuras de respuesta
                messages_list = None
                
                if isinstance(messages_data, dict):
                    # Buscar en diferentes posibles keys
                    if "messages" in messages_data:
                        # Verificar si messages_data["messages"] es dict o list
                        messages_obj = messages_data["messages"]
                        if isinstance(messages_obj, dict) and "messages" in messages_obj:
                            # Estructura anidada: messages.messages
                            messages_list = messages_obj["messages"]
                            logger.info(f"📨 Usando estructura anidada messages.messages, tipo: {type(messages_list)}, longitud: {len(messages_list) if isinstance(messages_list, list) else 'no es lista'}")
                        elif isinstance(messages_obj, list):
                            # Estructura directa: messages es una lista
                            messages_list = messages_obj
                            logger.info(f"📨 Usando 'messages' key directamente, tipo: {type(messages_list)}, longitud: {len(messages_list)}")
                        else:
                            logger.warning(f"📨 'messages' key no contiene estructura esperada. Tipo: {type(messages_obj)}")
                            messages_list = [messages_obj] if messages_obj else []
                    elif "data" in messages_data:
                        messages_list = messages_data["data"]
                        logger.info(f"📨 Usando 'data' key, tipo: {type(messages_list)}")
                    elif "conversations" in messages_data:
                        messages_list = messages_data["conversations"]
                        logger.info(f"📨 Usando 'conversations' key, tipo: {type(messages_list)}")
                    else:
                        # Listar todas las keys disponibles para debugging
                        available_keys = list(messages_data.keys())
                        logger.info(f"📨 Keys disponibles en messages_data: {available_keys}")
                        
                        # Intentar con keys que contengan 'message' en su nombre
                        message_keys = [k for k in available_keys if 'message' in k.lower()]
                        if message_keys:
                            key_to_use = message_keys[0]
                            messages_list = messages_data[key_to_use]
                            logger.info(f"📨 Usando key '{key_to_use}' que contiene 'message', tipo: {type(messages_list)}")
                        else:
                            # Si no encontramos una key conocida, crear una lista con todo el dict
                            messages_list = [messages_data]
                            logger.info(f"📨 No se encontró key de mensajes, usando todo el dict como mensaje único")
                elif isinstance(messages_data, list):
                    messages_list = messages_data
                    logger.info(f"📨 messages_data es lista directamente, longitud: {len(messages_list)}")

                if messages_list and isinstance(messages_list, list):
                    logger.info(f"📨 Total de mensajes recibidos: {len(messages_list)}")

                    # INVERTIR el orden: del más antiguo al más reciente
                    reversed_messages = list(reversed(messages_list))
                    logger.info(f"📨 Mensajes reordenados del más antiguo al más reciente")

                    # Separar mensajes en listas diferentes
                    for i, message in enumerate(reversed_messages):
                        logger.info(f"🔍 DEBUG - Mensaje {i+1}: Tipo={type(message)}")
                        
                        if isinstance(message, dict):
                            # Log de la estructura completa del mensaje para debug
                            logger.info(f"🔍 DEBUG - Keys del mensaje: {list(message.keys())}")
                            
                            body = message.get("body", "")
                            direction = message.get("direction", "")
                            msg_id = message.get("id", "sin-id")
                            
                            logger.info(f"🔍 DEBUG - ID: {msg_id}, Direction: '{direction}', Body: {body[:50]}...")
                            
                            # Agregar a la lista general
                            all_messages.append(message)
                            
                            # Separar por inbound y outbound
                            if direction == "inbound":
                                inbound_messages.append(message)
                                logger.info(f"✅ Mensaje clasificado como INBOUND")
                            elif direction == "outbound":
                                outbound_messages.append(message)
                                logger.info(f"✅ Mensaje clasificado como OUTBOUND")
                            else:
                                logger.warning(f"⚠️ Mensaje con direction desconocida: '{direction}'")
                                
                        elif isinstance(message, str):
                            logger.warning(f"⚠️ Mensaje es string: {message[:100]}...")
                            
                            # Si el string parece ser JSON, intentar parsearlo
                            try:
                                parsed_msg = json.loads(message)
                                if isinstance(parsed_msg, dict):
                                    logger.info(f"✅ String parseado exitosamente como JSON")
                                    all_messages.append(parsed_msg)
                                    
                                    direction = parsed_msg.get("direction", "")
                                    if direction == "inbound":
                                        inbound_messages.append(parsed_msg)
                                    elif direction == "outbound":
                                        outbound_messages.append(parsed_msg)
                            except json.JSONDecodeError:
                                logger.warning(f"⚠️ No se pudo parsear el string como JSON")
                        else:
                            logger.warning(f"⚠️ Mensaje con tipo desconocido: {type(message)}")

                    logger.info(f"📊 Mensajes separados - Inbound: {len(inbound_messages)}, Outbound: {len(outbound_messages)}")

                    # Procesar solo mensajes INBOUND para buscar sourceId
                    for msg in inbound_messages:
                        body = msg.get("body", "")
                        logger.info(f"🔍 Analizando mensaje inbound: {msg.get('id', 'sin-id')} - Body: {body[:100]}...")
                        
                        # Patrones específicos para capturar sourceId de ads
                        patterns = [
                            # Patrones más específicos primero
                            r"sourceId\s*:\s*\"([^\"]+)\"",        # sourceId: "valor entre comillas"
                            r"sourceId\s*:\s*'([^']+)'",          # sourceId: 'valor entre comillas simples'
                            r"sourceId\s*:\s*(\d+)",              # sourceId: 120225815911820692 (solo números)
                            r"sourceId\s*:\s*([a-zA-Z0-9_-]+)",   # sourceId: alfanumérico con _ y -
                            r"sourceId\s*:\s*([^\s\n,]+)",        # sourceId: cualquier valor sin espacios, saltos o comas
                            
                            # Variaciones con case insensitive
                            r"sourceid\s*:\s*\"([^\"]+)\"",       # sourceid: "valor" (case insensitive)
                            r"sourceid\s*:\s*'([^']+)'",          # sourceid: 'valor' (case insensitive)
                            r"sourceid\s*:\s*(\d+)",             # sourceid: números
                            r"sourceid\s*:\s*([a-zA-Z0-9_-]+)",  # sourceid: alfanumérico
                            r"sourceid\s*:\s*([^\s\n,]+)",       # sourceid: cualquier valor
                            
                            # Con underscores
                            r"source_id\s*:\s*\"([^\"]+)\"",      # source_id: "valor"
                            r"source_id\s*:\s*'([^']+)'",        # source_id: 'valor'
                            r"source_id\s*:\s*(\d+)",            # source_id: números
                            r"source_id\s*:\s*([a-zA-Z0-9_-]+)", # source_id: alfanumérico
                            r"source_id\s*:\s*([^\s\n,]+)"       # source_id: cualquier valor
                        ]
                        
                        source_id_found = None
                        matched_pattern = None
                        
                        for pattern in patterns:
                            match = re.search(pattern, body, re.IGNORECASE)
                            if match:
                                source_id_found = match.group(1).strip()
                                matched_pattern = pattern
                                logger.info(f"🎯 SOURCE ID encontrado con patrón '{pattern}': '{source_id_found}'")
                                break
                        
                        # Validar que el sourceId encontrado no esté vacío
                        if source_id_found and len(source_id_found.strip()) > 0:
                            # Limpiar el valor (remover espacios extra, etc.)
                            cleaned_source_id = source_id_found.strip()
                            
                            source_ids_found.append(cleaned_source_id)
                            all_source_ids.add(cleaned_source_id)
                            logger.info(f"✅ SourceId válido encontrado en mensaje inbound: '{cleaned_source_id}' (patrón: {matched_pattern})")
                            break
                        elif source_id_found:
                            logger.warning(f"⚠️ SourceId encontrado pero está vacío o solo espacios: '{source_id_found}'")
                    
                    # Si no encontramos sourceId en inbound, buscar también en outbound como respaldo
                    if not source_ids_found:
                        logger.info(f"🔍 No se encontró sourceId en inbound, buscando en outbound...")
                        for msg in outbound_messages:
                            body = msg.get("body", "")
                            logger.info(f"🔍 Analizando mensaje outbound: {msg.get('id', 'sin-id')} - Body: {body[:100]}...")
                            
                            patterns = [
                                # Patrones más específicos primero
                                r"sourceId\s*:\s*\"([^\"]+)\"",        # sourceId: "valor"
                                r"sourceId\s*:\s*'([^']+)'",          # sourceId: 'valor'
                                r"sourceId\s*:\s*(\d+)",              # sourceId: números
                                r"sourceId\s*:\s*([a-zA-Z0-9_-]+)",   # sourceId: alfanumérico
                                r"sourceId\s*:\s*([^\s\n,]+)",        # sourceId: cualquier valor
                                
                                # Variaciones case insensitive
                                r"sourceid\s*:\s*\"([^\"]+)\"",       # sourceid: "valor"
                                r"sourceid\s*:\s*'([^']+)'",          # sourceid: 'valor'
                                r"sourceid\s*:\s*(\d+)",             # sourceid: números
                                r"sourceid\s*:\s*([a-zA-Z0-9_-]+)",  # sourceid: alfanumérico
                                r"sourceid\s*:\s*([^\s\n,]+)",       # sourceid: cualquier valor
                                
                                # Con underscores
                                r"source_id\s*:\s*\"([^\"]+)\"",      # source_id: "valor"
                                r"source_id\s*:\s*'([^']+)'",        # source_id: 'valor'
                                r"source_id\s*:\s*(\d+)",            # source_id: números
                                r"source_id\s*:\s*([a-zA-Z0-9_-]+)", # source_id: alfanumérico
                                r"source_id\s*:\s*([^\s\n,]+)"       # source_id: cualquier valor
                            ]
                            
                            source_id_found = None
                            matched_pattern = None
                            
                            for pattern in patterns:
                                match = re.search(pattern, body, re.IGNORECASE)
                                if match:
                                    source_id_found = match.group(1).strip()
                                    matched_pattern = pattern
                                    logger.info(f"🎯 SOURCE ID encontrado en outbound con patrón '{pattern}': '{source_id_found}'")
                                    break
                            
                            # Validar que el sourceId encontrado no esté vacío
                            if source_id_found and len(source_id_found.strip()) > 0:
                                cleaned_source_id = source_id_found.strip()
                                
                                source_ids_found.append(cleaned_source_id)
                                all_source_ids.add(cleaned_source_id)
                                logger.info(f"✅ SourceId válido encontrado en mensaje outbound: '{cleaned_source_id}' (patrón: {matched_pattern})")
                                break
                            elif source_id_found:
                                logger.warning(f"⚠️ SourceId encontrado en outbound pero está vacío: '{source_id_found}'")
                else:
                    logger.warning(f"⚠️ No se pudo extraer lista de mensajes de la respuesta")

            # Tomar solo el primer sourceId encontrado (el más antiguo)
            final_source_ids = source_ids_found[:1] if source_ids_found else []

            enriched_conversations.append({
                "conversation_id": conversation_id,
                "last_message": conversation.get("lastMessageBody"),
                "last_message_date": conversation.get("lastMessageDate"),
                "contact_name": conversation.get("contactName"),
                "phone": conversation.get("phone"),
                "inbound_messages": inbound_messages,
                "outbound_messages": outbound_messages,
                "all_messages": all_messages,
                "source_ids": final_source_ids,
                "total_inbound_messages": len(inbound_messages),
                "total_outbound_messages": len(outbound_messages),
                "total_messages": len(all_messages)
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
            
            # Tomar el primer sourceId encontrado (el más antiguo)
            source_id_to_send = list(all_source_ids)[0]
            
            # Configurar la conexión para enviar el sourceId al webhook
            target_webhook_url = "https://services.leadconnectorhq.com/hooks/fwnI1qTmRiENU4TmxNZ4/webhook-trigger/5f0d133c-be2f-4d8e-928a-f6dc386fc73f"
            target_host = "services.leadconnectorhq.com"
            target_endpoint = "/hooks/fwnI1qTmRiENU4TmxNZ4/webhook-trigger/5f0d133c-be2f-4d8e-928a-f6dc386fc73f"
            
            try:
                conn = http.client.HTTPSConnection(target_host)
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Version": LEADCONNECTOR_VERSION,
                    "Authorization": LEADCONNECTOR_API_KEY
                }
                
                payload = json.dumps({
                    "sourceId": source_id_to_send
                })
                
                logger.info(f"📤 Enviando sourceId al webhook externo: {source_id_to_send}")
                conn.request("POST", target_endpoint, body=payload, headers=headers)
                
                response = conn.getresponse()
                response_data_webhook = response.read().decode("utf-8")
                
                if response.status >= 400:
                    logger.error(f"❌ Error al enviar al webhook externo: {response.status} - {response_data_webhook}")
                else:
                    logger.info(f"✅ SourceId enviado exitosamente al webhook externo. Respuesta: {response_data_webhook}")
                    
            except Exception as e:
                logger.error(f"🔥 Error al enviar al webhook externo: {str(e)}", exc_info=True)
        else:
            logger.info("⚠️ No se encontró ningún SOURCE ID en los mensajes inbound ni outbound.")

        logger.info(f"✅ Procesamiento completado para contact_id: {contact_id}")
        return response_data

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Formato JSON inválido")
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")