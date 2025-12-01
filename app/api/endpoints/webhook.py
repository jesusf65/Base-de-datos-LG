from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
import json
from datetime import datetime
import re

router = APIRouter()

# Almacenar conversaciones reales
conversation_store = []

async def get_raw_body(request: Request):
    return await request.body()

def extract_chat_information(payload: dict) -> Dict[str, Any]:
    """
    Extrae SOLO la información de chat del payload
    """
    chat_info = {
        "extracted_at": datetime.now().isoformat(),
        "contact_info": {},
        "messages": [],
        "metadata": {}
    }
    
    # 1. INFORMACIÓN DE CONTACTO (ESENCIAL)
    contact_id = payload.get('contactId') or payload.get('contact_id')
    phone = payload.get('contactPhone') or payload.get('contact_phone') or payload.get('phone')
    name = payload.get('first_name') or payload.get('contactName') or payload.get('full_name')
    
    if contact_id:
        chat_info["contact_info"]["id"] = contact_id
    if phone:
        chat_info["contact_info"]["phone"] = phone
    if name and name != "null":
        chat_info["contact_info"]["name"] = name
    
    # 2. BUSCAR CAMPOS DE MENSAJES (si existen)
    # Primero buscar en campos directos
    message_fields = ['body', 'message', 'text', 'content', 'value']
    for field in message_fields:
        if field in payload and payload[field] and str(payload[field]).strip():
            chat_info["messages"].append({
                "content": str(payload[field]),
                "field_source": field,
                "timestamp": datetime.now().isoformat(),
                "direction": "unknown"
            })
            break
    
    # 3. BUSCAR EN CAMPOS DE TEXTO LARGO (podría estar en algún campo específico)
    # Buscar cualquier campo que contenga texto que parezca un mensaje
    for key, value in payload.items():
        if isinstance(value, str) and len(value) > 10 and len(value) < 500:
            # Excluir campos que sabemos que no son mensajes
            excluded_keywords = ['timestamp', 'id', 'contact', 'phone', 'email', 'date', 'time', 'survey', 'rating', 'score']
            if not any(excl in key.lower() for excl in excluded_keywords):
                # Verificar si parece un mensaje de chat
                if any(word in value.lower() for word in ['hola', 'gracias', 'info', 'precio', 'ayuda', 'duda', 'buenos', 'tardes']):
                    chat_info["messages"].append({
                        "content": value,
                        "field_source": key,
                        "timestamp": datetime.now().isoformat(),
                        "direction": "inbound" if any(word in value.lower() for word in ['hola', 'buenos', 'info', 'precio']) else "outbound"
                    })
    
    # 4. INFORMACIÓN DE TIMING (ESENCIAL)
    timing_info = {}
    
    # Primer mensaje
    if 'Primer mensaje registrado' in payload and payload['Primer mensaje registrado']:
        timing_info['first_message'] = payload['Primer mensaje registrado']
    
    # Respuesta del vendedor
    if 'Hora respuesta del vendedor' in payload and payload['Hora respuesta del vendedor']:
        timing_info['seller_response'] = payload['Hora respuesta del vendedor']
    
    # Timestamp de respuesta
    if 'Timestamp Respuesta' in payload and payload['Timestamp Respuesta']:
        timing_info['response_timestamp'] = payload['Timestamp Respuesta']
    
    # Hora de primer mensaje
    if 'Hora de primer mensaje' in payload and payload['Hora de primer mensaje']:
        timing_info['first_message_time'] = payload['Hora de primer mensaje']
    
    if timing_info:
        chat_info["metadata"]["timing"] = timing_info
    
    # 5. CONTADOR DE MENSAJES
    if 'mensajes salientes' in payload:
        chat_info["metadata"]["outbound_count"] = payload['mensajes salientes']
    
    # 6. TIEMPO DE RESPUESTA
    if 'Tiempo hasta primer mensaje enviado' in payload and payload['Tiempo hasta primer mensaje enviado']:
        chat_info["metadata"]["response_time"] = payload['Tiempo hasta primer mensaje enviado']
    
    # 7. FUENTE
    if 'Fuente del lead' in payload and payload['Fuente del lead']:
        chat_info["metadata"]["source"] = payload['Fuente del lead']
    
    return chat_info

