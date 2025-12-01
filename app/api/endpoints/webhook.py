from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
import json
from datetime import datetime

router = APIRouter()

async def get_raw_body(request: Request):
    return await request.body()

@router.post("/webhook/diagnostic")
async def diagnostic_webhook(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint para diagnosticar EXACTAMENTE qué tipo de payload estás recibiendo
    """
    # Información básica
    client_ip = request.client.host if request.client else "unknown"
    timestamp = datetime.now().isoformat()
    
    # Leer body
    raw_body_text = raw_body.decode('utf-8', errors='ignore')
    
    try:
        payload = json.loads(raw_body_text) if raw_body_text.strip() else {}
    except json.JSONDecodeError:
        payload = {"raw_text": raw_body_text}
    
    # Análisis COMPLETO del payload
    analysis = {
        "timestamp": timestamp,
        "client_ip": client_ip,
        "payload_size_bytes": len(raw_body_text),
        "total_fields": len(payload) if isinstance(payload, dict) else 0,
        "is_form_data": len(payload) > 50,  # Los formularios tienen 110+ campos
        "has_message_fields": any(field in payload for field in ['body', 'message', 'text', 'content']),
        "has_direction_field": 'direction' in payload or 'type' in payload,
        "has_contact_fields": any(field in payload for field in ['contactId', 'contact_id', 'contactName', 'contactPhone']),
        "field_names": list(payload.keys()) if isinstance(payload, dict) else [],
        "sample_values": {}
    }
    
    # Tomar muestra de algunos valores
    sample_fields = ['contactId', 'contact_id', 'body', 'message', 'text', 'content', 'direction', 'type', 'timestamp']
    for field in sample_fields:
        if field in payload:
            value = payload[field]
            analysis["sample_values"][field] = str(value)[:100] + "..." if len(str(value)) > 100 else value
    
    # MOSTRAR EN CONSOLA de forma CLARA
    print("\n" + "🔍" * 30)
    print("🔍 DIAGNÓSTICO DE WEBHOOK")
    print("🔍" * 30)
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print(f"IP Cliente: {client_ip}")
    print(f"Tamaño payload: {len(raw_body_text)} bytes")
    print(f"Total campos: {len(payload)}")
    print("-" * 40)
    
    # Detectar tipo
    if analysis["has_message_fields"] and analysis["has_direction_field"]:
        print("✅ TIPO: MENSAJE INDIVIDUAL DE CHAT")
        direction = payload.get('direction') or payload.get('type', 'unknown')
        content = payload.get('body') or payload.get('message') or payload.get('text') or payload.get('content', '')
        contact_id = payload.get('contactId') or payload.get('contact_id')
        
        print(f"📨 Dirección: {direction}")
        print(f"👤 Contact ID: {contact_id}")
        print(f"💬 Mensaje: {content[:200]}{'...' if len(content) > 200 else ''}")
        
    elif analysis["is_form_data"]:
        print("📋 TIPO: FORMULARIO/RESUMEN (110+ campos)")
        print(f"📊 Campos con datos: {sum(1 for v in payload.values() if v and str(v).strip())}/{len(payload)}")
        
        # Mostrar campos importantes si existen
        important_fields = {
            'mensajes salientes': 'Mensajes enviados',
            'Tiempo hasta primer mensaje enviado': 'Tiempo respuesta',
            'contact_id': 'Contact ID',
            'phone': 'Teléfono',
            'first_name': 'Nombre'
        }
        
        for field, label in important_fields.items():
            if field in payload:
                print(f"📌 {label}: {payload[field]}")
                
    else:
        print("❓ TIPO: DESCONOCIDO")
        print(f"Campos encontrados: {', '.join(list(payload.keys())[:10])}")
        if len(payload) > 10:
            print(f"... y {len(payload) - 10} más")
    
    print("🔍" * 30)
    
    return JSONResponse(content={
        "status": "diagnosed",
        "analysis": analysis,
        "detected_type": "chat_message" if analysis["has_message_fields"] else "form_data" if analysis["is_form_data"] else "unknown"
    }, status_code=200)

@router.get("/webhook/test-chat")
async def test_chat_message():
    """
    Genera ejemplos de cómo DEBERÍAN verse los mensajes de chat reales
    """
    examples = {
        "inbound_example_correct": {
            "contactId": "TEST123",
            "contactName": "Juan Pérez",
            "contactPhone": "+573001234567",
            "body": "Hola, me interesa información sobre sus servicios",
            "direction": "inbound",
            "timestamp": "2025-12-01T16:30:00Z",
            "channel": "whatsapp",
            "type": "message"
        },
        "outbound_example_correct": {
            "contactId": "TEST456",
            "contactName": "María García",
            "contactPhone": "+573009876543",
            "message": "Gracias por contactarnos, te ayudo con eso",
            "direction": "outbound",
            "timestamp": "2025-12-01T16:31:15Z",
            "channel": "sms",
            "type": "message"
        },
        "what_you_are_receiving": {
            "¿tienes contacto directo con dueños o directivos de dealer?": "",
            "mensajes salientes": 17,
            "Tiempo hasta primer mensaje enviado": "1 hora con 34 minutos",
            "GPT - Full Conversation": "",
            "contact_id": "KKhGeMkoIdMdanhMGNg4",
            "first_name": "null",
            "phone": "+15164592134",
            "total_fields": 110
        }
    }
    
    return {
        "message": "Ejemplos de estructuras de mensajes",
        "note": "Compara lo que recibes con estos ejemplos",
        "examples": examples,
        "how_to_test": "Envía un mensaje real de chat a POST /webhook/diagnostic"
    }