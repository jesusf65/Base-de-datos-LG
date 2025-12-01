from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime

# Configuración de logging simple y limpio
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

# Almacenamiento simple
raw_data_store = []

async def get_raw_body(request: Request):
    return await request.body()

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
        
        # LOG 1: Encabezado de la petición
        logger.info("=" * 80)
        logger.info(f"WEBHOOK RECEIVED - {timestamp}")
        logger.info(f"Client IP: {client_ip}")
        logger.info(f"Method: {method}")
        logger.info(f"Endpoint: {url_path}")
        logger.info(f"Timestamp: {timestamp}")
        logger.info("-" * 40)
        
        # LOG 2: Headers completos
        logger.info("HEADERS:")
        for header, value in headers.items():
            logger.info(f"  {header}: {value}")
        logger.info("-" * 40)
        
        # LOG 3: Body crudo (texto original)
        logger.info("RAW BODY (original text):")
        logger.info(f"  Size: {len(raw_body_text)} bytes")
        if raw_body_text:
            # Mostrar el body completo, truncado si es muy largo
            if len(raw_body_text) > 2000:
                logger.info(f"  Content (first 2000 chars):")
                logger.info(raw_body_text[:2000])
                logger.info(f"  ... [TRUNCATED, total: {len(raw_body_text)} chars]")
            else:
                logger.info(f"  Content:")
                logger.info(raw_body_text)
        else:
            logger.info("  [EMPTY BODY]")
        logger.info("-" * 40)
        
        # LOG 4: Body parseado como JSON
        logger.info("PARSED JSON BODY:")
        if parsed_body:
            logger.info(json.dumps(parsed_body, indent=2, ensure_ascii=False))
        else:
            logger.info("  [NO JSON CONTENT]")
        logger.info("-" * 40)
        
        # LOG 5: Análisis de campos
        logger.info("FIELD ANALYSIS:")
        if parsed_body and isinstance(parsed_body, dict):
            logger.info(f"  Total fields: {len(parsed_body)}")
            
            # Campos comunes a buscar
            common_fields = {
                'contact_info': ['contactId', 'contact_id', 'contactName', 'contactPhone', 'contactEmail'],
                'message_info': ['body', 'message', 'text', 'content', 'direction', 'type'],
                'timestamps': ['timestamp', 'time', 'createdAt', 'date'],
                'channel_info': ['channel', 'channelType', 'platform', 'medium', 'source']
            }
            
            for category, fields in common_fields.items():
                found = []
                for field in fields:
                    if field in parsed_body:
                        value = parsed_body[field]
                        found.append(f"{field}: {value}")
                
                if found:
                    logger.info(f"  {category}:")
                    for item in found:
                        logger.info(f"    {item}")
                else:
                    logger.info(f"  {category}: No fields found")
        else:
            logger.info("  [NO FIELDS TO ANALYZE]")
        
        logger.info("=" * 80)
        
        # Almacenar para histórico
        entry = {
            "timestamp": timestamp,
            "client_ip": client_ip,
            "method": method,
            "endpoint": url_path,
            "headers_count": len(headers),
            "raw_body_size": len(raw_body_text),
            "parsed_fields_count": len(parsed_body) if isinstance(parsed_body, dict) else 0,
            "sample_data": {
                "contact_id": parsed_body.get('contactId') or parsed_body.get('contact_id'),
                "direction": parsed_body.get('direction') or parsed_body.get('type'),
                "has_message": any(field in parsed_body for field in ['body', 'message', 'text', 'content'])
            }
        }
        raw_data_store.append(entry)
        
        # Mantener solo últimos 1000 registros
        if len(raw_data_store) > 1000:
            raw_data_store.pop(0)
        
        # Respuesta simple
        response_data = {
            "status": "received",
            "timestamp": timestamp,
            "processing": {
                "raw_body_bytes": len(raw_body_text),
                "headers_count": len(headers),
                "parsed_fields_count": len(parsed_body) if isinstance(parsed_body, dict) else 0,
                "client_ip": client_ip
            },
            "data_preview": {
                "contact_id": parsed_body.get('contactId') or parsed_body.get('contact_id'),
                "direction": parsed_body.get('direction') or parsed_body.get('type'),
                "message_preview": None
            }
        }
        
        # Agregar preview del mensaje si existe
        message_fields = ['body', 'message', 'text', 'content']
        for field in message_fields:
            if field in parsed_body and parsed_body[field]:
                response_data["data_preview"]["message_preview"] = str(parsed_body[field])[:100]
                break
        
        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        error_time = datetime.now().isoformat()
        logger.error(f"ERROR PROCESSING WEBHOOK - {error_time}")
        logger.error(f"Error details: {str(e)}")
        
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
            "message": "No webhook data received yet",
            "timestamp": datetime.now().isoformat()
        }
    
    total_requests = len(raw_data_store)
    methods_count = {}
    endpoints_count = {}
    
    for entry in raw_data_store:
        method = entry["method"]
        endpoint = entry["endpoint"]
        
        methods_count[method] = methods_count.get(method, 0) + 1
        endpoints_count[endpoint] = endpoints_count.get(endpoint, 0) + 1
    
    # Últimos 5 registros
    recent_entries = raw_data_store[-5:] if len(raw_data_store) >= 5 else raw_data_store
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "total_requests_received": total_requests,
            "methods_distribution": methods_count,
            "endpoints_distribution": endpoints_count,
            "avg_body_size": sum(e["raw_body_size"] for e in raw_data_store) // total_requests if total_requests > 0 else 0,
            "avg_fields_count": sum(e["parsed_fields_count"] for e in raw_data_store) // total_requests if total_requests > 0 else 0
        },
        "recent_activity": recent_entries
    }

