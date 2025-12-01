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

def search_nested_value(data: dict, search_keys: list) -> any:
    """
    Busca un valor en un diccionario, incluyendo objetos anidados
    """
    # Buscar en nivel superior
    for key in search_keys:
        if key in data and data[key]:
            return data[key]
    
    # Buscar en objetos anidados
    for key, value in data.items():
        if isinstance(value, dict):
            result = search_nested_value(value, search_keys)
            if result:
                return result
    
    return None

def extract_message_info(data: dict) -> dict:
    """
    Extrae información específica de mensajes del webhook
    """
    message_info = {
        "contact_id": None,
        "message": None,
        "timestamp": None,
        "direction": None,
        "additional_info": {}
    }
    
    # Buscar contact_id
    contact_fields = ['contactId', 'contact_id', 'id', 'userId', 'user_id']
    message_info["contact_id"] = search_nested_value(data, contact_fields)
    
    # Buscar mensaje (ahora también en objetos anidados)
    message_fields = ['message', 'body', 'text', 'content', 'messageBody']
    message_info["message"] = search_nested_value(data, message_fields)
    
    # Buscar timestamp
    timestamp_fields = ['timestamp', 'time', 'createdAt', 'date', 'dateAdded', 'date_created', 
                       'Timestamp Respuesta', 'dateCreated', 'created_at']
    message_info["timestamp"] = search_nested_value(data, timestamp_fields)
    
    # Buscar dirección del mensaje
    direction_fields = ['direction', 'type', 'messageType', 'messageDirection']
    message_info["direction"] = search_nested_value(data, direction_fields)
    
    # Información adicional útil
    if 'first_name' in data:
        message_info["additional_info"]["first_name"] = data['first_name']
    if 'full_name' in data:
        message_info["additional_info"]["full_name"] = data['full_name']
    if 'phone' in data:
        message_info["additional_info"]["phone"] = data['phone']
    if 'mensajes salientes' in data:
        message_info["additional_info"]["mensajes_salientes"] = data['mensajes salientes']
    if 'Mensajes del cliente' in data:
        message_info["additional_info"]["mensajes_cliente"] = data['Mensajes del cliente']
    
    # Buscar conversación completa
    if 'GPT - Full Conversation' in data and data['GPT - Full Conversation']:
        message_info["additional_info"]["conversation"] = data['GPT - Full Conversation']
    
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
        # EXTRAER Y MOSTRAR INFORMACIÓN DE MENSAJES
        # ============================================
        message_info = extract_message_info(parsed_body)
        
        logger.info("=" * 100)
        logger.info(f"📨 WEBHOOK RECIBIDO - {timestamp}")
        logger.info("=" * 100)
        logger.info("")
        
        # INFORMACIÓN PRINCIPAL
        logger.info("📋 INFORMACIÓN DEL MENSAJE:")
        logger.info("")
        logger.info(f"  👤 Contact ID:    {message_info['contact_id'] or '❌ No encontrado'}")
        logger.info(f"  💬 Mensaje:       {message_info['message'] or '❌ No encontrado'}")
        logger.info(f"  🕐 Timestamp:     {message_info['timestamp'] or '❌ No encontrado'}")
        logger.info(f"  📍 Dirección:     {message_info['direction'] or '❌ No encontrado'}")
        logger.info("")
        
        # INFORMACIÓN ADICIONAL
        if message_info["additional_info"]:
            logger.info("ℹ️  INFORMACIÓN ADICIONAL:")
            logger.info("")
            for key, value in message_info["additional_info"].items():
                if key != "conversation":  # La conversación la mostramos aparte
                    logger.info(f"  • {key}: {value}")
            logger.info("")
        
        # CONVERSACIÓN COMPLETA (si existe)
        if "conversation" in message_info["additional_info"]:
            logger.info("🗨️  CONVERSACIÓN COMPLETA:")
            logger.info("")
            conv = message_info["additional_info"]["conversation"]
            if len(str(conv)) > 500:
                logger.info(f"  {str(conv)[:500]}...")
                logger.info(f"  [...continúa - total: {len(str(conv))} caracteres]")
            else:
                logger.info(f"  {conv}")
            logger.info("")
        
        logger.info("=" * 100)
        logger.info("")
        
        # Almacenar
        entry = {
            "timestamp": timestamp,
            "client_ip": client_ip,
            "message_info": message_info,
            "raw_body_size": len(raw_body_text)
        }
        raw_data_store.append(entry)
        
        if len(raw_data_store) > 1000:
            raw_data_store.pop(0)
        
        # Respuesta
        return JSONResponse(content={
            "status": "received",
            "timestamp": timestamp,
            "extracted_data": {
                "contact_id": message_info["contact_id"],
                "message": message_info["message"],
                "timestamp": message_info["timestamp"],
                "direction": message_info["direction"]
            }
        }, status_code=200)
        
    except Exception as e:
        error_time = datetime.now().isoformat()
        logger.error(f"❌ ERROR - {error_time}")
        logger.error(f"Detalles: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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
    messages_with_content = sum(1 for e in raw_data_store if e["message_info"]["message"])
    messages_with_contact = sum(1 for e in raw_data_store if e["message_info"]["contact_id"])
    messages_with_timestamp = sum(1 for e in raw_data_store if e["message_info"]["timestamp"])
    
    recent = raw_data_store[-10:]
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "total_webhooks": total_requests,
            "webhooks_with_messages": messages_with_content,
            "webhooks_with_contact_id": messages_with_contact,
            "webhooks_with_timestamp": messages_with_timestamp,
            "success_rate": f"{(messages_with_content/total_requests*100):.1f}%" if total_requests > 0 else "0%"
        },
        "recent_messages": [
            {
                "timestamp": e["timestamp"],
                "contact_id": e["message_info"]["contact_id"],
                "message": e["message_info"]["message"],
                "message_timestamp": e["message_info"]["timestamp"],
                "direction": e["message_info"]["direction"]
            }
            for e in recent
        ]
    }

@router.get("/webhook/raw/last")
async def get_last_messages(limit: int = 5):
    """Obtiene los últimos N mensajes recibidos"""
    if not raw_data_store:
        return {
            "status": "no_data",
            "message": "No hay mensajes aún"
        }
    
    recent = raw_data_store[-limit:]
    
    return {
        "status": "success",
        "count": len(recent),
        "messages": [
            {
                "received_at": e["timestamp"],
                "contact_id": e["message_info"]["contact_id"],
                "message": e["message_info"]["message"],
                "message_timestamp": e["message_info"]["timestamp"],
                "direction": e["message_info"]["direction"],
                "additional_info": e["message_info"]["additional_info"]
            }
            for e in recent
        ]
    }

@router.get("/")
async def root():
    return {
        "service": "Message Webhook Receiver",
        "version": "2.1 - Fixed Nested Search",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /webhook/raw": "Recibe webhooks y extrae mensajes",
            "GET /webhook/raw/stats": "Estadísticas de mensajes",
            "GET /webhook/raw/last?limit=N": "Últimos N mensajes recibidos"
        },
        "stats": {
            "total_received": len(raw_data_store),
            "last_message_at": raw_data_store[-1]["timestamp"] if raw_data_store else None,
            "last_message": raw_data_store[-1]["message_info"]["message"] if raw_data_store else None
        }
    }