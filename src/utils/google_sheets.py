from pathlib import Path
import gspread
import streamlit as st
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CRED_FILE = PROJECT_ROOT / "credenciais_google.json"
SHEET_NAME = "ERP_B3_Database"


def get_gspread_client():
    """
    Cria o cliente do Google Sheets.
    Prioridade:
    1) Streamlit Secrets
    2) Arquivo local credenciais_google.json
    """
    try:
        if "google_credentials" in st.secrets:
            credenciais_dict = dict(st.secrets["google_credentials"])
            logger.info("Google Sheets autenticado via Streamlit Secrets.")
            return gspread.service_account_from_dict(credenciais_dict)

        if CRED_FILE.exists():
            logger.info(f"Google Sheets autenticado via arquivo local: {CRED_FILE}")
            return gspread.service_account(filename=str(CRED_FILE))

        raise FileNotFoundError(
            f"Credenciais não encontradas. "
            f"Configure st.secrets['google_credentials'] "
            f"ou crie o arquivo local em: {CRED_FILE}"
        )

    except Exception as e:
        logger.error(f"Erro ao criar cliente do Google Sheets: {e}", exc_info=True)
        return None


def open_worksheet(tab_name: str):
    """
    Abre uma aba específica da planilha principal.
    Retorna: (gc, planilha, worksheet)
    """
    gc = get_gspread_client()
    if gc is None:
        return None, None, None

    try:
        planilha = gc.open(SHEET_NAME)
        worksheet = planilha.worksheet(tab_name)
        logger.info(f"Aba '{tab_name}' aberta com sucesso.")
        return gc, planilha, worksheet

    except Exception as e:
        logger.error(
            f"Erro ao abrir planilha '{SHEET_NAME}' / aba '{tab_name}': {e}",
            exc_info=True
        )
        return gc, None, None