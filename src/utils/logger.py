import logging
import os

# Garante que a pasta de logs exista
os.makedirs("logs", exist_ok=True)

# Configuração base do Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", encoding="utf-8"),
        logging.StreamHandler() # Continua mostrando no terminal para facilitar o debug
    ]
)

def get_logger(name: str) -> logging.Logger:
    """Retorna uma instância configurada do logger para o módulo solicitado."""
    return logging.getLogger(name)