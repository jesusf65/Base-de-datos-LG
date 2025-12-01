from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime
import re

# Configuración de logging más clara
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('all_messages_detailed.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("all_messages_tracker")

router = APIRouter()

# Almacenamiento simple para ver histórico
message_history = []

async def get_raw_body(request: Request):
    return await request.body()

def detect_message_direction(payload: dict) -> str:
    """
    Detecta si es MENSAJE ENTRANTE o MENSAJE SALIENTE
    """
    # 1. Por campo explícito 'direction'
    direction = payload.get('direction', '').lower()
    if direction == 'inbound':
        return "ENTRANTE"
    elif direction == 'outbound':
        return "SALIENTE"
    
    # 2. Por campo 'type'
    msg_type = payload.get('type', '').lower()
    if 'inbound' in msg_type:
        return "ENTRANTE"
    elif 'outbound' in msg_type:
        return "SALIENTE"
    
    # 3. Por campos específicos de GHL
    event_type = payload.get('eventType', '').lower()
    if 'inbound' in event_type:
        return "ENTRANTE"
    elif 'outbound' in event_type:
        return "SALIENTE"
    
    # 4. Por lógica de contenido (análisis de texto)
    content = get_message_content(payload)
    if content:
        content_lower = content.lower()
        
        # Palabras comunes en mensajes entrantes (del cliente)
        inbound_keywords = [
            'hola', 'hi', 'hello', 'buenos días', 'buenas tardes',
            'información', 'precio', 'costo', 'cotización', 'me interesa',
            'quiero', 'necesito', 'ayuda', 'duda', 'pregunta', 'problema',
            'disponible', 'tienen', 'venden', 'ofrecen'
        ]
        
        # Palabras comunes en mensajes salientes (del negocio)
        outbound_keywords = [
            'gracias', 'thank you', 'te ayudo', 'en breve', 'agente',
            'asesor', 'bienvenido', 'te contacto', 'llamada', 'cita',
            'horario', 'disponibilidad', 'oferta', 'promoción', 'descuento',
            'seguimiento', 'recordatorio', 'confirmación'
        ]
        
        inbound_count = sum(1 for word in inbound_keywords if word in content_lower)
        outbound_count = sum(1 for word in outbound_keywords if word in content_lower)
        
        if inbound_count > outbound_count:
            return "ENTRANTE"
        elif outbound_count > inbound_count:
            return "SALIENTE"
    
    # 5. Por campos de origen/destino
    if payload.get('fromCustomer') or payload.get('from_contact'):
        return "ENTRANTE"
    elif payload.get('toCustomer') or payload.get('campaignId'):
        return "SALIENTE"
    
    return "INDETERMINADO"

def get_message_content(payload: dict) -> str:
    """
    Obtiene el contenido del mensaje de cualquier campo posible
    """
    content_fields = [
        'body', 'message', 'text', 'content', 'message_body',
        'smsContent', 'whatsappMessage', 'value', 'data'
    ]
    
    for field in content_fields:
        if field in payload:
            value = payload[field]
            if isinstance(value, str) and value.strip():
                return value.strip()
            elif isinstance(value, dict):
                # Buscar en subcampos
                for sub_field in content_fields:
                    if sub_field in value and isinstance(value[sub_field], str) and value[sub_field].strip():
                        return value[sub_field].strip()
    
    return ""

def log_complete_payload(payload: dict, direction: str, headers: dict, client_ip: str):
    """
    Muestra TODA la información del payload de forma organizada
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Separador visual basado en dirección
    if direction == "ENTRANTE":
        separator = "📩" + "=" * 78 + "📩"
        title = "📩 MENSAJE ENTRANTE (INBOUND)"
    elif direction == "SALIENTE":
        separator = "📤" + "=" * 78 + "📤"
        title = "📤 MENSAJE SALIENTE (OUTBOUND)"
    else:
        separator = "❓" + "=" * 78 + "❓"
        title = "❓ MENSAJE DE DIRECCIÓN DESCONOCIDA"
    
    logger.info(separator)
    logger.info(f"{title}")
    logger.info(f"🕒 HORA RECEPCIÓN: {timestamp}")
    logger.info(f"🌐 IP CLIENTE: {client_ip}")
    logger.info(separator)
    
    # 1. INFORMACIÓN DE CONTACTO
    logger.info("👤 INFORMACIÓN DE CONTACTO:")
    contact_fields = ['contactId', 'contact_id', 'contactName', 'contact_name', 
                     'contactPhone', 'contact_phone', 'contactEmail', 'contact_email',
                     'from', 'to', 'phone', 'email', 'firstName', 'lastName']
    
    contact_info_found = False
    for field in contact_fields:
        if field in payload and payload[field]:
            logger.info(f"   • {field}: {payload[field]}")
            contact_info_found = True
    
    if not contact_info_found:
        logger.info("   • No se encontró información de contacto")
    
    # 2. CONTENIDO DEL MENSAJE
    logger.info("💬 CONTENIDO DEL MENSAJE:")
    content = get_message_content(payload)
    if content:
        if len(content) > 200:
            logger.info(f"   {content[:200]}... [TRUNCADO - TOTAL: {len(content)} caracteres]")
        else:
            logger.info(f"   {content}")
    else:
        logger.info("   • [SIN CONTENIDO DE TEXTO]")
    
    # 3. METADATOS IMPORTANTES
    logger.info("📊 METADATOS PRINCIPALES:")
    important_fields = [
        'timestamp', 'time', 'createdAt', 'date', 'eventType',
        'channel', 'channelType', 'platform', 'medium', 'source',
        'conversationId', 'conversation_id', 'messageId', 'id',
        'locationId', 'location_id', 'userId', 'user_id'
    ]
    
    for field in important_fields:
        if field in payload:
            value = payload[field]
            if isinstance(value, str) and len(value) > 100:
                logger.info(f"   • {field}: {value[:100]}...")
            else:
                logger.info(f"   • {field}: {value}")
    
    # 4. TODOS LOS CAMPOS DISPONIBLES (resumen)
    logger.info("📋 TODOS LOS CAMPOS DISPONIBLES:")
    all_fields = list(payload.keys())
    total_fields = len(all_fields)
    
    if total_fields <= 20:
        for field in all_fields:
            if field not in important_fields and field not in contact_fields:
                value = payload[field]
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:50] + "..."
                logger.info(f"   • {field}: {value_str}")
    else:
        logger.info(f"   • Total de campos: {total_fields}")
        logger.info(f"   • Primeros 10 campos: {', '.join(all_fields[:10])}")
        logger.info(f"   • ... y {total_fields - 10} campos más")
    
    # 5. HEADERS IMPORTANTES
    logger.info("🌐 INFORMACIÓN DE CONEXIÓN:")
    important_headers = ['user-agent', 'content-type', 'content-length', 
                        'x-forwarded-for', 'x-real-ip', 'host']
    
    for header in important_headers:
        if header in headers:
            logger.info(f"   • {header}: {headers[header]}")
    
    logger.info(separator + "\n")

@router.post("/webhook/messages")
async def receive_all_messages(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint principal que muestra TODA la información recibida
    """
    try:
        # Obtener información básica
        client_ip = request.client.host if request.client else "Desconocida"
        headers = dict(request.headers)
        
        # Leer y parsear el body
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        try:
            payload = json.loads(raw_body_text) if raw_body_text.strip() else {}
        except json.JSONDecodeError:
            payload = {"raw_text": raw_body_text}
        
        # Detectar dirección del mensaje
        direction = detect_message_direction(payload)
        
        # Log completo del payload
        log_complete_payload(payload, direction, headers, client_ip)
        
        # Guardar en histórico
        message_entry = {
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "client_ip": client_ip,
            "payload_size": len(raw_body_text),
            "field_count": len(payload),
            "has_content": bool(get_message_content(payload))
        }
        message_history.append(message_entry)
        
        # Mantener solo últimos 1000 registros
        if len(message_history) > 1000:
            message_history.pop(0)
        
        # Preparar respuesta
        content = get_message_content(payload)
        
        response_data = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "message_type": direction,
            "summary": {
                "total_fields_received": len(payload),
                "payload_size_bytes": len(raw_body_text),
                "message_content_found": bool(content),
                "content_length": len(content) if content else 0,
                "detection_method": "Análisis automático de contenido"
            },
            "contact_info": {
                "contact_id": payload.get('contactId') or payload.get('contact_id'),
                "contact_name": payload.get('contactName') or payload.get('contact_name'),
                "contact_phone": payload.get('contactPhone') or payload.get('contact_phone')
            },
            "message_content": content if content else "[Sin contenido de texto]"
        }
        
        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.error(f"❌ ERROR PROCESANDO MENSAJE | {error_time}")
        logger.error(f"🔧 Detalle del error: {str(e)}")
        
        raise HTTPException(
            status_code=400, 
            detail=f"Error procesando mensaje: {str(e)}"
        )

