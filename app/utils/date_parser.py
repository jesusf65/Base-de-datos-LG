from datetime import datetime

DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%fZ',  # Formato ISO (date_created)
    '%m/%d/%Y %H:%M',         # Formato Fecha/Hora primer llamada
    '%Y-%m-%d',               # Formato simple de fecha
    '%m/%d/%Y'                # Formato americano simple
]

def parse_date(date_str, formats=DATE_FORMATS):
    """Intenta parsear una fecha usando múltiples formatos"""
    if not date_str:
        return None
        
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None