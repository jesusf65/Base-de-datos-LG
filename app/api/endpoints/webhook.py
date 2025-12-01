from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime
import threading

# Configuración de logging sincronizada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('raw_webhook_data.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("raw_webhook_tracker")

# Lock para sincronizar logs
log_lock = threading.Lock()

router = APIRouter()

# Almacenamiento simple
raw_data_store = []

async def get_raw_body(request: Request):
    return await request.body()

def log_section(title: str, content: str = ""):
    """
    Función para loguear secciones de forma sincronizada
    """
    with log_lock:
        logger.info("")
        logger.info(title)
        if content:
            logger.info(content)

def log_headers(headers: dict):
    """
    Loguea headers de forma ordenada
    """
    with log_lock:
        logger.info("HEADERS:")
        for header, value in headers.items():
            logger.info(f"  {header}: {value}")

def log_json_parsed(parsed_body: dict):
    """
    Loguea JSON parseado de forma ordenada
    """
    with log_lock:
        logger.info("JSON PARSEADO:")
        logger.info(json.dumps(parsed_body, indent=2, ensure_ascii=False))

@router.post("/webhook/raw")
async def receive_raw_webhook(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint que muestra TODOS los datos crudos recibidos
    """
    try:
        # Obtener información básica
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        url_path = request.url.path
        headers = dict(request.headers)
        timestamp = datetime.now().isoformat()
        
        # Leer body crudo
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        # Intentar parsear como JSON
        parsed_body = {}
        try:
            if raw_body_text.strip():
                parsed_body = json.loads(raw_body_text)
        except json.JSONDecodeError:
            parsed_body = {"raw_text": raw_body_text}
        
        # Usar lock para toda la sección de logging
        with log_lock:
            # SEPARADOR PRINCIPAL
            logger.info("=" * 100)
            logger.info(f"WEBHOOK RECIBIDO")
            logger.info(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"IP Cliente: {client_ip}")
            logger.info(f"Método: {method}")
            logger.info(f"Endpoint: {url_path}")
            logger.info("-" * 50)
        
        # LOG 1: Headers
        log_headers(headers)
        
        # LOG 2: Body crudo
        with log_lock:
            logger.info("-" * 50)
            logger.info("BODY CRUDO (texto original):")
            logger.info(f"Tamaño: {len(raw_body_text)} bytes")
        
        if raw_body_text:
            with log_lock:
                if len(raw_body_text) > 3000:
                    logger.info("Contenido (primeros 3000 caracteres):")
                    # Dividir en líneas más pequeñas para evitar mezcla
                    chunk_size = 500
                    for i in range(0, min(3000, len(raw_body_text)), chunk_size):
                        chunk = raw_body_text[i:i+chunk_size]
                        logger.info(chunk)
                    logger.info(f"... [TRUNCADO, total: {len(raw_body_text)} caracteres]")
                else:
                    logger.info("Contenido completo:")
                    # Dividir en líneas si es muy largo
                    if len(raw_body_text) > 500:
                        chunk_size = 500
                        for i in range(0, len(raw_body_text), chunk_size):
                            chunk = raw_body_text[i:i+chunk_size]
                            logger.info(chunk)
                    else:
                        logger.info(raw_body_text)
        else:
            with log_lock:
                logger.info("[BODY VACIO]")
        
        # LOG 3: JSON parseado
        with log_lock:
            logger.info("-" * 50)
        
        if parsed_body:
            log_json_parsed(parsed_body)
        else:
            with log_lock:
                logger.info("[NO HAY CONTENIDO JSON]")
        
        # LOG 4: Análisis simple
        with log_lock:
            logger.info("-" * 50)
            logger.info("INFORMACION CLAVE EXTRAIDA:")
            
            # Buscar campos específicos
            key_fields = {
                "Contact ID": ["contactId", "contact_id", "contactId"],
                "Teléfono": ["contactPhone", "contact_phone", "phone", "Phone"],
                "Nombre": ["contactName", "contact_name", "first_name", "firstName", "full_name", "fullName"],
                "Mensajes salientes": ["mensajes salientes", "outbound_messages", "messages_sent"],
                "Tiempo respuesta": ["Tiempo hasta primer mensaje enviado", "response_time", "ResponseTime"],
                "Dirección": ["direction", "Direction", "message_type", "type"]
            }
            
            for label, field_options in key_fields.items():
                found = False
                for field in field_options:
                    if field in parsed_body and parsed_body[field]:
                        logger.info(f"  {label}: {parsed_body[field]}")
                        found = True
                        break
                if not found:
                    logger.info(f"  {label}: No encontrado")
            
            # Contar campos
            total_fields = len(parsed_body) if isinstance(parsed_body, dict) else 0
            filled_fields = sum(1 for v in parsed_body.values() if v and str(v).strip()) if isinstance(parsed_body, dict) else 0
            
            logger.info(f"  Total campos: {total_fields}")
            logger.info(f"  Campos con datos: {filled_fields}")
            logger.info(f"  Porcentaje llenado: {(filled_fields/total_fields*100 if total_fields > 0 else 0):.1f}%")
            
            logger.info("=" * 100)
            logger.info("")  # Línea en blanco para separar requests
        
        # Almacenar para histórico
        entry = {
            "timestamp": timestamp,
            "client_ip": client_ip,
            "method": method,
            "endpoint": url_path,
            "headers_count": len(headers),
            "raw_body_size": len(raw_body_text),
            "parsed_fields_count": len(parsed_body) if isinstance(parsed_body, dict) else 0,
            "contact_id": parsed_body.get('contactId') or parsed_body.get('contact_id'),
            "phone": parsed_body.get('contactPhone') or parsed_body.get('contact_phone') or parsed_body.get('phone'),
            "response_time": parsed_body.get('Tiempo hasta primer mensaje enviado'),
            "outbound_messages": parsed_body.get('mensajes salientes')
        }
        raw_data_store.append(entry)
        
        # Mantener solo últimos 1000 registros
        if len(raw_data_store) > 1000:
            raw_data_store.pop(0)
        
        # Respuesta simple
        response_data = {
            "status": "received",
            "timestamp": timestamp,
            "summary": {
                "body_size_bytes": len(raw_body_text),
                "fields_count": len(parsed_body) if isinstance(parsed_body, dict) else 0,
                "client_ip": client_ip,
                "contact_identified": bool(entry["contact_id"]),
                "has_response_time": bool(entry["response_time"]),
                "has_outbound_count": entry["outbound_messages"] is not None
            },
            "extracted_data": {
                "contact_id": entry["contact_id"],
                "phone": entry["phone"],
                "response_time": entry["response_time"],
                "outbound_messages": entry["outbound_messages"]
            }
        }
        
        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_lock:
            logger.error("=" * 100)
            logger.error(f"ERROR PROCESANDO WEBHOOK - {error_time}")
            logger.error(f"Detalle del error: {str(e)}")
            logger.error("=" * 100)
        
        raise HTTPException(
            status_code=400, 
            detail=f"Error processing webhook: {str(e)}"
        )

@router.get("/webhook/raw/stats")
async def get_raw_stats():
    """
    Obtiene estadísticas de los datos crudos recibidos
    """
    if not raw_data_store:
        return {
            "status": "no_data",
            "message": "No se han recibido webhooks aún",
            "timestamp": datetime.now().isoformat()
        }
    
    total_requests = len(raw_data_store)
    
    # Calcular estadísticas
    stats = {
        "total_requests": total_requests,
        "last_24_hours": len([r for r in raw_data_store if 
                            (datetime.now() - datetime.fromisoformat(r["timestamp"].replace('Z', '+00:00'))).total_seconds() < 86400]),
        "avg_body_size": sum(r["raw_body_size"] for r in raw_data_store) // total_requests,
        "requests_with_contact": sum(1 for r in raw_data_store if r["contact_id"]),
        "requests_with_response_time": sum(1 for r in raw_data_store if r["response_time"])
    }
    
    # Últimos 5 registros
    recent = raw_data_store[-5:] if len(raw_data_store) >= 5 else raw_data_store
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "statistics": stats,
        "recent_requests": recent
    }

@router.post("/webhook/inbound")
async def compatibility_inbound(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint de compatibilidad para /webhook/inbound
    """
    with log_lock:
        logger.info("")
        logger.info("⚠️  ENDPOINT LEGACY USADO: /webhook/inbound")
    
    return await receive_raw_webhook(request, raw_body)

@router.get("/")
async def root():
    """
    Página raíz con información simple
    """
    return {
        "service": "Receptor de Webhooks Crudos",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /webhook/raw": "Endpoint principal para recibir webhooks",
            "POST /webhook/inbound": "Endpoint legacy de compatibilidad",
            "GET /webhook/raw/stats": "Estadísticas de datos recibidos",
            "GET /": "Esta página de información"
        },
        "current_status": {
            "total_requests": len(raw_data_store),
            "service_status": "Activo"
        },
        "description": "Sistema que muestra TODOS los datos crudos recibidos sin formato especial"
    }