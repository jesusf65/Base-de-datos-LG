from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import logging
import os
import pytz
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
        
        self.date_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%m/%d/%Y %H:%M',
            '%Y-%m-%d',
            '%m/%d/%Y'
        ]
        self.gmt5 = pytz.timezone('America/Bogota')

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parsear fecha con múltiples formatos y convertir a GMT-5"""
        if not date_str:
            return None
            
        for fmt in self.date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                
                # Si la fecha está en UTC (formato ISO con 'Z')
                if fmt.endswith('Z'):
                    utc_date = pytz.utc.localize(parsed_date)
                    return utc_date.astimezone(self.gmt5)
                else:
                    # Asumir que la fecha está en GMT-5 (sin zona horaria)
                    return self.gmt5.localize(parsed_date)
                    
            except ValueError:
                continue
        return None

    def process_timing_data(self, data: Dict) -> TimingData:
        """Procesa los datos de tiempo con zona horaria GMT-5"""
        timing_data = TimingData()
        timing_data.contact_id = data.get('contact_id')

        try:
            # Procesar fechas con zona horaria
            create_date = self.parse_date(data.get('date_created'))
            first_call_date = self.parse_date(data.get('Fecha/Hora primer llamada'))
            
            if create_date and first_call_date:
                # Asegurarse de que ambas fechas están en GMT-5
                create_date = create_date.astimezone(self.gmt5)
                first_call_date = first_call_date.astimezone(self.gmt5)
                
                diferencia = first_call_date - create_date
                diferencia_minutos = diferencia.total_seconds() / 60
                
                # Registrar fechas ya en GMT-5
                self.logger.info(f"Fecha creación contacto (GMT-5): {create_date}")
                self.logger.info(f"Fecha primera llamada (GMT-5): {first_call_date}")
                self.logger.info(f"Tiempo entre eventos (minutos): {diferencia_minutos:.2f}")
                
                timing_data.contact_creation = create_date.isoformat()
                timing_data.first_call = first_call_date.isoformat()
                timing_data.time_between_minutes = round(diferencia_minutos, 2)
                
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


class WebhookServiceDriverUs:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.leadconnector_webhook_url = os.getenv(
            "LEADCONNECTOR_WEBHOOK_URL",
            "https://services.leadconnectorhq.com/hooks/zmN2snXFkGxFawxaNH2Z/webhook-trigger/cb471924-37ca-4e3c-a13d-4c821d851c3e"
        )
        
        self.date_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%m/%d/%Y %H:%M',
            '%Y-%m-%d',
            '%m/%d/%Y'
        ]
        self.gmt5 = pytz.timezone('America/Bogota')

    def parse_dates(self, date_str: str) -> Optional[datetime]:
        """Parsear fecha con múltiples formatos y convertir a GMT-5"""
        if not date_str:
            return None
            
        for fmt in self.date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                
                # Si la fecha está en UTC (formato ISO con 'Z')
                if fmt.endswith('Z'):
                    utc_date = pytz.utc.localize(parsed_date)
                    return utc_date.astimezone(self.gmt5)
                else:
                    # Asumir que la fecha está en GMT-5 (sin zona horaria)
                    return self.gmt5.localize(parsed_date)
                    
            except ValueError:
                continue
        return None

    def process_timing_datas(self, data: Dict) -> TimingData:
        """Procesa los datos de tiempo con zona horaria GMT-5"""
        timing_data = TimingData()
        timing_data.contact_id = data.get('contact_id')

        try:
            # Procesar fechas con zona horaria
            create_date = self.parse_dates(data.get('date_created'))
            first_call_date = self.parse_dates(data.get('Fecha/Hora primer llamada'))
            
            if create_date and first_call_date:
                create_date = create_date.astimezone(self.gmt5)
                first_call_date = first_call_date.astimezone(self.gmt5)
                
                diferencia = first_call_date - create_date
                diferencia_minutos = diferencia.total_seconds() / 60
                
                # Registrar fechas ya en GMT-5
                self.logger.info(f"Fecha creación contacto (GMT-5): {create_date}")
                self.logger.info(f"Fecha primera llamada (GMT-5): {first_call_date}")
                self.logger.info(f"Tiempo entre eventos (minutos): {diferencia_minutos:.2f}")
                
                timing_data.contact_creation = create_date.isoformat()
                timing_data.first_call = first_call_date.isoformat()
                timing_data.time_between_minutes = round(diferencia_minutos, 2)
                
        except Exception as e:
            self.logger.error(f"Error procesando fechas: {str(e)}", exc_info=True)
            
        return timing_data

    def create_responses(self, timing_data: TimingData, call_count: int) -> Dict:
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

    async def send_to_leadconnectors(self, payload: Dict) -> Optional[Dict]:
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

    def prepare_leadconnector_payloads(self, data: Dict, timing_data: TimingData) -> Dict:
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

webhooks_services = WebhookServiceDriverUs