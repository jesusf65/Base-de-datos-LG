from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import logging
import os

class TimingData:
    def __init__(self):
        self.contact_creation = None
        self.first_call = None
        self.time_between_minutes = None
        self.contact_id = None

class GHLContactPayload(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    customFields: Optional[Dict[str, Any]] = None

class WebhookService:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.leadconnector_webhook_url = os.getenv(
            "LEADCONNECTOR_WEBHOOK_URL",
            "https://services.leadconnectorhq.com/hooks/k7RoeQKT06Odv8RoFOjg/webhook-trigger/9ed9eac2-24d4-4fee-98d8-6009d2c452e2"
        )
        
        # Formatos de fecha soportados
        self.date_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%m/%d/%Y %H:%M',
            '%Y-%m-%d',
            '%m/%d/%Y'
        ]



class WebhookServiceDriverUs:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.leadconnector_webhook_url = os.getenv(
            "LEADCONNECTOR_WEBHOOK_URL",
            "https://services.leadconnectorhq.com/hooks/zmN2snXFkGxFawxaNH2Z/webhook-trigger/6028efbe-971c-4d11-89d6-07af21f65d73"
        )
        
        # Formatos de fecha soportados
        self.date_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%m/%d/%Y %H:%M',
            '%Y-%m-%d',
            '%m/%d/%Y'
        ]

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parsear fecha con múltiples formatos"""
        if not date_str:
            return None
            
        for fmt in self.date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def process_timing_data(self, data: Dict) -> TimingData:
        """Procesa los datos de tiempo del webhook"""
        timing_data = TimingData()
        timing_data.contact_id = data.get('contact_id')

        try:
            # Procesar fecha de creación
            creation_str = data.get('date_created') or data.get('Fecha de creación') or data.get('create date')
            create_date = self.parse_date(creation_str)
            
            # Procesar fecha de primera llamada
            first_call_str = data.get('Fecha/Hora primer llamada')
            first_call_date = self.parse_date(first_call_str)
            
            # Calcular diferencia
            if create_date and first_call_date:
                diferencia = first_call_date - create_date
                diferencia_minutos = diferencia.total_seconds() / 60
                
                self.logger.info(f"Fecha creación contacto: {create_date}")
                self.logger.info(f"Fecha/Hora primera llamada: {first_call_date}")
                self.logger.info(f"Tiempo entre creación y primera llamada (minutos): {diferencia_minutos:.2f}")
                
                timing_data.contact_creation = create_date.isoformat()
                timing_data.first_call = first_call_date.isoformat()
                timing_data.time_between_minutes = round(diferencia_minutos, 2)
            else:
                if not create_date:
                    self.logger.warning("Fecha de creación no encontrada")
                if not first_call_date:
                    self.logger.warning("Fecha de primera llamada no encontrada")
                    
        except Exception as e:
            self.logger.error(f"Error procesando fechas: {str(e)}", exc_info=True)
            
        return timing_data

    def create_response(self, timing_data: TimingData, call_count: int) -> Dict:
        """Crea la respuesta estructurada"""
        return {
            "status": "success",
            "message": "Webhook processed successfully",
            "timing_data": {
                "contact_creation": timing_data.contact_creation,
                "first_call": timing_data.first_call,
                "time_between_minutes": timing_data.time_between_minutes,
                "contact_id": timing_data.contact_id
            },
            "call_count": call_count
        }

    async def send_to_leadconnector(self, payload: Dict) -> Optional[Dict]:
        """Envía datos al webhook de LeadConnector"""
        headers = {
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.leadconnector_webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Error HTTP al enviar a LeadConnector: {e.response.text}")
        except Exception as e:
            self.logger.error(f"Error inesperado al enviar a LeadConnector: {str(e)}")
        return None

    def prepare_leadconnector_payload(self, data: Dict, timing_data: TimingData) -> Dict:
        """Prepara payload para LeadConnector"""
        return {
            "event_type": "contact_activity",
            "contact": {
                "email": data.get("email"),
                "phone": data.get("phone"),
                "name": data.get("name"),
                "custom_fields": {
                    "contact_creation": timing_data.contact_creation,
                    "first_call_time": timing_data.first_call,
                    "time_between_minutes": timing_data.time_between_minutes,
                    "call_count": data.get('Número de veces contactado', 0)
                }
            },
            "metadata": {
                "source": "fastapi_webhook",
                "processed_at": datetime.utcnow().isoformat()
            }
        }