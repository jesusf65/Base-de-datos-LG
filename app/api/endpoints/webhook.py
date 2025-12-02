from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import json
from datetime import datetime
from collections import defaultdict
import httpx

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

# Lista global para calcular el tiempo promedio que tarda el CLIENTE en responder
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

def parse_timestamp(ts_value) -> Optional[datetime]:
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

def search_nested_value(data: dict, search_keys: list):
    for key in search_keys:
        if key in data and data[key]:
            return data[key]
    for key, value in data.items():
        if isinstance(value, dict):
            result = search_nested_value(value, search_keys)
            if result:
                return result
    return None

def extract_message_info(data: dict) -> dict:
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
    
    timestamp_fields = ['timestamp', 'time', 'createdAt', 'date', 'dateAdded', 'date_created', 'dateCreated', 'created_at']
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

def calculate_average_time(times_list: list) -> Optional[dict]:
    """Calcula el tiempo promedio de una lista de segundos"""
    if not times_list:
        return None
    avg_seconds = sum(times_list) / len(times_list)
    hours = int(avg_seconds // 3600)
    minutes = int((avg_seconds % 3600) // 60)
    seconds = int(avg_seconds % 60)
    if hours > 0:
        formatted = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        formatted = f"{minutes}m {seconds}s"
    else:
        formatted = f"{seconds}s"
    return {
        "total_seconds": avg_seconds,
        "formatted": formatted,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "count": len(times_list)
    }

@router.post("/webhook/raw")
async def receive_raw_webhook(request: Request, raw_body: bytes = Depends(get_raw_body)):
    try:
        timestamp_received = datetime.now()
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        parsed_body = {}
        try:
            if raw_body_text.strip():
                parsed_body = json.loads(raw_body_text)
        except json.JSONDecodeError:
            parsed_body = {"raw_text": raw_body_text}
        
        logger.info(f"📦 Body recibido: {json.dumps(parsed_body, indent=2, ensure_ascii=False)}")
        
        msg_info = extract_message_info(parsed_body)
        contact_id = msg_info["contact_id"]
        if not contact_id:
            logger.warning("⚠️ Mensaje sin contact_id - ignorado")
            return JSONResponse(content={"status": "ignored", "reason": "no_contact_id"})
        
        conv = conversations[contact_id]
        if not conv["contact_id"]:
            conv["contact_id"] = contact_id
            conv["contact_info"] = {"name": msg_info["contact_name"], "phone": msg_info["phone"]}
        
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
        response_time_info = None

        if direction_lower == "inbound":
            conv["pending_client_message"] = message_entry
            logger.info(f"📥 MENSAJE INBOUND recibido: {msg_info['message']}")
        
        elif direction_lower == "outbound":
            logger.info(f"📤 MENSAJE OUTBOUND recibido: {msg_info['message']}")
            
            if conv["pending_client_message"]:
                pending = conv["pending_client_message"]
                client_time = pending["timestamp_received_parsed"]
                vendor_time = timestamp_received
                response_time_info = calculate_response_time(client_time, vendor_time)
                
                message_entry["response_time"] = response_time_info
                conv["response_times"].append(response_time_info)
                global_client_response_times.append(response_time_info["total_seconds"])
                conv["pending_client_message"] = None
                
                logger.info(f"⏱️ Tiempo de respuesta individual: {response_time_info['formatted']}")
                
                # Calcular promedio global actualizado
                avg_time = calculate_average_time(global_client_response_times)
                
                # Extraer client_id y client_name
                client_id = parsed_body.get("client_id") or parsed_body.get("clientId") or "unknown"
                client_name = parsed_body.get("client_name") or parsed_body.get("clientName") or msg_info.get("contact_name") or "unknown"
                
                # Enviar payload al webhook de GHL
                ghl_webhook_url = "https://services.leadconnectorhq.com/hooks/f1nXHhZhhRHOiU74mtmb/webhook-trigger/d1138875-719d-4350-92d1-be289146ee88"
                
                payload_to_ghl = {
                    "contact_id": str(contact_id),
                    "client_id": str(client_id),
                    "client_name": str(client_name),
                    "outbound_message": str(message_entry["message"]) if message_entry["message"] else "",
                    "timestamp": timestamp_received.isoformat(),
                    "current_response_time_seconds": float(response_time_info["total_seconds"]),
                    "current_response_time_formatted": str(response_time_info["formatted"]),
                    "average_response_time_seconds": float(avg_time["total_seconds"]) if avg_time else 0.0,
                    "average_response_time_formatted": str(avg_time["formatted"]) if avg_time else "N/A",
                    "total_responses_counted": len(global_client_response_times)
                }
                
                logger.info(f"📤 PAYLOAD A ENVIAR: {json.dumps(payload_to_ghl, indent=2, ensure_ascii=False)}")
                
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        ghl_response = await client.post(ghl_webhook_url, json=payload_to_ghl)
                        logger.info(f"✅ Webhook GHL enviado - Status: {ghl_response.status_code}")
                        logger.info(f"📥 Respuesta del servidor: {ghl_response.text}")
                except Exception as e:
                    logger.error(f"❌ Error enviando webhook GHL: {str(e)}")
        
        return JSONResponse(content={
            "status": "received",
            "timestamp": timestamp_received.isoformat(),
            "data": {
                "contact_id": contact_id,
                "direction": direction,
                "message": msg_info["message"],
                "response_time": response_time_info,
                "average_time": calculate_average_time(global_client_response_times)
            }
        })
    
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
