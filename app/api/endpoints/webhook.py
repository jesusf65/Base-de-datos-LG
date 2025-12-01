from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime
from collections import defaultdict

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('webhook_messages.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("message_tracker")

router = APIRouter()

# ==========================================================================================
# NUEVO: Lista global para calcular el tiempo promedio que tarda el CLIENTE en responder
# ==========================================================================================
global_client_response_times = []

# Almacenamiento organizado por conversación
conversations = defaultdict(lambda: {
    "contact_id": None,
    "contact_info": {},
    "messages": [],
    "response_times": [],
    "pending_client_message": None
})

async def get_raw_body(request: Request):
    return await request.body()

def search_nested_value(data: dict, search_keys: list) -> any:
    """Busca un valor en un diccionario, incluyendo objetos anidados"""
    for key in search_keys:
        if key in data and data[key]:
            return data[key]
    
    for key, value in data.items():
        if isinstance(value, dict):
            result = search_nested_value(value, search_keys)
            if result:
                return result
    
    return None

def parse_timestamp(ts_value) -> Optional[datetime]:
    """Convierte diferentes formatos de timestamp a datetime"""
    if not ts_value:
        return None
    
    if isinstance(ts_value, datetime):
        return ts_value
    
    ts_str = str(ts_value)
    
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except:
            continue
    
    return None

def extract_message_info(data: dict) -> dict:
    """Extrae información específica de mensajes del webhook"""
    message_info = {
        "contact_id": None,
        "message": None,
        "timestamp": None,
        "timestamp_parsed": None,
        "direction": None,
        "contact_name": None,
        "phone": None,
        "raw_data": data
    }
    
    contact_fields = ['contactId', 'contact_id', 'id', 'userId', 'user_id']
    message_info["contact_id"] = search_nested_value(data, contact_fields)
    
    message_fields = ['message', 'body', 'text', 'content', 'messageBody']
    message_info["message"] = search_nested_value(data, message_fields)
    
    timestamp_fields = ['timestamp', 'time', 'createdAt', 'date', 'dateAdded', 'date_created', 
                       'Timestamp Respuesta', 'dateCreated', 'created_at']
    raw_timestamp = search_nested_value(data, timestamp_fields)
    message_info["timestamp"] = raw_timestamp
    message_info["timestamp_parsed"] = parse_timestamp(raw_timestamp)
    
    direction_fields = ['direction', 'type', 'messageType', 'messageDirection', 'messageStatus']
    message_info["direction"] = search_nested_value(data, direction_fields)
    
    if not message_info["direction"]:
        if 'Mensajes del cliente' in data:
            message_info["direction"] = "inbound"
        elif 'mensajes salientes' in data:
            message_info["direction"] = "outbound"
        
        if 'customData' in data and isinstance(data['customData'], dict):
            custom = data['customData']
            if 'direction' in custom:
                message_info["direction"] = custom['direction']
            elif 'type' in custom:
                message_info["direction"] = custom['type']
    
    if 'full_name' in data:
        message_info["contact_name"] = data['full_name']
    elif 'first_name' in data:
        message_info["contact_name"] = data['first_name']
    
    if 'phone' in data:
        message_info["phone"] = data['phone']
    
    return message_info

def calculate_response_time(start: datetime, end: datetime) -> dict:
    """Calcula el tiempo de respuesta usando timestamps reales"""
    diff = end - start
    total_seconds = diff.total_seconds()
    
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    
    if hours > 0:
        formatted = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        formatted = f"{minutes}m {seconds}s"
    else:
        formatted = f"{seconds}s"
    
    return {
        "total_seconds": total_seconds,
        "formatted": formatted,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds
    }

@router.post("/webhook/raw")
async def receive_raw_webhook(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    try:
        timestamp_received = datetime.now()
        client_ip = request.client.host if request.client else "unknown"
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        # Parsear JSON
        parsed_body = {}
        try:
            if raw_body_text.strip():
                parsed_body = json.loads(raw_body_text)
        except json.JSONDecodeError:
            parsed_body = {"raw_text": raw_body_text}
        
        msg_info = extract_message_info(parsed_body)
        contact_id = msg_info["contact_id"]
        
        if not contact_id:
            logger.warning("⚠️  Mensaje sin contact_id - ignorado")
            return JSONResponse(content={"status": "ignored", "reason": "no_contact_id"})
        
        conv = conversations[contact_id]
        if not conv["contact_id"]:
            conv["contact_id"] = contact_id
            conv["contact_info"] = {
                "name": msg_info["contact_name"],
                "phone": msg_info["phone"]
            }
        
        direction = msg_info["direction"] or "unknown"
        direction_lower = str(direction).lower()
        
        message_entry = {
            "timestamp_received": timestamp_received.isoformat(),
            "timestamp_received_parsed": timestamp_received,
            "timestamp_message": msg_info["timestamp"],
            "timestamp_parsed": msg_info["timestamp_parsed"],
            "direction": direction,
            "message": msg_info["message"],
            "response_time": None
        }
        
        conv["messages"].append(message_entry)

        # ====================================================================================
        # MÉTODO REAL DE CÁLCULO DE TIEMPO (CON timestamp_received)
        # ====================================================================================
        response_time_info = None
        
        if direction_lower == "inbound":
            conv["pending_client_message"] = message_entry
            
            logger.info("=" * 100)
            logger.info(f"📥 MENSAJE INBOUND RECIBIDO - {timestamp_received.isoformat()}")
            logger.info("=" * 100)
        
        elif direction_lower == "outbound":
            logger.info("=" * 100)
            logger.info(f"📤 MENSAJE OUTBOUND RECIBIDO - {timestamp_received.isoformat()}")
            logger.info("=" * 100)
            
            if conv["pending_client_message"]:
                pending = conv["pending_client_message"]

                client_time = pending["timestamp_received_parsed"]
                vendor_time = timestamp_received

                response_time_info = calculate_response_time(client_time, vendor_time)
                message_entry["response_time"] = response_time_info
                conv["response_times"].append(response_time_info)

                # ==================================================================================
                # NUEVO: Guardar el tiempo en la lista global para calcular el promedio del cliente
                # ==================================================================================
                global_client_response_times.append(response_time_info["total_seconds"])
                
                logger.info("⏱️  TIEMPO DE RESPUESTA REAL:")
                logger.info(f"  ⏰ Tiempo: {response_time_info['formatted']}")
                
                conv["pending_client_message"] = None
        
        return JSONResponse(content={
            "status": "received",
            "timestamp": timestamp_received.isoformat(),
            "data": {
                "contact_id": contact_id,
                "direction": direction,
                "message": msg_info["message"],
                "response_time": response_time_info
            }
        })
        
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@router.get("/webhook/stats")
async def get_statistics():
    
    total_conversations = len(conversations)
    total_messages = sum(len(conv["messages"]) for conv in conversations.values())
    total_responses = sum(len(conv["response_times"]) for conv in conversations.values())
    
    all_response_times = []
    for conv in conversations.values():
        all_response_times.extend(conv["response_times"])
    
    global_avg = None
    if all_response_times:
        avg_seconds = sum(rt["total_seconds"] for rt in all_response_times) / len(all_response_times)
        avg_minutes = int(avg_seconds // 60)
        avg_secs = int(avg_seconds % 60)
        global_avg = {
            "total_seconds": avg_seconds,
            "formatted": f"{avg_minutes}m {avg_secs}s"
        }

    # =====================================================================================
    # NUEVO: Cálculo del tiempo promedio global de respuesta DEL CLIENTE
    # =====================================================================================
    avg_client_response = None
    if global_client_response_times:
        s = sum(global_client_response_times) / len(global_client_response_times)
        avg_client_response = f"{int(s // 60)}m {int(s % 60)}s"

    conversations_summary = []
    for contact_id, conv in conversations.items():
        conv_avg = None
        if conv["response_times"]:
            avg_sec = sum(rt["total_seconds"] for rt in conv["response_times"]) / len(conv["response_times"])
            avg_min = int(avg_sec // 60)
            avg_s = int(avg_sec % 60)
            conv_avg = f"{avg_min}m {avg_s}s"
        
        conversations_summary.append({
            "contact_id": contact_id,
            "contact_name": conv["contact_info"].get("name"),
            "phone": conv["contact_info"].get("phone"),
            "total_messages": len(conv["messages"]),
            "total_responses": len(conv["response_times"]),
            "average_response_time": conv_avg,
            "pending_response": conv["pending_client_message"] is not None
        })
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "global_stats": {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_responses_calculated": total_responses,
            "average_response_time": global_avg,
            "average_client_reply_time": avg_client_response   # 👈 NUEVO
        },
        "conversations": conversations_summary
    }

@router.get("/webhook/conversation/{contact_id}")
async def get_conversation(contact_id: str):
    if contact_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    conv = conversations[contact_id]
    
    return {
        "status": "success",
        "contact_id": contact_id,
        "contact_info": conv["contact_info"],
        "total_messages": len(conv["messages"]),
        "total_responses": len(conv["response_times"]),
        "messages": conv["messages"],
        "response_times": conv["response_times"],
        "pending_response": conv["pending_client_message"] is not None
    }

@router.get("/")
async def root():
    total_convs = len(conversations)
    total_msgs = sum(len(conv["messages"]) for conv in conversations.values())
    
    return {
        "service": "Message Response Time Tracker",
        "version": "3.1",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /webhook/raw": "Recibe mensajes y calcula tiempos de respuesta",
            "GET /webhook/stats": "Estadísticas globales",
            "GET /webhook/conversation/{contact_id}": "Detalle de conversación específica"
        },
        "current_stats": {
            "total_conversations": total_convs,
            "total_messages": total_msgs
        }
    }
