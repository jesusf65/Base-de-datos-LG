from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime, timedelta
import httpx
import uuid
from collections import defaultdict
import statistics

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('response_times.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("response_times_tracker")

router = APIRouter()

# Almacenamiento para tracking de tiempos
conversation_tracker = {
    "conversations": {},  # conversation_id -> {messages: [], timestamps: []}
    "response_times": [],  # Lista de tiempos de respuesta en segundos
    "contact_conversations": defaultdict(list),  # contact_id -> [conversation_ids]
}

async def get_raw_body(request: Request):
    return await request.body()

def calculate_response_time(conversation_messages: List[dict]) -> List[float]:
    """
    Calcula los tiempos de respuesta entre mensajes inbound y outbound
    """
    response_times = []
    
    for i in range(1, len(conversation_messages)):
        prev_msg = conversation_messages[i-1]
        current_msg = conversation_messages[i]
        
        # Solo calcular si hay cambio de dirección (inbound -> outbound o viceversa)
        if prev_msg['direction'] != current_msg['direction']:
            try:
                prev_time = datetime.fromisoformat(prev_msg['timestamp'].replace('Z', '+00:00'))
                current_time = datetime.fromisoformat(current_msg['timestamp'].replace('Z', '+00:00'))
                
                time_diff = (current_time - prev_time).total_seconds()
                
                # Solo considerar respuestas válidas (menos de 24 horas)
                if 0 < time_diff < 86400:  # 24 horas en segundos
                    response_times.append(time_diff)
                    logger.info(f"⏱️ Response time calculated: {time_diff:.2f} seconds")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not calculate response time: {e}")
    
    return response_times

def update_conversation_tracker(message_info: dict):
    """
    Actualiza el tracker de conversaciones y calcula tiempos de respuesta
    """
    contact_id = message_info['contact_id']
    conversation_id = message_info['conversation_id'] or contact_id  # Fallback to contact_id
    message_timestamp = message_info['timestamp']
    
    # Inicializar conversación si no existe
    if conversation_id not in conversation_tracker["conversations"]:
        conversation_tracker["conversations"][conversation_id] = {
            "contact_id": contact_id,
            "contact_name": message_info['contact_name'],
            "contact_phone": message_info['contact_phone'],
            "messages": [],
            "timestamps": [],
            "start_time": message_timestamp
        }
    
    # Agregar mensaje a la conversación
    conversation = conversation_tracker["conversations"][conversation_id]
    conversation["messages"].append(message_info)
    conversation["timestamps"].append(message_timestamp)
    
    # Actualizar último mensaje
    conversation["last_message"] = message_timestamp
    conversation["message_count"] = len(conversation["messages"])
    
    # Calcular tiempos de respuesta si hay al menos 2 mensajes
    if len(conversation["messages"]) >= 2:
        new_response_times = calculate_response_time(conversation["messages"])
        
        # Agregar nuevos tiempos al tracker global
        conversation_tracker["response_times"].extend(new_response_times)
        
        # Actualizar estadísticas de esta conversación
        if new_response_times:
            conversation["last_response_time"] = new_response_times[-1]
            conversation["response_times"] = conversation.get("response_times", []) + new_response_times
    
    # Mantener contacto-conversation mapping
    if conversation_id not in conversation_tracker["contact_conversations"][contact_id]:
        conversation_tracker["contact_conversations"][contact_id].append(conversation_id)
    
    # Limpiar conversaciones antiguas (más de 30 días)
    cleanup_old_conversations()

def cleanup_old_conversations(days=30):
    """
    Limpia conversaciones más antiguas que 'days' días
    """
    cutoff_time = datetime.now() - timedelta(days=days)
    conversations_to_remove = []
    
    for conv_id, conversation in conversation_tracker["conversations"].items():
        try:
            last_msg_time = datetime.fromisoformat(conversation["last_message"].replace('Z', '+00:00'))
            if last_msg_time < cutoff_time:
                conversations_to_remove.append(conv_id)
        except:
            pass
    
    for conv_id in conversations_to_remove:
        del conversation_tracker["conversations"][conv_id]
    
    if conversations_to_remove:
        logger.info(f"🧹 Cleaned up {len(conversations_to_remove)} old conversations")

def get_response_time_stats() -> Dict[str, Any]:
    """
    Calcula estadísticas de tiempos de respuesta
    """
    response_times = conversation_tracker["response_times"]
    
    if not response_times:
        return {
            "total_conversations": len(conversation_tracker["conversations"]),
            "total_messages": sum(len(conv["messages"]) for conv in conversation_tracker["conversations"].values()),
            "message": "No response times calculated yet"
        }
    
    # Convertir a minutos para estadísticas más legibles
    response_times_minutes = [rt / 60 for rt in response_times]
    
    stats = {
        "total_response_times": len(response_times),
        "average_response_minutes": round(statistics.mean(response_times_minutes), 2),
        "median_response_minutes": round(statistics.median(response_times_minutes), 2),
        "min_response_minutes": round(min(response_times_minutes), 2),
        "max_response_minutes": round(max(response_times_minutes), 2),
        "std_dev_minutes": round(statistics.stdev(response_times_minutes) if len(response_times) > 1 else 0, 2),
        "total_conversations": len(conversation_tracker["conversations"]),
        "total_messages": sum(len(conv["messages"]) for conv in conversation_tracker["conversations"].values()),
        "active_conversations_today": count_active_conversations_today()
    }
    
    # Percentiles
    if len(response_times) >= 5:
        sorted_times = sorted(response_times_minutes)
        stats.update({
            "percentile_25_minutes": round(sorted_times[int(len(sorted_times) * 0.25)], 2),
            "percentile_75_minutes": round(sorted_times[int(len(sorted_times) * 0.75)], 2),
            "percentile_90_minutes": round(sorted_times[int(len(sorted_times) * 0.90)], 2)
        })
    
    return stats

def count_active_conversations_today() -> int:
    """
    Cuenta conversaciones activas hoy
    """
    today = datetime.now().date()
    count = 0
    
    for conversation in conversation_tracker["conversations"].values():
        try:
            last_msg_time = datetime.fromisoformat(conversation["last_message"].replace('Z', '+00:00'))
            if last_msg_time.date() == today:
                count += 1
        except:
            pass
    
    return count

def extract_message_info(body: dict, direction: str) -> dict:
    """
    Extrae información del mensaje para tracking
    """
    message_id = body.get('messageId') or body.get('id') or str(uuid.uuid4())
    contact_id = body.get('contactId') or body.get('contact_id') or 'unknown'
    conversation_id = body.get('conversationId') or body.get('conversation_id') or contact_id
    
    message_content = body.get('body') or body.get('message') or body.get('text') or body.get('content') or ''
    
    channel = body.get('channel') or body.get('channelType') or 'unknown'
    provider = body.get('provider') or body.get('platform') or 'unknown'
    
    contact_name = body.get('contactName') or body.get('from') or body.get('to') or 'Unknown'
    contact_phone = body.get('contactPhone') or body.get('phone') or body.get('fromNumber') or body.get('toNumber')
    
    timestamp = body.get('timestamp') or body.get('time') or body.get('createdAt') or datetime.now().isoformat()
    
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
        "timestamp": timestamp,
        "processed_at": datetime.now().isoformat()
    }

