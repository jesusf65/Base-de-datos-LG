from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime
import httpx

# Configuración de logging simplificada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('webhook_inbound.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("ghl_inbound_webhook")

router = APIRouter()

class WebhookData(BaseModel):
    data: Dict[str, Any] = {}

async def get_raw_body(request: Request):
    """Obtiene el cuerpo raw de la petición"""
    return await request.body()

async def send_to_leadconnector_inbound(contact_id: str, message_body: str, message_type: str, subaccount_info: dict, contact_info: dict):
    """
    Función para enviar datos de inbound messages al webhook de LeadConnector
    """
    if not contact_id:
        logger.warning("⚠️ No contact_id available, skipping LeadConnector call")
        return None
    
    leadconnector_url = "https://services.leadconnectorhq.com/hooks/f1nXHhZhhRHOiU74mtmb/webhook-trigger/8c04bdb6-054d-42cb-a77a-5769d491d8b3"
    
    payload = {
        "contact_id": contact_id,
        "message": message_body,
        "type": message_type,
        "direction": "inbound",
        "timestamp": datetime.now().isoformat(),
        "subaccount_info": subaccount_info,
        "contact_info": contact_info,
        "webhook_source": "inbound_message"
    }
    
    try:
        logger.info(f"🔄 Preparing to send INBOUND to LeadConnector")
        logger.info(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info("🚀 Sending POST request to LeadConnector...")
            response = await client.post(
                leadconnector_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"📤 LeadConnector Response: Status {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ Successfully sent INBOUND to LeadConnector")
                try:
                    return response.json()
                except:
                    return {"raw_response": response.text}
            else:
                logger.error(f"❌ LeadConnector error: {response.status_code} - {response.text}")
                return {"error": f"Status {response.status_code}", "details": response.text}
                
    except Exception as e:
        logger.error(f"🚨 Error calling LeadConnector: {str(e)}")
        return {"error": str(e)}

def extract_subaccount_info_inbound(body_content: dict, headers: dict) -> dict:
    """
    Extrae información de la subcuenta para inbound messages
    """
    subaccount_info = {}
    
    # Campos específicos para inbound messages
    possible_location_fields = ['locationId', 'location_id', 'businessId', 'business_id', 'accountId', 'account_id']
    possible_user_fields = ['userId', 'user_id', 'assignedTo', 'assigned_to']
    
    for field in possible_location_fields:
        if body_content.get(field):
            subaccount_info['location_id'] = body_content.get(field)
            break
    
    for field in possible_user_fields:
        if body_content.get(field):
            subaccount_info['user_id'] = body_content.get(field)
            break
    
    # Headers específicos
    if 'x-account-id' in headers:
        subaccount_info['account_id_header'] = headers['x-account-id']
    if 'x-location-id' in headers:
        subaccount_info['location_id_header'] = headers['x-location-id']
    
    # Información de canal para inbound
    if body_content.get('channel'):
        subaccount_info['channel'] = body_content.get('channel')
    if body_content.get('provider'):
        subaccount_info['provider'] = body_content.get('provider')
    
    return subaccount_info

def extract_contact_info_inbound(body_content: dict) -> dict:
    """
    Extrae información del contacto para inbound messages
    """
    contact_info = {}
    
    # Información básica del contacto
    if body_content.get('contactId'):
        contact_info['contact_id'] = body_content.get('contactId')
    if body_content.get('contactName'):
        contact_info['contact_name'] = body_content.get('contactName')
    if body_content.get('contactEmail'):
        contact_info['contact_email'] = body_content.get('contactEmail')
    if body_content.get('contactPhone'):
        contact_info['contact_phone'] = body_content.get('contactPhone')
    
    # Información de canal y medio
    if body_content.get('channelType'):
        contact_info['channel_type'] = body_content.get('channelType')
    if body_content.get('medium'):
        contact_info['medium'] = body_content.get('medium')
    if body_content.get('source'):
        contact_info['source'] = body_content.get('source')
    
    return contact_info

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
        
        # Obtener el body
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        # Intentar parsear como JSON
        body_content = {}
        if raw_body_text.strip():
            try:
                body_content = json.loads(raw_body_text)
            except json.JSONDecodeError:
                body_content = {"raw_text": raw_body_text}
        
        # Extraer datos específicos para inbound messages
        contact_id = body_content.get('contactId') or body_content.get('contact_id')
        message_body = body_content.get('body', '') or body_content.get('message', '') or body_content.get('text', '')
        message_type = body_content.get('type', 'InboundMessage')
        direction = body_content.get('direction', 'inbound')
        status = body_content.get('status', 'received')
        
        # Información específica de inbound
        channel = body_content.get('channel', 'Unknown')
        provider = body_content.get('provider', 'Unknown')
        contact_name = body_content.get('contactName', 'Unknown')
        contact_email = body_content.get('contactEmail')
        contact_phone = body_content.get('contactPhone')
        
        # 🔍 EXTRAER INFORMACIÓN DE LA SUBCUENTA Y CONTACTO
        subaccount_info = extract_subaccount_info_inbound(body_content, headers)
        contact_info = extract_contact_info_inbound(body_content)
        
        # 🎯 LOG ESPECÍFICO PARA INBOUND
        logger.info(f"📩 INBOUND MESSAGE | 👤 {client_host} | 🕒 {timestamp}")
        logger.info(f"👤 Contact: {contact_name} | 📞 {contact_phone} | 📧 {contact_email}")
        logger.info(f"🔗 Contact ID: {contact_id} | 📱 Channel: {channel} | 🏢 Provider: {provider}")
        
        # 📊 MOSTRAR INFORMACIÓN DE LA SUBCUENTA
        if subaccount_info:
            logger.info(f"🏢 Subaccount Info: {json.dumps(subaccount_info, ensure_ascii=False)}")
        
        if message_body:
            # Mostrar el mensaje de forma compacta
            if len(message_body) > 500:
                message_display = message_body[:500] + "..."
            else:
                message_display = message_body
            logger.info(f"💬 Inbound Message: {message_display}")
        else:
            logger.info("💬 Inbound Message: ⚠️ Empty")

        # 🔄 Enviar a LeadConnector
        leadconnector_response = None
        if contact_id:
            logger.info(f"🔄 Sending INBOUND to LeadConnector for contact: {contact_id}")
            leadconnector_response = await send_to_leadconnector_inbound(
                contact_id=contact_id,
                message_body=message_body,
                message_type=message_type,
                subaccount_info=subaccount_info,
                contact_info=contact_info
            )
        else:
            logger.warning("⚠️ No contact_id found, skipping LeadConnector")

        # Respuesta específica para inbound
        response_data = {
            "status": "success",
            "message": "Inbound webhook processed successfully",
            "timestamp": timestamp,
            "direction": "inbound",
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
                "type": message_type,
                "status": status
            },
            "subaccount_info": subaccount_info,
            "leadconnector_sent": leadconnector_response is not None and "error" not in str(leadconnector_response)
        }

        # Agregar respuesta de LeadConnector si existe
        if leadconnector_response:
            response_data["leadconnector_response"] = leadconnector_response

        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        error_time = datetime.now().isoformat()
        logger.error(f"❌ Error processing INBOUND | 🕒 {error_time} | Error: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Error processing inbound webhook: {str(e)}"
        )

