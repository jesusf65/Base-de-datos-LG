from datetime import datetime
import pytz  # Requiere instalación: pip install pytz

DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%fZ',  # Formato ISO (UTC)
    '%m/%d/%Y %H:%M',         # Formato Fecha/Hora primer llamada
    '%Y-%m-%d',               # Formato simple de fecha
    '%m/%d/%Y'                # Formato americano simple
]

def parse_date(date_str, formats=DATE_FORMATS):
    """Intenta parsear una fecha usando múltiples formatos y la convierte a GMT-5."""
    if not date_str:
        return None
        
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            # Si la fecha está en UTC (formato ISO con 'Z'), la convertimos a GMT-5
            if fmt.endswith('Z'):
                utc_date = pytz.utc.localize(parsed_date)
                gmt5 = pytz.timezone('America/Bogota')  # GMT-5 (Colombia)
                return utc_date.astimezone(gmt5)
            else:
                # Asumimos que la fecha ya está en GMT-5 (sin información de zona horaria)
                return pytz.timezone('America/Bogota').localize(parsed_date)
        except ValueError:
            continue
    return None