@router.post("/webhook/inbound")
async def compatibility_inbound(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint de compatibilidad para /webhook/inbound
    """
    # Registrar que se usa el endpoint legacy
    logger.info("LEGACY ENDPOINT CALLED: /webhook/inbound")
    logger.info("Redirecting to /webhook/raw for processing")
    
    # Procesar igual que /webhook/raw
    return await receive_raw_webhook(request, raw_body)

@router.api_route("/webhook/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def catch_all_webhooks(
    request: Request,
    path: str,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Captura CUALQUIER webhook que llegue a /webhook/*
    """
    # Para métodos sin body, obtener body vacío
    if request.method in ["GET", "OPTIONS"]:
        raw_body = b""
        raw_body_text = ""
    else:
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
    
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    headers = dict(request.headers)
    timestamp = datetime.now().isoformat()
    
    # Log básico
    logger.info(f"CATCH-ALL WEBHOOK: {method} /webhook/{path}")
    logger.info(f"Client IP: {client_ip}")
    logger.info(f"Timestamp: {timestamp}")
    logger.info(f"Headers count: {len(headers)}")
    
    if raw_body_text:
        logger.info(f"Body size: {len(raw_body_text)} bytes")
        if len(raw_body_text) > 500:
            logger.info(f"Body preview: {raw_body_text[:500]}...")
        else:
            logger.info(f"Body content: {raw_body_text}")
    
    # Intentar parsear JSON
    parsed_body = {}
    if raw_body_text.strip():
        try:
            parsed_body = json.loads(raw_body_text)
        except:
            parsed_body = {"raw_text": raw_body_text}
    
    # Responder
    return {
        "status": "received",
        "message": f"Webhook received at /webhook/{path}",
        "method": method,
        "timestamp": timestamp,
        "client_ip": client_ip,
        "data_info": {
            "headers_count": len(headers),
            "body_size_bytes": len(raw_body_text),
            "parsed_fields_count": len(parsed_body) if isinstance(parsed_body, dict) else 0,
            "is_json": isinstance(parsed_body, dict) and parsed_body.get("raw_text") is None
        }
    }

@router.get("/")
async def root():
    """
    Página raíz con información simple
    """
    return {
        "service": "Raw Webhook Receiver",
        "description": "System to capture and display ALL raw webhook data",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /webhook/raw": "Main endpoint to receive webhooks",
            "POST /webhook/inbound": "Legacy compatibility endpoint",
            "GET /webhook/raw/stats": "Statistics of received data",
            "ANY /webhook/{path}": "Catch-all for any webhook path"
        },
        "features": {
            "raw_body_logging": "Shows complete raw body text",
            "headers_logging": "Shows all headers",
            "json_parsing": "Attempts to parse JSON bodies",
            "catch_all": "Captures any endpoint under /webhook/"
        },
        "current_stats": {
            "total_requests": len(raw_data_store),
            "last_request_time": raw_data_store[-1]["timestamp"] if raw_data_store else "None"
        }
    }