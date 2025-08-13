from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import logging
import os
import pytz

class TimingData:
    def __init__(self):
        self.Call_AIRCALL = None
        self.Call_CRM = None
        self.date_created = None
        self.time_between_minutes = None
        self.contact_id = None
        self.contact_creation = None
        self.first_call = None

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
            '%Y-%m-%dT%H:%M:%S.%fZ',  # Formato ISO UTC
            '%m/%d/%Y %H:%M',         # Formato con hora
            '%Y-%m-%d',               # Fecha simple
            '%m/%d/%Y'                # Formato americano
        ]
        self.miami_tz = pytz.timezone('America/New_York')  # Zona horaria de Miami

    def parse_date(self, date_str: str, subtract_hours: int = 4) -> Optional[datetime]:
        """Parsear fecha con múltiples formatos, convertir a Miami time y restar horas"""
        if not date_str:
            return None
            
        for fmt in self.date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                
                # Si la fecha está en UTC (formato ISO con 'Z')
                if fmt.endswith('Z'):
                    utc_date = pytz.utc.localize(parsed_date)
                    miami_time = utc_date.astimezone(self.miami_tz)
                    return miami_time - timedelta(hours=subtract_hours)
                else:
                    # Asumir que la fecha está en Miami time (sin zona horaria)
                    return self.miami_tz.localize(parsed_date)
                    
            except ValueError:
                continue
        return None

    def unix_to_miami(self, unix_timestamp: str, is_milliseconds: bool = True) -> Optional[datetime]:
        """Convertir timestamp UNIX a Miami time"""
        if not unix_timestamp:
            return None
        
        try:
            timestamp = float(unix_timestamp)
            if is_milliseconds:
                timestamp /= 1000  # Convertir a segundos
            
            utc_date = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)
            return utc_date.astimezone(self.miami_tz)
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error convirtiendo timestamp UNIX: {str(e)}")
            return None

    def process_timing_data(self, data: Dict) -> TimingData:
        """Procesa los datos de tiempo con zona horaria de Miami"""
        timing_data = TimingData()
        timing_data.contact_id = data.get('contact_id')

        try:
            # Procesar date_created (restar 4 horas)
            create_date = self.parse_date(data.get('date_created'))
            
            # Procesar Call_AIRCALL (timestamp UNIX)
            call_aircall = data.get('Call_AIRCALL')
            first_call_date = self.unix_to_miami(call_aircall) if call_aircall else None
            
            # Si no hay Call_AIRCALL, intentar con Call_CRM
            if not first_call_date:
                first_call_date = self.parse_date(data.get('Call_CRM'))
            
            if create_date and first_call_date:
                # Asegurarse de que ambas fechas están en Miami time
                create_date = create_date.astimezone(self.miami_tz)
                first_call_date = first_call_date.astimezone(self.miami_tz)
                
                diferencia = first_call_date - create_date
                diferencia_minutos = diferencia.total_seconds() / 60
                
                self.logger.info(f"Fecha creación contacto (Miami -4h): {create_date}")
                self.logger.info(f"Fecha primera llamada (Miami): {first_call_date}")
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