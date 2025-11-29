from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime
import httpx

# Configuración de logging más detallada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('webhook_inbound_complete.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("ghl_inbound_webhook_complete")

router = APIRouter()

class WebhookData(BaseModel):
    data: Dict[str, Any] = {}

async def get_raw_body(request: Request):
    """Obtiene el cuerpo raw de la petición"""
    return await request.body()

def log_complete_request(headers: dict, body: dict, raw_body: str, client_host: str):
    """
    Función para loguear COMPLETAMENTE todo lo que llega al webhook
    """
    logger.info("=" * 80)
    logger.info("📥 INBOUND WEBHOOK - COMPLETE REQUEST DATA")
    logger.info("=" * 80)
    
    # 1. Información básica de la petición
    logger.info("🔍 BASIC REQUEST INFO:")
    logger.info(f"   • Client IP: {client_host}")
    logger.info(f"   • Timestamp: {datetime.now().isoformat()}")
    logger.info(f"   • Headers Count: {len(headers)}")
    logger.info(f"   • Body Fields Count: {len(body) if body else 0}")
    
    # 2. Headers COMPLETOS
    logger.info("📋 ALL HEADERS:")
    for header, value in headers.items():
        # Ocultar valores sensibles de autorización
        if header.lower() in ['authorization', 'api-key', 'token'] and len(value) > 10:
            logger.info(f"   • {header}: {value[:10]}...")
        else:
            logger.info(f"   • {header}: {value}")
    
    # 3. Body COMPLETO (JSON parseado)
    logger.info("📦 PARSED JSON BODY:")
    if body:
        logger.info(json.dumps(body, indent=2, ensure_ascii=False))
    else:
        logger.info("   • Empty or non-JSON body")
    
    # 4. Raw Body (texto original)
    logger.info("📄 RAW BODY (ORIGINAL):")
    if raw_body:
        # Mostrar máximo 2000 caracteres del raw body
        if len(raw_body) > 2000:
            logger.info(f"   {raw_body[:2000]}... [TRUNCATED - TOTAL: {len(raw_body)} chars]")
        else:
            logger.info(f"   {raw_body}")
    else:
        logger.info("   • Empty raw body")
    
    # 5. Análisis de campos comunes
    logger.info("🎯 COMMON FIELD ANALYSIS:")
    common_fields = {
        'contact': ['contactId', 'contact_id', 'contactName', 'contactEmail', 'contactPhone'],
        'message': ['body', 'message', 'text', 'content', 'message_body'],
        'channel': ['channel', 'channelType', 'provider', 'medium', 'source'],
        'location': ['locationId', 'location_id', 'businessId', 'business_id', 'accountId'],
        'user': ['userId', 'user_id', 'assignedTo', 'assigned_to'],
        'event': ['type', 'eventType', 'direction', 'status', 'timestamp']
    }
    
    for category, fields in common_fields.items():
        found = []
        for field in fields:
            if field in body:
                value = body[field]
                # Truncar valores largos
                if isinstance(value, str) and len(value) > 100:
                    value = f"{value[:100]}... [TRUNCATED]"
                found.append(f"{field}: {value}")
        
        if found:
            logger.info(f"   • {category.upper()}:")
            for item in found:
                logger.info(f"     - {item}")
        else:
            logger.info(f"   • {category.upper()}: No fields found")
    
    logger.info("=" * 80)

