from datetime import datetime
import pytz  

DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%fZ',  # Formato ISO (UTC)
    '%m/%d/%Y %H:%M',         # Formato Fecha/Hora primer llamada
    '%Y-%m-%d',               # Formato simple de fecha
    '%m/%d/%Y'                # Formato americano simple
]

def parse_date(date_str, formats=DATE_FORMATS):
    """Intenta parsear una fecha usando múltiples formatos y la convierte a Miami (GMT-5/GMT-4)."""
    if not date_str:
        return None
        
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            # Si la fecha está en UTC (formato ISO con 'Z'), la convertimos a Miami
            if fmt.endswith('Z'):
                utc_date = pytz.utc.localize(parsed_date)
                miami_tz = pytz.timezone('America/New_York')  # Miami usa esta zona
                return utc_date.astimezone(miami_tz)
            else:
                # Asumimos que la fecha ya está en Miami (sin info de zona horaria)
                return pytz.timezone('America/New_York').localize(parsed_date)
        except ValueError:
            continue
    return None