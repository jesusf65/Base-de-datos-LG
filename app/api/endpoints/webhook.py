from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime, timedelta
import re
import statistics

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('form_response_times.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("form_response_tracker")

router = APIRouter()

# Almacenamiento para métricas de formularios
form_metrics_store = {
    "submissions": [],
    "contact_metrics": {},
    "response_time_stats": []
}

async def get_raw_body(request: Request):
    return await request.body()

def extract_time_from_string(time_string: str) -> float:
    """
    Convierte strings de tiempo como "1 hora con 34 minutos" a minutos
    """
    if not time_string or not isinstance(time_string, str):
        return None
    
    time_string = time_string.lower()
    
    try:
        # Patrón para "X hora(s) con Y minuto(s)"
        pattern1 = r'(\d+)\s*hora(?:\w*)\s*con\s*(\d+)\s*minuto'
        match1 = re.search(pattern1, time_string)
        if match1:
            horas = int(match1.group(1))
            minutos = int(match1.group(2))
            return horas * 60 + minutos
        
        # Patrón para "X hora(s) Y minuto(s)"  
        pattern2 = r'(\d+)\s*hora(?:\w*)\s*(\d+)\s*minuto'
        match2 = re.search(pattern2, time_string)
        if match2:
            horas = int(match2.group(1))
            minutos = int(match2.group(2))
            return horas * 60 + minutos
        
        # Patrón para solo horas
        pattern3 = r'(\d+)\s*hora'
        match3 = re.search(pattern3, time_string)
        if match3:
            return int(match3.group(1)) * 60
        
        # Patrón para solo minutos
        pattern4 = r'(\d+)\s*minuto'
        match4 = re.search(pattern4, time_string)
        if match4:
            return int(match4.group(1))
        
        # Intentar convertir directamente si es número
        if time_string.replace('.', '').isdigit():
            return float(time_string)
            
    except Exception as e:
        logger.warning(f"⚠️ Could not parse time string: {time_string} - Error: {e}")
    
    return None

def extract_form_metrics(form_data: dict) -> Dict[str, Any]:
    """
    Extrae métricas clave del formulario de 110 campos
    """
    contact_id = form_data.get('contactId') or form_data.get('contact_id')
    contact_phone = form_data.get('contactPhone') or form_data.get('contactPhone')
    contact_name = form_data.get('contactName') or form_data.get('contactName') or 'Unknown'
    
    # Extraer tiempo de respuesta
    response_time_str = None
    response_time_minutes = None
    
    # Buscar en diferentes campos posibles de tiempo
    time_fields = [
        'Tiempo hasta primer mensaje enviado',
        'Tiempo de respuesta',
        'Response Time',
        'Wait Time',
        'Hora respuesta del vendedor'
    ]
    
    for field in time_fields:
        if field in form_data and form_data[field]:
            response_time_str = form_data[field]
            response_time_minutes = extract_time_from_string(response_time_str)
            if response_time_minutes is not None:
                break
    
    # Extraer cantidad de mensajes
    messages_sent = None
    message_fields = [
        'mensajes salientes',
        'mensajes_enviados',
        'messages_sent',
        'outbound_messages'
    ]
    
    for field in message_fields:
        if field in form_data and form_data[field]:
            try:
                messages_sent = int(form_data[field])
                break
            except:
                pass
    
    # Timestamps importantes
    first_message_time = form_data.get('Hora de primer mensaje') or form_data.get('Primer mensaje registrado')
    response_timestamp = form_data.get('Timestamp Respuesta') or form_data.get('Hora respuesta del vendedor')
    
    # Fuente del lead
    lead_source = form_data.get('Fuente del lead') or form_data.get('Canal') or 'unknown'
    
    return {
        "contact_id": contact_id,
        "contact_name": contact_name,
        "contact_phone": contact_phone,
        "response_time_string": response_time_str,
        "response_time_minutes": response_time_minutes,
        "messages_sent": messages_sent,
        "first_message_time": first_message_time,
        "response_timestamp": response_timestamp,
        "lead_source": lead_source,
        "submission_timestamp": datetime.now().isoformat(),
        "total_form_fields": len(form_data),
        "fields_with_data": sum(1 for v in form_data.values() if v and str(v).strip())
    }

def calculate_form_response_stats():
    """
    Calcula estadísticas basadas en los formularios recibidos
    """
    submissions = form_metrics_store["submissions"]
    
    if not submissions:
        return {
            "total_submissions": 0,
            "message": "No form submissions yet"
        }
    
    # Filtrar submissions con tiempos de respuesta válidos
    valid_response_times = [s for s in submissions if s['response_time_minutes'] is not None]
    response_times_minutes = [s['response_time_minutes'] for s in valid_response_times]
    
    stats = {
        "total_submissions": len(submissions),
        "submissions_with_response_times": len(valid_response_times),
        "coverage_rate": f"{(len(valid_response_times) / len(submissions) * 100):.1f}%" if submissions else "0%"
    }
    
    if response_times_minutes:
        stats.update({
            "average_response_minutes": round(statistics.mean(response_times_minutes), 2),
            "median_response_minutes": round(statistics.median(response_times_minutes), 2),
            "min_response_minutes": round(min(response_times_minutes), 2),
            "max_response_minutes": round(max(response_times_minutes), 2),
            "response_time_range": f"{min(response_times_minutes)} - {max(response_times_minutes)} minutes"
        })
        
        # Análisis de desempeño
        avg_time = stats['average_response_minutes']
        if avg_time < 5:
            stats["performance"] = "Excellent"
            stats["recommendation"] = "Outstanding response times!"
        elif avg_time < 15:
            stats["performance"] = "Good" 
            stats["recommendation"] = "Good response times. Aim for under 5 minutes."
        elif avg_time < 60:
            stats["performance"] = "Needs Improvement"
            stats["recommendation"] = "Focus on reducing response times to under 15 minutes."
        else:
            stats["performance"] = "Poor"
            stats["recommendation"] = "Immediate action required to improve response times."
    
    # Estadísticas de mensajes
    valid_message_counts = [s for s in submissions if s['messages_sent'] is not None]
    if valid_message_counts:
        message_counts = [s['messages_sent'] for s in valid_message_counts]
        stats["message_stats"] = {
            "average_messages_per_contact": round(statistics.mean(message_counts), 2),
            "total_messages_tracked": sum(message_counts),
            "contacts_with_message_data": len(valid_message_counts)
        }
    
    return stats

@router.post("/webhook/form-submission")
async def receive_form_submission(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint específico para formularios de 110 campos
    """
    try:
        client_host = request.client.host if request.client else "Unknown"
        
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        try:
            form_data = json.loads(raw_body_text) if raw_body_text.strip() else {}
        except json.JSONDecodeError:
            form_data = {"raw_text": raw_body_text}
        
        # Extraer métricas del formulario
        metrics = extract_form_metrics(form_data)
        
        # Log detallado
        logger.info("📋 FORM SUBMISSION RECEIVED")
        logger.info(f"👤 Contact: {metrics['contact_name']} | 📞 {metrics['contact_phone']}")
        logger.info(f"🆔 Contact ID: {metrics['contact_id']}")
        
        if metrics['response_time_string']:
            logger.info(f"⏱️ Response Time: {metrics['response_time_string']} → {metrics['response_time_minutes']} minutes")
        else:
            logger.warning("⚠️ No response time data found in form")
        
        if metrics['messages_sent'] is not None:
            logger.info(f"📤 Messages Sent: {metrics['messages_sent']}")
        
        logger.info(f"📊 Form Analysis: {metrics['fields_with_data']}/{metrics['total_form_fields']} fields with data")
        
        # Almacenar métricas
        form_metrics_store["submissions"].append(metrics)
        
        # Actualizar por contacto
        if metrics['contact_id'] and metrics['contact_id'] != 'unknown':
            form_metrics_store["contact_metrics"][metrics['contact_id']] = metrics
        
        # Limpiar datos antiguos (más de 30 días)
        cleanup_old_submissions()
        
        # Calcular estadísticas
        stats = calculate_form_response_stats()
        
        response_data = {
            "status": "success",
            "message": "Form submission processed for response time tracking",
            "metrics_extracted": {
                "response_time_detected": metrics['response_time_minutes'] is not None,
                "messages_detected": metrics['messages_sent'] is not None,
                "contact_identified": metrics['contact_id'] != 'unknown'
            },
            "current_stats": stats
        }
        
        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        logger.error(f"❌ Error processing form submission: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

def cleanup_old_submissions(days=30):
    """
    Limpia submissions antiguos
    """
    cutoff_time = datetime.now() - timedelta(days=days)
    submissions_to_keep = []
    
    for submission in form_metrics_store["submissions"]:
        try:
            submission_time = datetime.fromisoformat(submission['submission_timestamp'].replace('Z', '+00:00'))
            if submission_time > cutoff_time:
                submissions_to_keep.append(submission)
        except:
            submissions_to_keep.append(submission)
    
    if len(submissions_to_keep) < len(form_metrics_store["submissions"]):
        removed = len(form_metrics_store["submissions"]) - len(submissions_to_keep)
        form_metrics_store["submissions"] = submissions_to_keep
        logger.info(f"🧹 Cleaned up {removed} old form submissions")

@router.get("/webhook/response-times/dashboard")
async def form_response_dashboard():
    """
    Dashboard de tiempos de respuesta basado en formularios
    """
    stats = calculate_form_response_stats()
    
    # Últimas 5 submissions
    recent_submissions = form_metrics_store["submissions"][-5:] if form_metrics_store["submissions"] else []
    
    return {
        "dashboard": "📊 Form Response Times Dashboard",
        "timestamp": datetime.now().isoformat(),
        "overview": {
            "total_form_submissions": stats["total_submissions"],
            "submissions_with_time_data": stats.get("submissions_with_response_times", 0),
            "data_coverage_rate": stats.get("coverage_rate", "0%")
        },
        "response_time_metrics": {
            "average_minutes": stats.get("average_response_minutes", "No data"),
            "median_minutes": stats.get("median_response_minutes", "No data"),
            "performance_rating": stats.get("performance", "No data"),
            "recommendation": stats.get("recommendation", "Collect more data")
        },
        "recent_activity": {
            "last_5_submissions": [
                {
                    "contact": sub["contact_name"],
                    "phone": sub["contact_phone"],
                    "response_time": sub["response_time_string"],
                    "response_minutes": sub["response_time_minutes"],
                    "messages_sent": sub["messages_sent"]
                }
                for sub in recent_submissions
            ]
        },
        "message_metrics": stats.get("message_stats", {})
    }

@router.get("/webhook/response-times/raw-data")
async def get_raw_form_data(limit: int = 20):
    """
    Obtiene los datos crudos de formularios para análisis
    """
    submissions = form_metrics_store["submissions"][-limit:] if form_metrics_store["submissions"] else []
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "total_stored": len(form_metrics_store["submissions"]),
        "requested_limit": limit,
        "submissions": submissions
    }

# Endpoint de compatibilidad
@router.post("/webhook/inbound")
async def backward_compatibility_form(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint de compatibilidad que procesa el formulario de 110 campos
    """
    return await receive_form_submission(request, raw_body)

@router.get("/webhook/form-stats/help")
async def form_stats_help():
    """
    Ayuda para entender el sistema de tracking de formularios
    """
    return {
        "system": "Form Response Time Tracker",
        "purpose": "Track response times from 110-field form submissions",
        "key_metrics_extracted": [
            "Tiempo hasta primer mensaje enviado → Response time in minutes",
            "mensajes salientes → Outbound message count", 
            "contactId → Contact identification",
            "contactPhone → Contact phone number"
        ],
        "endpoints": {
            "primary": "POST /webhook/form-submission",
            "compatibility": "POST /webhook/inbound (legacy)",
            "dashboard": "GET /webhook/response-times/dashboard",
            "raw_data": "GET /webhook/response-times/raw-data"
        },
        "example_analysis": {
            "input": "Tiempo hasta primer mensaje enviado: '1 hora con 34 minutos'",
            "output": "94 minutes response time",
            "performance": "Needs Improvement (target: <15 minutes)"
        }
    }