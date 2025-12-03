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

# ⚙️ CONFIGURACIÓN: Tiempo máximo permitido (en minutos)
# Solo se enviarán al webhook las respuestas que estén dentro de este tiempo
# Ejemplos: 30 (media hora), 60 (1 hora), 120 (2 horas), 300 (5 horas)
TIEMPO_MAXIMO_MINUTOS = 300

# 🔗 CONFIGURACIÓN DE SUBCUENTAS (POR LOCATION_ID)
# Cada subcuenta/ubicación tiene su LOCATION_ID único y su WEBHOOK correspondiente

# Subcuenta 1: 
LOCATION_ID_LEADGROWTH = "f1nXHhZhhRHOiU74mtmb"
WEBHOOK_LEADGROWTH = "https://services.leadconnectorhq.com/hooks/f1nXHhZhhRHOiU74mtmb/webhook-trigger/d1138875-719d-4350-92d1-be289146ee88"

# Subcuenta 2: Luxury Motors ejemplo
LOCATION_ID_LUXURY_MOTORS = "xk92jdLm4pQr8Yz"
WEBHOOK_LUXURY_MOTORS = "https://services.leadconnectorhq.com/hooks/f1nXHhZhhRHOiU74mtmb/webhook-trigger/luxury-motors-456"

# Subcuenta 3: Auto Express Ejemplo
LOCATION_ID_AUTO_EXPRESS = "vB7nWq3RtY5mKpL"
WEBHOOK_AUTO_EXPRESS = "https://services.leadconnectorhq.com/hooks/f1nXHhZhhRHOiU74mtmb/webhook-trigger/auto-express-789"

# 🔗 Webhook por defecto (si el location_id no coincide con ninguno)
WEBHOOK_DEFAULT = "https://services.leadconnectorhq.com/hooks/f1nXHhZhhRHOiU74mtmb/webhook-trigger/d1138875-719d-4350-92d1-be289146ee88"

# 📋 Mapeo automático (NO EDITAR - se genera automáticamente)
WEBHOOKS_POR_LOCATION = {
    LOCATION_ID_LEADGROWTH: WEBHOOK_LEADGROWTH,
    LOCATION_ID_LUXURY_MOTORS: WEBHOOK_LUXURY_MOTORS,
    LOCATION_ID_AUTO_EXPRESS: WEBHOOK_AUTO_EXPRESS,
}

# Variables globales para medir cuánto tarda el VENDEDOR en responder al CLIENTE
global_total_seconds = 0.0
global_response_count = 0

# Promedio por vendedor/cliente
location_stats = defaultdict(lambda: {
    "total_seconds": 0.0,
    "response_count": 0
})

