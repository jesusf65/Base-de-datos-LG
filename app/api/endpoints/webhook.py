from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('raw_webhook_data.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("raw_webhook_tracker")

router = APIRouter()
raw_data_store = []

async def get_raw_body(request: Request):
    return await request.body()

def extract_message_info(data: dict) -> dict:
    """
    Extrae información específica de mensajes del webhook
    """
    message_info = {
        "contact_id": None,
        "messages": [],
        "conversation": None,
        "timestamp": None,
        "direction": None
    }
    
    # Buscar contact_id en diferentes campos posibles
    contact_fields = ['contactId', 'contact_id', 'id', 'userId', 'user_id']
    for field in contact_fields:
        if field in data and data[field]:
            message_info["contact_id"] = data[field]
            break
    
    # Buscar timestamp
    timestamp_fields = ['timestamp', 'createdAt', 'date', 'time', 'dateAdded', 'Timestamp Respuesta']
    for field in timestamp_fields:
        if field in data and data[field]:
            message_info["timestamp"] = data[field]
            break
    
    # Buscar dirección del mensaje
    direction_fields = ['direction', 'type', 'messageType', 'messageDirection']
    for field in direction_fields:
        if field in data and data[field]:
            message_info["direction"] = data[field]
            break
    
    # Buscar el mensaje en diferentes campos
    message_fields = ['body', 'message', 'text', 'content', 'messageBody']
    for field in message_fields:
        if field in data and data[field]:
            message_info["messages"].append({
                "field_name": field,
                "content": data[field],
                "length": len(str(data[field]))
            })
    
    # Buscar conversación completa
    if 'GPT - Full Conversation' in data and data['GPT - Full Conversation']:
        message_info["conversation"] = data['GPT - Full Conversation']
    
    # Buscar arrays de mensajes
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], dict):
                # Verificar si parece ser un array de mensajes
                if any(msg_field in value[0] for msg_field in ['body', 'message', 'text', 'content']):
                    message_info["messages"].append({
                        "field_name": f"{key} (array)",
                        "content": value,
                        "count": len(value)
                    })
    
    return message_info

@router.post("/webhook/raw")
async def receive_raw_webhook(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint que captura y muestra mensajes específicamente
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        timestamp = datetime.now().isoformat()
        headers = dict(request.headers)
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        # Parsear JSON
        parsed_body = {}
        try:
            if raw_body_text.strip():
                parsed_body = json.loads(raw_body_text)
        except json.JSONDecodeError:
            parsed_body = {"raw_text": raw_body_text}
        
        # ============================================
        # MOSTRAR INFORMACIÓN DE MENSAJES
        # ============================================
        logger.info("=" * 100)
        logger.info(f"📨 MENSAJE RECIBIDO - {timestamp}")
        logger.info("=" * 100)
        
        # Extraer info de mensajes
        message_info = extract_message_info(parsed_body)
        
        # MOSTRAR: Contact ID
        logger.info(f"👤 CONTACT ID: {message_info['contact_id'] or '❌ No encontrado'}")
        
        # MOSTRAR: Timestamp
        logger.info(f"🕐 TIMESTAMP: {message_info['timestamp'] or '❌ No encontrado'}")
        
        # MOSTRAR: Dirección
        logger.info(f"📍 DIRECCIÓN: {message_info['direction'] or '❌ No encontrado'}")
        
        logger.info("-" * 100)
        
        # MOSTRAR: Mensajes encontrados
        if message_info['messages']:
            logger.info(f"💬 MENSAJES ENCONTRADOS ({len(message_info['messages'])}):")
            logger.info("")
            for idx, msg in enumerate(message_info['messages'], 1):
                logger.info(f"  Mensaje #{idx} - Campo: '{msg['field_name']}'")
                if isinstance(msg['content'], str):
                    logger.info(f"  Contenido: {msg['content']}")
                    logger.info(f"  Longitud: {msg['length']} caracteres")
                elif isinstance(msg['content'], list):
                    logger.info(f"  Tipo: Array con {msg['count']} elementos")
                    logger.info(f"  Contenido: {json.dumps(msg['content'], indent=4, ensure_ascii=False)}")
                logger.info("")
        else:
            logger.info("💬 MENSAJES: ❌ No se encontraron mensajes")
            logger.info("")
        
        # MOSTRAR: Conversación completa si existe
        if message_info['conversation']:
            logger.info("🗨️  CONVERSACIÓN COMPLETA:")
            logger.info(f"{message_info['conversation']}")
            logger.info("")
        
        logger.info("=" * 100)
        
        # Log adicional: campos disponibles
        logger.info("📋 CAMPOS DISPONIBLES EN EL WEBHOOK:")
        non_empty_fields = {k: v for k, v in parsed_body.items() if v not in ["", None, [], {}]}
        logger.info(f"Total de campos con datos: {len(non_empty_fields)}")
        logger.info("")
        for key, value in non_empty_fields.items():
            value_preview = str(value)[:100] if len(str(value)) > 100 else str(value)
            logger.info(f"  • {key}: {value_preview}")
        logger.info("")
        logger.info("=" * 100)
        
        # Almacenar
        entry = {
            "timestamp": timestamp,
            "client_ip": client_ip,
            "message_info": message_info,
            "raw_body_size": len(raw_body_text),
            "parsed_fields_count": len(parsed_body) if isinstance(parsed_body, dict) else 0
        }
        raw_data_store.append(entry)
        
        if len(raw_data_store) > 1000:
            raw_data_store.pop(0)
        
        # Respuesta
        return JSONResponse(content={
            "status": "received",
            "timestamp": timestamp,
            "message_data": {
                "contact_id": message_info["contact_id"],
                "timestamp": message_info["timestamp"],
                "direction": message_info["direction"],
                "messages_count": len(message_info["messages"]),
                "has_conversation": bool(message_info["conversation"])
            }
        }, status_code=200)
        
    except Exception as e:
        error_time = datetime.now().isoformat()
        logger.error(f"❌ ERROR - {error_time}")
        logger.error(f"Detalles: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@router.get("/webhook/raw/stats")
async def get_raw_stats():
    """Estadísticas de mensajes recibidos"""
    if not raw_data_store:
        return {
            "status": "no_data",
            "message": "No hay datos aún",
            "timestamp": datetime.now().isoformat()
        }
    
    total_requests = len(raw_data_store)
    messages_with_content = sum(1 for e in raw_data_store if e["message_info"]["messages"])
    messages_with_contact = sum(1 for e in raw_data_store if e["message_info"]["contact_id"])
    
    recent = raw_data_store[-10:]
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "total_webhooks": total_requests,
            "webhooks_with_messages": messages_with_content,
            "webhooks_with_contact_id": messages_with_contact,
            "success_rate": f"{(messages_with_content/total_requests*100):.1f}%" if total_requests > 0 else "0%"
        },
        "recent_messages": [
            {
                "timestamp": e["timestamp"],
                "contact_id": e["message_info"]["contact_id"],
                "message_count": len(e["message_info"]["messages"]),
                "direction": e["message_info"]["direction"]
            }
            for e in recent
        ]
    }

@router.get("/")
async def root():
    return {
        "service": "Message Webhook Receiver",
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /webhook/raw": "Recibe webhooks y extrae mensajes",
            "GET /webhook/raw/stats": "Estadísticas de mensajes"
        },
        "stats": {
            "total_received": len(raw_data_store),
            "last_message": raw_data_store[-1]["timestamp"] if raw_data_store else None
        }
    }