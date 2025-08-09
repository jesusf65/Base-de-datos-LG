from datetime import datetime
from app.utils.date_parser import parse_date
from app.schemas.models import TimingData, WebhookResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import logging
import os


class WebhookService:
    def __init__(self, logger):
        self.logger = logger

    def process_timing_data(self, data: dict) -> TimingData:
        timing_data = TimingData(
            contact_creation=None,
            first_call=None,
            time_between_minutes=None,
            contact_id=data.get('contact_id')
        )

        try:
            # Procesar fechas
            creation_str = data.get('date_created') or data.get('Fecha de creación') or data.get('create date')
            create_date = parse_date(creation_str)
            
            first_call_str = data.get('Fecha/Hora primer llamada')
            first_call_date = parse_date(first_call_str)
            
            if create_date and first_call_date:
                diferencia = create_date - first_call_date
                diferencia_minutos = diferencia.total_seconds() / 60
                
                self.logger.info(f"Fecha creación contacto: {create_date}")
                self.logger.info(f"Fecha/Hora primera llamada: {first_call_date}")
                self.logger.info(f"Tiempo en minutos: {diferencia_minutos:.2f}")
                self.logger.info(f"contact_id: {data.get('contact_id')}")
                
                timing_data.contact_creation = create_date.isoformat()
                timing_data.first_call = first_call_date.isoformat()
                timing_data.time_between_minutes = round(diferencia_minutos, 2)
            else:
                if not create_date:
                    self.logger.warning("No se pudo obtener fecha de creación válida")
                if not first_call_date:
                    self.logger.warning("No se pudo obtener fecha de primera llamada válida")
                
        except Exception as date_error:
            self.logger.error(f"Error procesando fechas: {date_error}", exc_info=True)

        return timing_data

    def create_response(self, timing_data: TimingData, call_count: int) -> WebhookResponse:
        return WebhookResponse(
            status="success",
            message="Webhook received successfully",
            timing_data=timing_data,
            call_count=call_count
        )

class GHLContactPayload(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    customFields: Optional[Dict[str, Any]] = None


class WebhookService:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.leadconnector_webhook_url = os.getenv("LEADCONNECTOR_WEBHOOK_URL", 
                                    "https://services.leadconnectorhq.com/hooks/k7RoeQKT06Odv8RoFOjg/webhook-trigger/9ed9eac2-24d4-4fee-98d8-6009d2c452e2")

    async def send_to_leadconnector(self, payload: dict) -> Optional[dict]:
        """
        Envía datos al webhook específico de LeadConnector
        """
        headers = {
            "Content-Type": "application/json",
            "Version": "2021-07-28"  # Versión de API recomendada
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
            self.logger.error(f"Error de HTTP al enviar a LeadConnector: {e.response.text}")
        except Exception as e:
            self.logger.error(f"Error inesperado al enviar a LeadConnector: {str(e)}")
        return None

    def prepare_leadconnector_payload(self, original_data: dict, timing_data: dict) -> dict:
        """
        Prepara el payload específico para LeadConnector HQ
        """
        return {
            "event_type": "contact_activity",  # Tipo de evento personalizado
            "contact": {
                "email": original_data.get("email"),
                "phone": original_data.get("phone"),
                "name": original_data.get("name"),
                "custom_fields": {
                    "contact_creation": timing_data.get("contact_creation"),
                    "first_call_time": timing_data.get("first_call"),
                    "time_between_minutes": timing_data.get("time_between_minutes"),
                    "call_count": original_data.get("Número de veces contactado", 0)
                }
            },
            "metadata": {
                "source": "fastapi_webhook",
                "original_data": original_data  # Opcional: enviar datos originales
            }
        }