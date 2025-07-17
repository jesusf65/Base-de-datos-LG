from fastapi import APIRouter, Request
import json
import logging
# Configura el logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Crea un handler para console
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

# Define el formato del log
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Añade el handler al logger
logger.addHandler(handler)

router = APIRouter()

@router.post("/webhook/lead")
async def receive_webhook(request: Request):
    try:
        payload = await request.json()
        logger.info("📥 Webhook recibido:")
        logger.info(json.dumps(payload, indent=2, ensure_ascii=False))
        
        call_data = payload.get('data', {})
        
        # Verificar si la llamada fue atendida
        if call_data.get('answered_at'):
            logger.info("✅ Llamada ATENDIDA")
            
            # Verificar posible grabación vacía
            duration = call_data.get('duration', 0)
            answered_at = call_data.get('answered_at', 0)
            ended_at = call_data.get('ended_at', 0)
            
            # Calcular tiempo real de conversación
            talk_time = ended_at - answered_at if all([answered_at, ended_at]) else 0
            
            if talk_time < 5:  # Menos de 5 segundos de conversación
                logger.warning(f"⚠️ Grabación potencialmente vacía o corta. Duración: {talk_time}s")
                
            # Verificar si existe URL de grabación
            if not call_data.get('recording'):
                logger.error("❌ No se encontró URL de grabación")
                
        elif call_data.get('missed_call_reason'):
            logger.warning(f"⛔ Llamada NO atendida: {call_data['missed_call_reason']}")
        else:
            logger.warning("⚠️ Estado de llamada desconocido")
        
        return {"status": "ok", "message": "llamada recibida"}
    except Exception as e:
        logger.error(f"Error al procesar webhook: {str(e)}")
        return {"status": "error", "message": str(e)}