@router.post("/webhook/inbound/debug")
async def debug_inbound_webhook(request: Request):
    """
    Endpoint para debuggear inbound webhooks
    """
    headers = dict(request.headers)
    body = await request.json()
    
    # Campos específicos para inbound
    inbound_fields = {
        'contact_fields': ['contactId', 'contact_id', 'contactName', 'contactEmail', 'contactPhone'],
        'channel_fields': ['channel', 'channelType', 'provider', 'medium', 'source'],
        'message_fields': ['body', 'message', 'text', 'direction', 'type', 'status'],
        'location_fields': ['locationId', 'location_id', 'businessId', 'business_id']
    }
    
    found_fields = {}
    
    for category, fields in inbound_fields.items():
        found_fields[category] = {}
        for field in fields:
            if field in body:
                found_fields[category][field] = body[field]
    
    return {
        "webhook_type": "inbound_debug",
        "all_headers": headers,
        "all_body_fields": body,
        "categorized_fields": found_fields,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/inbound")
async def inbound_root():
    """
    Endpoint raíz para inbound webhooks
    """
    return {
        "message": "🚀 GHL Inbound Webhook Server Active",
        "endpoints": {
            "/webhook/inbound": "POST - Para inbound messages",
            "/webhook/inbound/debug": "POST - Para debuggear inbound webhooks"
        },
        "supported_channels": ["sms", "whatsapp", "messenger", "instagram", "email"],
        "timestamp": datetime.now().isoformat()
    }