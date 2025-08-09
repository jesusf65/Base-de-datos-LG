from datetime import datetime
from app.utils.date_parser import parse_date
from app.schemas.models import TimingData, WebhookResponse

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
                diferencia = first_call_date - create_date
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