@router.post("/webhook/messages")
async def receive_all_messages(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint universal para recibir mensajes y calcular tiempos de respuesta
    """
    try:
        client_host = request.client.host if request.client else "Unknown"
        headers = dict(request.headers)
        
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        try:
            body_content = json.loads(raw_body_text) if raw_body_text.strip() else {}
        except json.JSONDecodeError:
            body_content = {"raw_text": raw_body_text}
        
        # Detectar dirección
        direction = "inbound" if body_content.get('direction') == 'inbound' else "outbound"
        
        # Extraer información
        message_info = extract_message_info(body_content, direction)
        
        # Log del mensaje
        logger.info(f"📨 {direction.upper()} | 👤 {message_info['contact_name']} | 📞 {message_info['contact_phone']}")
        logger.info(f"💬 {message_info['content'][:100]}{'...' if len(message_info['content']) > 100 else ''}")
        
        # Actualizar tracker y calcular tiempos
        update_conversation_tracker(message_info)
        
        # Obtener estadísticas actualizadas
        stats = get_response_time_stats()
        
        response_data = {
            "status": "success",
            "message": f"{direction} message processed",
            "message_info": {
                "message_id": message_info['message_id'],
                "direction": direction,
                "contact_id": message_info['contact_id'],
                "conversation_id": message_info['conversation_id']
            },
            "response_time_stats": stats
        }
        
        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        logger.error(f"❌ Error processing message: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@router.get("/webhook/response-times/stats")
async def get_response_time_statistics():
    """
    Obtiene estadísticas completas de tiempos de respuesta
    """
    stats = get_response_time_stats()
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "statistics": stats,
        "interpretation": interpret_response_times(stats)
    }

def interpret_response_times(stats: Dict) -> Dict:
    """
    Proporciona interpretación de las estadísticas
    """
    avg_time = stats.get('average_response_minutes', 0)
    
    interpretation = {
        "performance": "Excellent" if avg_time < 5 else "Good" if avg_time < 15 else "Needs Improvement" if avg_time < 60 else "Poor",
        "sla_meeting": avg_time <= 15,  # SLA común de 15 minutos
        "recommendation": ""
    }
    
    if avg_time < 5:
        interpretation["recommendation"] = "Excellent response times! Maintain this level."
    elif avg_time < 15:
        interpretation["recommendation"] = "Good response times. Consider optimizing for under 5 minutes."
    elif avg_time < 60:
        interpretation["recommendation"] = "Response times need improvement. Focus on reducing to under 15 minutes."
    else:
        interpretation["recommendation"] = "Critical: Response times too high. Immediate action required."
    
    return interpretation

@router.get("/webhook/response-times/conversations")
async def get_conversations(
    contact_id: Optional[str] = None,
    limit: int = 10
):
    """
    Obtiene conversaciones específicas con sus tiempos de respuesta
    """
    conversations = conversation_tracker["conversations"]
    
    if contact_id:
        # Filtrar por contact_id
        conv_ids = conversation_tracker["contact_conversations"].get(contact_id, [])
        filtered_conversations = {conv_id: conversations[conv_id] for conv_id in conv_ids if conv_id in conversations}
    else:
        # Últimas conversaciones
        sorted_conv_ids = sorted(conversations.keys(), 
                               key=lambda x: conversations[x]["last_message"], 
                               reverse=True)[:limit]
        filtered_conversations = {conv_id: conversations[conv_id] for conv_id in sorted_conv_ids}
    
    # Formatear respuesta
    formatted_conversations = {}
    for conv_id, conv_data in filtered_conversations.items():
        formatted_conversations[conv_id] = {
            "contact_info": {
                "contact_id": conv_data["contact_id"],
                "contact_name": conv_data["contact_name"],
                "contact_phone": conv_data["contact_phone"]
            },
            "message_count": conv_data["message_count"],
            "last_message": conv_data["last_message"],
            "response_times_minutes": [round(rt/60, 2) for rt in conv_data.get("response_times", [])],
            "average_response_minutes": round(statistics.mean([rt/60 for rt in conv_data.get("response_times", [])]), 2) if conv_data.get("response_times") else None
        }
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "total_conversations": len(formatted_conversations),
        "conversations": formatted_conversations
    }

@router.get("/webhook/response-times/dashboard")
async def response_times_dashboard():
    """
    Dashboard completo de tiempos de respuesta
    """
    stats = get_response_time_stats()
    
    return {
        "dashboard": "📊 Response Times Dashboard",
        "timestamp": datetime.now().isoformat(),
        "key_metrics": {
            "average_response_time": f"{stats.get('average_response_minutes', 0)} minutes",
            "median_response_time": f"{stats.get('median_response_minutes', 0)} minutes",
            "sla_compliance": f"{(sum(1 for rt in conversation_tracker['response_times'] if rt <= 900) / len(conversation_tracker['response_times']) * 100) if conversation_tracker['response_times'] else 0:.1f}%" if conversation_tracker['response_times'] else "N/A",
            "active_conversations_today": stats.get('active_conversations_today', 0)
        },
        "endpoints": {
            "stats": "/webhook/response-times/stats",
            "conversations": "/webhook/response-times/conversations",
            "webhook": "POST /webhook/messages"
        }
    }

# Endpoint de compatibilidad
@router.post("/webhook/inbound")
async def backward_compatibility_inbound(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint de compatibilidad para /webhook/inbound
    """
    logger.warning("⚠️ Using deprecated endpoint /webhook/inbound")
    return await receive_all_messages(request, raw_body)