@router.post("/webhook/inbound")
async def receive_inbound_webhook(
    request: Request,
    webhook_data: Optional[WebhookData] = None,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint específico para webhooks de INBOUND messages
    """
    try:
        # Obtener información esencial
        client_host = request.client.host if request.client else "Unknown"
        timestamp = datetime.now().isoformat()
        headers = dict(request.headers)
        
        # Obtener el body en diferentes formatos
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        # Intentar parsear como JSON
        body_content = {}
        if raw_body_text.strip():
            try:
                body_content = json.loads(raw_body_text)
            except json.JSONDecodeError:
                body_content = {"raw_text": raw_body_text}
        
        # 🎯 LOG COMPLETO DE TODO LO QUE LLEGA
        log_complete_request(headers, body_content, raw_body_text, client_host)
        
        # Extraer datos específicos para inbound messages
        contact_id = body_content.get('contactId') or body_content.get('contact_id')
        message_body = body_content.get('body', '') or body_content.get('message', '') or body_content.get('text', '')
        message_type = body_content.get('type', 'InboundMessage')
        
        # Información específica de inbound
        channel = body_content.get('channel', 'Unknown')
        provider = body_content.get('provider', 'Unknown')
        contact_name = body_content.get('contactName', 'Unknown')
        contact_email = body_content.get('contactEmail')
        contact_phone = body_content.get('contactPhone')
        
        # Respuesta específica para inbound
        response_data = {
            "status": "success",
            "message": "Inbound webhook processed successfully",
            "timestamp": timestamp,
            "direction": "inbound",
            "request_received": {
                "headers_count": len(headers),
                "body_fields_count": len(body_content),
                "raw_body_length": len(raw_body_text),
                "client_ip": client_host
            },
            "contact_info": {
                "contact_id": contact_id,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "contact_phone": contact_phone
            },
            "channel_info": {
                "channel": channel,
                "provider": provider
            },
            "message_data": {
                "body": message_body,
                "type": message_type
            },
            "all_headers_keys": list(headers.keys()),
            "all_body_keys": list(body_content.keys()) if body_content else []
        }

        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        error_time = datetime.now().isoformat()
        logger.error(f"❌ Error processing INBOUND | 🕒 {error_time} | Error: {str(e)}")
        logger.error(f"🔍 Headers at error: {dict(request.headers)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Error processing inbound webhook: {str(e)}"
        )

@router.post("/webhook/inbound/raw")
async def receive_inbound_webhook_raw(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint alternativo que muestra TODO sin procesamiento
    """
    client_host = request.client.host if request.client else "Unknown"
    headers = dict(request.headers)
    
    # Obtener body en diferentes formatos
    raw_body_text = raw_body.decode('utf-8', errors='ignore')
    
    # Intentar parsear JSON
    try:
        parsed_body = json.loads(raw_body_text) if raw_body_text.strip() else {}
    except:
        parsed_body = {"raw_text": raw_body_text}
    
    # Log completo
    logger.info("🔄 RAW ENDPOINT CALLED - COMPLETE DATA DUMP")
    log_complete_request(headers, parsed_body, raw_body_text, client_host)
    
    return {
        "status": "raw_data_received",
        "timestamp": datetime.now().isoformat(),
        "client_ip": client_host,
        "headers": headers,
        "body": parsed_body,
        "raw_body_preview": raw_body_text[:500] + "..." if len(raw_body_text) > 500 else raw_body_text,
        "raw_body_length": len(raw_body_text)
    }

@router.api_route("/webhook/inbound/catch-all", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all_inbound_webhook(request: Request):
    """
    Endpoint que captura CUALQUIER método HTTP
    """
    client_host = request.client.host if request.client else "Unknown"
    method = request.method
    headers = dict(request.headers)
    
    # Obtener body
    raw_body = await request.body()
    raw_body_text = raw_body.decode('utf-8', errors='ignore')
    
    # Intentar parsear JSON
    try:
        parsed_body = json.loads(raw_body_text) if raw_body_text.strip() else {}
    except:
        parsed_body = {"raw_text": raw_body_text}
    
    logger.info(f"🎯 CATCH-ALL ENDPOINT - METHOD: {method}")
    log_complete_request(headers, parsed_body, raw_body_text, client_host)
    
    return {
        "status": "catch_all_received",
        "method": method,
        "timestamp": datetime.now().isoformat(),
        "client_ip": client_host,
        "headers_count": len(headers),
        "body_fields_count": len(parsed_body),
        "raw_body_length": len(raw_body_text)
    }

@router.get("/inbound/debug")
async def inbound_debug_dashboard():
    """
    Dashboard de debug para ver los últimos webhooks recibidos
    """
    return {
        "message": "🔍 GHL Inbound Webhook Debug Dashboard",
        "endpoints": {
            "/webhook/inbound": "POST - Procesamiento normal con logging completo",
            "/webhook/inbound/raw": "POST - Solo logging sin procesamiento",
            "/webhook/inbound/catch-all": "ANY METHOD - Captura cualquier método HTTP",
            "/inbound/debug": "GET - Este dashboard"
        },
        "logging": {
            "file": "webhook_inbound_complete.log",
            "level": "INFO - Completo"
        },
        "features": {
            "logs_all_headers": True,
            "logs_complete_body": True,
            "logs_raw_body": True,
            "field_analysis": True
        },
        "timestamp": datetime.now().isoformat()
    }