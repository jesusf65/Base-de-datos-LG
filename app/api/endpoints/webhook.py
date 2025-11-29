from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime
import httpx
import uuid

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('webhook_messages_complete.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("ghl_messages_webhook")

router = APIRouter()

# Modelos de datos
class MessageData(BaseModel):
    data: Dict[str, Any] = {}

# Almacenamiento en memoria (para demo)
message_store = {
    "inbound": [],
    "outbound": [],
    "all_messages": []
}

async def get_raw_body(request: Request):
    """Obtiene el cuerpo raw de la petición"""
    return await request.body()

def detect_message_direction(body: dict, headers: dict) -> str:
    """
    Detecta si el mensaje es inbound o outbound basado en el contenido
    """
    # Por campo específico
    if body.get('direction'):
        return body.get('direction').lower()
    
    # Por tipo de mensaje
    if body.get('type'):
        msg_type = body.get('type', '').lower()
        if 'inbound' in msg_type:
            return 'inbound'
        elif 'outbound' in msg_type:
            return 'outbound'
    
    # Por campos específicos de cada dirección
    inbound_indicators = ['inbound', 'received', 'from_customer', 'from_contact']
    outbound_indicators = ['outbound', 'sent', 'to_customer', 'to_contact', 'campaign']
    
    body_str = json.dumps(body).lower()
    
    for indicator in inbound_indicators:
        if indicator in body_str:
            return 'inbound'
    
    for indicator in outbound_indicators:
        if indicator in body_str:
            return 'outbound'
    
    # Por contenido del mensaje
    if body.get('message') and any(word in str(body.get('message')).lower() for word in ['hello', 'hi', 'help', 'question', 'interested']):
        return 'inbound'
    
    return 'unknown'

def extract_message_info(body: dict, direction: str) -> dict:
    """
    Extrae información común del mensaje
    """
    message_id = body.get('messageId') or body.get('id') or str(uuid.uuid4())
    contact_id = body.get('contactId') or body.get('contact_id')
    conversation_id = body.get('conversationId') or body.get('conversation_id')
    
    # Contenido del mensaje
    message_content = body.get('body') or body.get('message') or body.get('text') or body.get('content') or ''
    
    # Información del canal
    channel = body.get('channel') or body.get('channelType') or 'unknown'
    provider = body.get('provider') or body.get('platform') or 'unknown'
    
    # Información de contacto
    contact_name = body.get('contactName') or body.get('from') or body.get('to') or 'Unknown'
    contact_phone = body.get('contactPhone') or body.get('phone') or body.get('fromNumber') or body.get('toNumber')
    contact_email = body.get('contactEmail') or body.get('email')
    
    # Timestamps
    timestamp = body.get('timestamp') or body.get('time') or body.get('createdAt') or datetime.now().isoformat()
    
    # Estado del mensaje
    status = body.get('status') or body.get('state') or ('received' if direction == 'inbound' else 'sent')
    
    return {
        "message_id": message_id,
        "direction": direction,
        "contact_id": contact_id,
        "conversation_id": conversation_id,
        "content": message_content,
        "channel": channel,
        "provider": provider,
        "contact_name": contact_name,
        "contact_phone": contact_phone,
        "contact_email": contact_email,
        "timestamp": timestamp,
        "status": status,
        "raw_body": body
    }

def log_message_detailed(message_info: dict, headers: dict, client_host: str):
    """
    Log detallado del mensaje
    """
    direction = message_info['direction']
    direction_emoji = "📩" if direction == 'inbound' else "📤" if direction == 'outbound' else "❓"
    
    logger.info("=" * 80)
    logger.info(f"{direction_emoji} {direction.upper()} MESSAGE DETECTED")
    logger.info("=" * 80)
    
    logger.info("👤 CONTACT INFO:")
    logger.info(f"   • Name: {message_info['contact_name']}")
    logger.info(f"   • Phone: {message_info['contact_phone']}")
    logger.info(f"   • Email: {message_info['contact_email']}")
    logger.info(f"   • Contact ID: {message_info['contact_id']}")
    
    logger.info("📱 CHANNEL INFO:")
    logger.info(f"   • Channel: {message_info['channel']}")
    logger.info(f"   • Provider: {message_info['provider']}")
    logger.info(f"   • Conversation ID: {message_info['conversation_id']}")
    
    logger.info("💬 MESSAGE CONTENT:")
    content = message_info['content']
    if len(content) > 300:
        logger.info(f"   {content[:300]}... [TRUNCATED - TOTAL: {len(content)} chars]")
    else:
        logger.info(f"   {content}")
    
    logger.info("📊 MESSAGE METADATA:")
    logger.info(f"   • Message ID: {message_info['message_id']}")
    logger.info(f"   • Direction: {message_info['direction']}")
    logger.info(f"   • Status: {message_info['status']}")
    logger.info(f"   • Timestamp: {message_info['timestamp']}")
    logger.info(f"   • Client IP: {client_host}")
    
    # Headers importantes
    logger.info("🌐 NETWORK INFO:")
    important_headers = ['user-agent', 'content-type', 'x-forwarded-for', 'x-real-ip']
    for header in important_headers:
        if header in headers:
            logger.info(f"   • {header}: {headers[header]}")

@router.post("/webhook/messages")
async def receive_all_messages(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint universal para recibir TODOS los tipos de mensajes (inbound y outbound)
    """
    try:
        # Obtener información básica
        client_host = request.client.host if request.client else "Unknown"
        headers = dict(request.headers)
        
        # Procesar body
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        try:
            body_content = json.loads(raw_body_text) if raw_body_text.strip() else {}
        except json.JSONDecodeError:
            body_content = {"raw_text": raw_body_text}
        
        # Detectar dirección del mensaje
        direction = detect_message_direction(body_content, headers)
        
        # Extraer información del mensaje
        message_info = extract_message_info(body_content, direction)
        
        # Log detallado
        log_message_detailed(message_info, headers, client_host)
        
        # Almacenar en memoria
        message_store[direction].append(message_info)
        message_store["all_messages"].append(message_info)
        
        # Limitar almacenamiento a últimos 1000 mensajes por categoría
        for key in ['inbound', 'outbound', 'all_messages']:
            if len(message_store[key]) > 1000:
                message_store[key] = message_store[key][-1000:]
        
        # Respuesta
        response_data = {
            "status": "success",
            "message": f"{direction} message processed successfully",
            "message_info": {
                "message_id": message_info['message_id'],
                "direction": direction,
                "contact_id": message_info['contact_id'],
                "contact_name": message_info['contact_name'],
                "channel": message_info['channel'],
                "timestamp": datetime.now().isoformat()
            },
            "storage": {
                "total_messages": len(message_store["all_messages"]),
                "inbound_count": len(message_store["inbound"]),
                "outbound_count": len(message_store["outbound"])
            }
        }
        
        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        error_time = datetime.now().isoformat()
        logger.error(f"❌ Error processing message | 🕒 {error_time} | Error: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Error processing message: {str(e)}"
        )

@router.post("/webhook/messages/inbound")
async def receive_inbound_messages(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint específico para mensajes INBOUND (entrantes)
    """
    return await process_specific_direction(request, raw_body, "inbound")

@router.post("/webhook/messages/outbound")
async def receive_outbound_messages(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint específico para mensajes OUTBOUND (salientes)
    """
    return await process_specific_direction(request, raw_body, "outbound")

async def process_specific_direction(request: Request, raw_body: bytes, direction: str):
    """
    Procesa mensajes de una dirección específica
    """
    try:
        client_host = request.client.host if request.client else "Unknown"
        headers = dict(request.headers)
        
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        try:
            body_content = json.loads(raw_body_text) if raw_body_text.strip() else {}
        except json.JSONDecodeError:
            body_content = {"raw_text": raw_body_text}
        
        # Forzar dirección
        message_info = extract_message_info(body_content, direction)
        
        # Log detallado
        log_message_detailed(message_info, headers, client_host)
        
        # Almacenar
        message_store[direction].append(message_info)
        message_store["all_messages"].append(message_info)
        
        # Limitar almacenamiento
        for key in [direction, "all_messages"]:
            if len(message_store[key]) > 1000:
                message_store[key] = message_store[key][-1000:]
        
        response_data = {
            "status": "success",
            "message": f"{direction} message processed successfully",
            "message_info": {
                "message_id": message_info['message_id'],
                "direction": direction,
                "contact_id": message_info['contact_id'],
                "contact_name": message_info['contact_name'],
                "content_preview": message_info['content'][:100] + "..." if len(message_info['content']) > 100 else message_info['content'],
                "channel": message_info['channel'],
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        error_time = datetime.now().isoformat()
        logger.error(f"❌ Error processing {direction} message | 🕒 {error_time} | Error: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Error processing {direction} message: {str(e)}"
        )

@router.get("/webhook/messages/stats")
async def get_message_stats():
    """
    Obtiene estadísticas de los mensajes recibidos
    """
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "total_messages": len(message_store["all_messages"]),
            "inbound_messages": len(message_store["inbound"]),
            "outbound_messages": len(message_store["outbound"]),
            "unknown_messages": len([m for m in message_store["all_messages"] if m['direction'] == 'unknown'])
        },
        "recent_messages": {
            "last_5_inbound": message_store["inbound"][-5:] if message_store["inbound"] else [],
            "last_5_outbound": message_store["outbound"][-5:] if message_store["outbound"] else []
        }
    }

@router.get("/webhook/messages/all")
async def get_all_messages(
    direction: Optional[str] = None,
    limit: int = 50
):
    """
    Obtiene todos los mensajes almacenados, filtrables por dirección
    """
    if direction and direction in ['inbound', 'outbound']:
        messages = message_store[direction][-limit:]
    else:
        messages = message_store["all_messages"][-limit:]
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "filters": {
            "direction": direction,
            "limit": limit
        },
        "total_returned": len(messages),
        "messages": messages
    }

@router.get("/webhook/messages/debug")
async def debug_messages():
    """
    Dashboard de debug para mensajes
    """
    return {
        "message": "📨 GHL Messages Webhook Debug Dashboard",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "universal": "POST /webhook/messages - Recibe inbound y outbound automáticamente",
            "inbound_only": "POST /webhook/messages/inbound - Solo mensajes entrantes",
            "outbound_only": "POST /webhook/messages/outbound - Solo mensajes salientes",
            "stats": "GET /webhook/messages/stats - Estadísticas",
            "all_messages": "GET /webhook/messages/all - Ver mensajes almacenados"
        },
        "current_storage": {
            "total_messages": len(message_store["all_messages"]),
            "inbound": len(message_store["inbound"]),
            "outbound": len(message_store["outbound"])
        },
        "features": {
            "auto_detection": "Sí",
            "detailed_logging": "Sí", 
            "in_memory_storage": "Sí (últimos 1000 mensajes)",
            "channel_support": "SMS, WhatsApp, Email, Messenger, etc."
        }
    }