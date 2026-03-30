import logging
import os
from logging.handlers import RotatingFileHandler

# Garante que a pasta de logs exista
os.makedirs("logs", exist_ok=True)

# Configuração do manipulador de arquivo com rotação (Máx 5MB por arquivo, mantém os últimos 3)
file_handler = RotatingFileHandler(
    "logs/app.log", 
    mode='a', 
    maxBytes=5*1024*1024, 
    backupCount=3, 
    encoding="utf-8"
)

# Configuração base do Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        file_handler,
        logging.StreamHandler() # Continua mostrando no terminal
    ]
)

def get_logger(name: str) -> logging.Logger:
    """Retorna uma instância configurada do logger para o módulo solicitado."""
    return logging.getLogger(name)