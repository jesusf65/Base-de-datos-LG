import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Ruta donde se guardarán los logs
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def setup_logger(name: str, log_file: str = None, level=logging.INFO):
    """
    Configura y devuelve un logger con salida en consola y archivo.

    :param name: Nombre del logger.
    :param log_file: Nombre del archivo de log (opcional). Si no se pasa, no guarda en archivo.
    :param level: Nivel de log (default INFO).
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar handlers duplicados si ya está configurado
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler para archivo (si se especifica)
    if log_file:
        file_path = LOGS_DIR / log_file
        file_handler = RotatingFileHandler(
            file_path, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