@router.post("/webhook/messages/simple")
async def receive_messages_simple(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Versión simplificada para logs más limpios
    """
    client_ip = request.client.host if request.client else "Desconocida"
    
    raw_body_text = raw_body.decode('utf-8', errors='ignore')
    
    try:
        payload = json.loads(raw_body_text) if raw_body_text.strip() else {}
    except json.JSONDecodeError:
        payload = {"raw_text": raw_body_text}
    
    # Detectar dirección
    direction = detect_message_direction(payload)
    
    # Obtener contenido
    content = get_message_content(payload)
    
    # Log simple pero claro
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if direction == "ENTRANTE":
        logger.info(f"📩 [{timestamp}] MENSAJE ENTRANTE de {client_ip}")
    elif direction == "SALIENTE":
        logger.info(f"📤 [{timestamp}] MENSAJE SALIENTE de {client_ip}")
    else:
        logger.info(f"❓ [{timestamp}] MENSAJE INDETERMINADO de {client_ip}")
    
    if content:
        content_preview = content[:100] + "..." if len(content) > 100 else content
        logger.info(f"   💬 {content_preview}")
    
    # Info de contacto si existe
    contact_id = payload.get('contactId') or payload.get('contact_id')
    contact_phone = payload.get('contactPhone') or payload.get('contact_phone')
    
    if contact_id:
        logger.info(f"   👤 Contact ID: {contact_id}")
    if contact_phone:
        logger.info(f"   📞 Teléfono: {contact_phone}")
    
    logger.info(f"   📊 Campos recibidos: {len(payload)}")
    
    return {
        "status": "received",
        "direction": direction,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/webhook/messages/history")
async def get_message_history(limit: int = 20):
    """
    Obtiene el histórico de mensajes recibidos
    """
    recent_history = message_history[-limit:] if message_history else []
    
    stats = {
        "total_messages_received": len(message_history),
        "inbound_count": sum(1 for m in message_history if m['direction'] == 'ENTRANTE'),
        "outbound_count": sum(1 for m in message_history if m['direction'] == 'SALIENTE'),
        "indeterminate_count": sum(1 for m in message_history if m['direction'] == 'INDETERMINADO')
    }
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "statistics": stats,
        "recent_messages": recent_history
    }

@router.get("/webhook/messages/test")
async def test_message_endpoint():
    """
    Endpoint de prueba para verificar que el sistema funciona
    """
    test_examples = {
        "inbound_example": {
            "contactId": "TEST123",
            "contactName": "Juan Pérez",
            "contactPhone": "+573001234567",
            "body": "Hola, me interesa información sobre sus servicios",
            "direction": "inbound",
            "timestamp": datetime.now().isoformat(),
            "channel": "whatsapp"
        },
        "outbound_example": {
            "contactId": "TEST456",
            "contactName": "María García",
            "contactPhone": "+573009876543",
            "message": "Gracias por contactarnos, en breve le atenderemos",
            "type": "outbound_message",
            "time": datetime.now().isoformat(),
            "platform": "sms"
        },
        "form_example": {
            "contactId": "SL3Ljfe3CJ90iv7OHWIu",
            "Tiempo hasta primer mensaje enviado": "1 hora con 34 minutos",
            "mensajes salientes": 3,
            "contactPhone": "+573246870911",
            "Fuente del lead": "Facebook",
            "Canal": "WhatsApp"
        }
    }
    
    return {
        "message": "✅ Sistema de mensajes funcionando",
        "timestamp": datetime.now().isoformat(),
        "endpoints_available": {
            "POST /webhook/messages": "Muestra TODA la información detallada",
            "POST /webhook/messages/simple": "Versión simplificada para logs",
            "GET /webhook/messages/history": "Histórico de mensajes",
            "GET /webhook/messages/test": "Esta página de prueba"
        },
        "test_payloads": test_examples,
        "current_stats": {
            "total_messages_stored": len(message_history),
            "last_message_time": message_history[-1]['timestamp'] if message_history else "Ninguno"
        }
    }

# Endpoint de compatibilidad
@router.post("/webhook/inbound")
async def compatibility_endpoint(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint de compatibilidad para /webhook/inbound
    """
    logger.info("🔄 Usando endpoint de compatibilidad /webhook/inbound")
    return await receive_all_messages(request, raw_body)

@router.api_route("/webhook/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all_webhooks(request: Request, path: str):
    """
    Captura cualquier webhook que llegue
    """
    method = request.method
    client_ip = request.client.host if request.client else "Desconocida"
    
    logger.info(f"🎯 WEBHOOK CAPTURADO: {method} /webhook/{path}")
    logger.info(f"   🌐 IP: {client_ip}")
    logger.info(f"   🕒 Hora: {datetime.now().strftime('%H:%M:%S')}")
    
    # Solo procesar body para métodos que lo tienen
    if method in ["POST", "PUT", "PATCH"]:
        try:
            raw_body = await request.body()
            raw_body_text = raw_body.decode('utf-8', errors='ignore')
            
            try:
                payload = json.loads(raw_body_text) if raw_body_text.strip() else {}
                logger.info(f"   📦 Payload (primeros 200 chars): {raw_body_text[:200]}...")
            except:
                logger.info(f"   📦 Body raw: {raw_body_text[:200]}...")
        except:
            logger.info("   📦 [No se pudo leer el body]")
    
    return {
        "status": "captured",
        "message": f"Webhook recibido en /webhook/{path}",
        "method": method,
        "timestamp": datetime.now().isoformat(),
        "recommendation": "Usa POST /webhook/messages para procesamiento de mensajes"
    }