# Almacenamiento organizado por conversación
conversations = defaultdict(lambda: {
    "contact_id": None,
    "contact_info": {},
    "messages": [],
    "response_times": [],
    "pending_client_message": None  # Mensaje del cliente esperando respuesta del vendedor
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

def search_nested_value(data, search_keys):
    if not isinstance(data, dict):
        return None

    for key in search_keys:
        try:
            if key in data and data[key]:
                return data[key]
        except TypeError:
            continue

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
        "location_id": None,
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
    
    # Extraer location_id
    location_fields = ['locationId', 'location_id', 'location']
    message_info["location_id"] = search_nested_value(data, location_fields)
    
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

def calculate_average(total_seconds: float, count: int) -> Optional[dict]:
    """Calcula el promedio: suma_total / cantidad"""
    if count == 0:
        return None
    
    avg_seconds = total_seconds / count
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
        "count": count
    }

def calculate_conversation_average(response_times: list) -> Optional[dict]:
    """Calcula el promedio de UNA conversación específica"""
    if not response_times:
        return None
    total = sum(rt["total_seconds"] for rt in response_times)
    return calculate_average(total, len(response_times))

@router.post("/webhook/raw")
async def receive_raw_webhook(request: Request, raw_body: bytes = Depends(get_raw_body)):
    global global_total_seconds, global_response_count
    
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

        # INBOUND = Cliente envía mensaje al vendedor
        if direction_lower == "inbound":
            conv["pending_client_message"] = message_entry
            logger.info(f"📥 MENSAJE INBOUND recibido (cliente → vendedor): {msg_info['message']}")
            logger.info(f"⏳ Esperando respuesta del vendedor...")
        
        # OUTBOUND = Vendedor responde al cliente
        elif direction_lower == "outbound":
            logger.info(f"📤 MENSAJE OUTBOUND enviado (vendedor → cliente): {msg_info['message']}")
            
            # Si hay un mensaje pendiente del cliente, calculamos cuánto tardó el vendedor en responder
            if conv["pending_client_message"]:
                pending = conv["pending_client_message"]
                client_time = pending["timestamp_received_parsed"]  # Cuando el cliente envió
                vendor_time = timestamp_received  # Cuando el vendedor respondió
                response_time_info = calculate_response_time(client_time, vendor_time)
                
                # 🔍 FILTRO: Verificar si el tiempo de respuesta está dentro del límite permitido
                tiempo_respuesta_minutos = response_time_info["total_seconds"] / 60
                
                if tiempo_respuesta_minutos > TIEMPO_MAXIMO_MINUTOS:
                    logger.warning(f"⚠️ RESPUESTA DESCARTADA: {response_time_info['formatted']} ({tiempo_respuesta_minutos:.1f} min) excede el límite de {TIEMPO_MAXIMO_MINUTOS} minutos")
                    conv["pending_client_message"] = None  # Limpiar mensaje pendiente
                    
                    return JSONResponse(content={
                        "status": "ignored",
                        "reason": "response_time_exceeded",
                        "response_time_minutes": tiempo_respuesta_minutos,
                        "max_allowed_minutes": TIEMPO_MAXIMO_MINUTOS,
                        "message": f"Tiempo de respuesta {response_time_info['formatted']} excede el límite de {TIEMPO_MAXIMO_MINUTOS} minutos"
                    })
                
                # ✅ El tiempo está dentro del límite, continuar normalmente
                logger.info(f"✅ Tiempo de respuesta válido: {response_time_info['formatted']} ({tiempo_respuesta_minutos:.1f} min)")
                
                message_entry["response_time"] = response_time_info
                conv["response_times"].append(response_time_info)
                conv["pending_client_message"] = None
                
                # Extraer location_id y datos del cliente
                location_id = msg_info.get("location_id") or parsed_body.get("location_id") or parsed_body.get("locationId") or "unknown"
                location_id = str(location_id) if location_id and not isinstance(location_id, dict) else "unknown"
                client_id = parsed_body.get("client_id") or parsed_body.get("clientId") or "unknown"
                client_name = parsed_body.get("client_name") or parsed_body.get("clientName") or msg_info.get("contact_name") or "unknown"
                
                # ACTUALIZAR LOS 3 PROMEDIOS:
                
                # 1️⃣ PROMEDIO GLOBAL (todos los chats)
                global_total_seconds += response_time_info["total_seconds"]
                global_response_count += 1
                avg_global = calculate_average(global_total_seconds, global_response_count)
                
                # 2️⃣ PROMEDIO DE ESTA CONVERSACIÓN (solo este contact_id)
                avg_conversation = calculate_conversation_average(conv["response_times"])
                
                # 3️⃣ PROMEDIO POR LOCATION (todos los chats de este location_id)
                location_stats[location_id]["total_seconds"] += response_time_info["total_seconds"]
                location_stats[location_id]["response_count"] += 1
                avg_location = calculate_average(
                    location_stats[location_id]["total_seconds"],
                    location_stats[location_id]["response_count"]
                )
                
                # LOGS DETALLADOS
                logger.info(f"⏱️ El VENDEDOR tardó en responder: {response_time_info['formatted']}")
                logger.info(f"📊 PROMEDIO GLOBAL (todos los chats): {avg_global['formatted'] if avg_global else 'N/A'}")
                logger.info(f"💬 PROMEDIO DE ESTA CONVERSACIÓN: {avg_conversation['formatted'] if avg_conversation else 'N/A'}")
                logger.info(f"📍 PROMEDIO DE LOCATION {location_id}: {avg_location['formatted'] if avg_location else 'N/A'}")
                
                # 🔗 Seleccionar el webhook correcto según el location_id
                webhook_url = WEBHOOKS_POR_LOCATION.get(location_id, WEBHOOK_DEFAULT)
                
                if location_id in WEBHOOKS_POR_LOCATION:
                    logger.info(f"🎯 Usando webhook específico para location_id '{location_id}'")
                else:
                    logger.info(f"⚠️ Location_id '{location_id}' no encontrado, usando webhook por defecto")
                
                logger.info(f"🔗 Webhook destino: {webhook_url}")
                
                # Enviar payload al webhook correspondiente
                
                payload_to_ghl = {
                    "contact_id": str(contact_id),
                    "location_id": str(location_id),
                    "client_id": str(client_id),
                    "client_name": str(client_name),
                    "outbound_message": str(message_entry["message"]) if message_entry["message"] else "",
                    "timestamp": timestamp_received.isoformat(),
                    
                    # ⭐ TIEMPO DE ESTA RESPUESTA ESPECÍFICA (en segundos)
                    "response_time_seconds": float(response_time_info["total_seconds"]),
                    "response_time_formatted": str(response_time_info["formatted"]),
                    
                    # ⭐ PROMEDIO SOLO DE ESTA CONVERSACIÓN (en segundos)
                    "conversation_average_seconds": float(avg_conversation["total_seconds"]) if avg_conversation else 0.0,
                    "conversation_average_formatted": str(avg_conversation["formatted"]) if avg_conversation else "N/A",
                    "conversation_total_responses": len(conv["response_times"]),
                    
                    # PROMEDIO GLOBAL (todos los chats juntos)
                    "global_average_seconds": float(avg_global["total_seconds"]) if avg_global else 0.0,
                    "global_average_formatted": str(avg_global["formatted"]) if avg_global else "N/A",
                    "global_total_responses": global_response_count,
                    
                    # PROMEDIO DE ESTA LOCATION (todos los chats de este location_id)
                    "location_average_seconds": float(avg_location["total_seconds"]) if avg_location else 0.0,
                    "location_average_formatted": str(avg_location["formatted"]) if avg_location else "N/A",
                    "location_total_responses": location_stats[location_id]["response_count"]
                }
                
                logger.info(f"📤 PAYLOAD A ENVIAR: {json.dumps(payload_to_ghl, indent=2, ensure_ascii=False)}")
                
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        ghl_response = await client.post(webhook_url, json=payload_to_ghl)
                        logger.info(f"✅ Webhook enviado a {webhook_url} - Status: {ghl_response.status_code}")
                        logger.info(f"📥 Respuesta del servidor: {ghl_response.text}")
                except Exception as e:
                    logger.error(f"❌ Error enviando webhook GHL: {str(e)}")
            else:
                logger.info(f"ℹ️ Vendedor envió mensaje sin haber un inbound previo pendiente")
        
        return JSONResponse(content={
            "status": "received",
            "timestamp": timestamp_received.isoformat(),
            "data": {
                "contact_id": contact_id,
                "direction": direction,
                "message": msg_info["message"],
                "vendor_response_time": response_time_info,
                "averages": {
                    "global": calculate_average(global_total_seconds, global_response_count),
                    "conversation": calculate_conversation_average(conv["response_times"]) if conv["response_times"] else None,
                    "location": calculate_average(
                        location_stats[msg_info.get("location_id", "unknown")]["total_seconds"],
                        location_stats[msg_info.get("location_id", "unknown")]["response_count"]
                    ) if msg_info.get("location_id") else None
                }
            }
        })
    
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")