@router.post("/webhook/chat-essential")
async def receive_chat_essential(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Muestra SOLO la información ESENCIAL del chat
    """
    try:
        # Leer payload
        raw_body_text = raw_body.decode('utf-8', errors='ignore')
        
        try:
            payload = json.loads(raw_body_text) if raw_body_text.strip() else {}
        except json.JSONDecodeError:
            payload = {"raw_text": raw_body_text}
        
        # Extraer solo información esencial
        chat_info = extract_chat_information(payload)
        
        # MOSTRAR EN FORMATO DE CHAT LIMPIO
        print("\n" + "═" * 60)
        print("💬 CHAT ACTIVO")
        print("═" * 60)
        
        # Información del contacto
        contact = chat_info["contact_info"]
        if contact.get("id") or contact.get("name") or contact.get("phone"):
            print(f"👤 CONTACTO:")
            if contact.get("name"):
                print(f"   Nombre: {contact['name']}")
            if contact.get("phone"):
                print(f"   Teléfono: {contact['phone']}")
            if contact.get("id"):
                print(f"   ID: {contact['id']}")
        
        # Mostrar mensajes encontrados
        if chat_info["messages"]:
            print(f"\n📨 MENSAJES ENCONTRADOS ({len(chat_info['messages'])}):")
            for i, msg in enumerate(chat_info["messages"], 1):
                direction = msg.get("direction", "desconocido")
                if direction == "inbound":
                    prefix = "📩 [CLIENTE]"
                elif direction == "outbound":
                    prefix = "📤 [VENDEDOR]"
                else:
                    prefix = "❓ [DESCONOCIDO]"
                
                print(f"\n{prefix}")
                print(f"   {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")
                print(f"   🕒 {msg['timestamp'][11:19]} | 📍 Campo: {msg['field_source']}")
        else:
            print("\n⚠️  NO se encontraron mensajes de texto en este payload")
            print("   (Solo se recibieron datos de formulario/resumen)")
        
        # Mostrar información de timing
        if chat_info["metadata"].get("timing"):
            print(f"\n⏰ TIMING:")
            timing = chat_info["metadata"]["timing"]
            for key, value in timing.items():
                if value:
                    label = key.replace('_', ' ').title()
                    print(f"   • {label}: {value}")
        
        # Mostrar métricas
        if chat_info["metadata"].get("outbound_count") is not None:
            print(f"\n📊 MÉTRICAS:")
            print(f"   • Mensajes enviados: {chat_info['metadata']['outbound_count']}")
        
        if chat_info["metadata"].get("response_time"):
            print(f"   • Tiempo respuesta: {chat_info['metadata']['response_time']}")
        
        if chat_info["metadata"].get("source"):
            print(f"   • Fuente: {chat_info['metadata']['source']}")
        
        # Información del payload
        print(f"\n📦 INFORMACIÓN TÉCNICA:")
        print(f"   • Campos totales: {len(payload)}")
        print(f"   • Campos con datos: {sum(1 for v in payload.values() if v and str(v).strip())}")
        print(f"   • Tamaño: {len(raw_body_text)} bytes")
        print(f"   • Hora recepción: {datetime.now().strftime('%H:%M:%S')}")
        
        print("═" * 60)
        
        # Almacenar para histórico
        conversation_store.append({
            "timestamp": datetime.now().isoformat(),
            "contact_id": contact.get("id"),
            "contact_name": contact.get("name"),
            "phone": contact.get("phone"),
            "messages_found": len(chat_info["messages"]),
            "outbound_count": chat_info["metadata"].get("outbound_count"),
            "response_time": chat_info["metadata"].get("response_time")
        })
        
        # Limpiar histórico antiguo
        if len(conversation_store) > 1000:
            conversation_store.pop(0)
        
        # Respuesta
        return JSONResponse(content={
            "status": "processed",
            "chat_info": {
                "contact": chat_info["contact_info"],
                "messages_count": len(chat_info["messages"]),
                "has_timing_info": bool(chat_info["metadata"].get("timing")),
                "outbound_messages": chat_info["metadata"].get("outbound_count")
            },
            "processing_summary": {
                "total_fields": len(payload),
                "essential_fields_extracted": bool(chat_info["contact_info"]) or bool(chat_info["messages"])
            }
        }, status_code=200)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@router.post("/webhook/minimal")
async def receive_minimal(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Versión MUY mínima - solo lo ABSOLUTAMENTE esencial
    """
    raw_body_text = raw_body.decode('utf-8', errors='ignore')
    
    try:
        payload = json.loads(raw_body_text) if raw_body_text.strip() else {}
    except json.JSONDecodeError:
        payload = {"raw_text": raw_body_text}
    
    # EXTRAER SOLO LO ESENCIAL
    essential = {}
    
    # 1. Contact ID
    essential["contact_id"] = payload.get('contactId') or payload.get('contact_id')
    
    # 2. Phone
    essential["phone"] = payload.get('contactPhone') or payload.get('contact_phone') or payload.get('phone')
    
    # 3. Name
    essential["name"] = payload.get('first_name') or payload.get('contactName') or payload.get('full_name')
    
    # 4. Outbound messages count
    essential["outbound_count"] = payload.get('mensajes salientes')
    
    # 5. Response time
    essential["response_time"] = payload.get('Tiempo hasta primer mensaje enviado')
    
    # 6. Buscar ALGÚN mensaje de texto
    message_content = None
    message_fields = ['body', 'message', 'text', 'content']
    for field in message_fields:
        if field in payload and payload[field] and str(payload[field]).strip():
            message_content = str(payload[field])[:100]
            break
    
    # MOSTRAR SUPER LIMPIO
    print("\n" + "-" * 40)
    print(f"🕒 {datetime.now().strftime('%H:%M:%S')}")
    
    if essential["contact_id"]:
        print(f"👤 ID: {essential['contact_id']}")
    
    if essential["name"] and essential["name"] != "null":
        print(f"📛 Nombre: {essential['name']}")
    
    if essential["phone"]:
        print(f"📞 Tel: {essential['phone']}")
    
    if essential["outbound_count"] is not None:
        print(f"📤 Enviados: {essential['outbound_count']}")
    
    if essential["response_time"]:
        print(f"⏱️  Respuesta: {essential['response_time']}")
    
    if message_content:
        print(f"💬 Msg: {message_content}")
    else:
        print("💬 [Sin contenido de mensaje]")
    
    print("-" * 40)
    
    return {"status": "minimal_processed"}

@router.get("/webhook/chat-history")
async def get_chat_history():
    """
    Obtiene historial de conversaciones
    """
    # Agrupar por contacto
    contacts = {}
    for conv in conversation_store:
        contact_id = conv.get("contact_id")
        if contact_id:
            if contact_id not in contacts:
                contacts[contact_id] = {
                    "contact_id": contact_id,
                    "contact_name": conv.get("contact_name"),
                    "phone": conv.get("phone"),
                    "updates": [],
                    "max_outbound": 0
                }
            
            contacts[contact_id]["updates"].append({
                "timestamp": conv["timestamp"],
                "outbound_count": conv.get("outbound_count"),
                "response_time": conv.get("response_time")
            })
            
            if conv.get("outbound_count", 0) > contacts[contact_id]["max_outbound"]:
                contacts[contact_id]["max_outbound"] = conv.get("outbound_count", 0)
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "total_conversations": len(conversation_store),
        "unique_contacts": len(contacts),
        "contacts": list(contacts.values())
    }

# Endpoint de compatibilidad
@router.post("/webhook/inbound")
async def compatibility_inbound(
    request: Request,
    raw_body: bytes = Depends(get_raw_body)
):
    """
    Endpoint legacy
    """
    return await receive_chat_essential(request, raw_body)

@router.get("/")
async def root():
    return {
        "service": "Chat Essential Tracker",
        "description": "Muestra SOLO la información esencial de los mensajes",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /webhook/chat-essential": "Información completa pero limpia",
            "POST /webhook/minimal": "Versión SUPER mínima",
            "POST /webhook/inbound": "Endpoint legacy",
            "GET /webhook/chat-history": "Historial de conversaciones"
        },
        "what_it_shows": [
            "Contact ID",
            "Nombre (si existe)",
            "Teléfono",
            "Contador de mensajes enviados",
            "Tiempo de respuesta",
            "Cualquier mensaje de texto encontrado"
        ]
    }