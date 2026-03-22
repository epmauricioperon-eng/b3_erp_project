from pathlib import Path
import sys
import os
from dotenv import load_dotenv
import streamlit as st

# ==========================================
# BOOTSTRAP DO PROJETO
# ==========================================
ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Carrega o .env da raiz do projeto, se existir
load_dotenv(ROOT_DIR / ".env")


def get_secret(key: str, default=None):
    """Busca segredo primeiro no st.secrets e depois no .env"""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


def render_tela_login():
    """Desenha a interface de autenticação."""
    st.title("🔒 Acesso Restrito")
    st.markdown("Por favor, identifique-se para acessar o App de Investimentos.")

    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

        if submit:
            user_correto = get_secret("ADMIN_USER")
            senha_correta = get_secret("ADMIN_PASS")

            if usuario == user_correto and senha == senha_correta:
                st.success("Acesso liberado! Carregando sistema...")
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")


def main() -> None:
    """Ponto de entrada do sistema."""
    # Esse precisa ser o primeiro comando Streamlit
    st.set_page_config(page_title="ERP B3", page_icon="📈", layout="wide")

    try:
        # Importa módulos do projeto somente depois do bootstrap
        from src.utils.logger import get_logger
        from src.views.b3_view import render_main_page
        from src.controllers.transacao_controller import TransacaoController

        logger = get_logger(__name__)

        if "autenticado" not in st.session_state:
            st.session_state["autenticado"] = False

        if not st.session_state["autenticado"]:
            render_tela_login()
        else:
            logger.info("Iniciando o sistema B3 ERP...")

            with st.sidebar:
                if st.button("🚪 Sair do Sistema"):
                    st.session_state["autenticado"] = False
                    st.rerun()

            controller = TransacaoController()
            render_main_page(controller)

    except Exception as e:
        st.error(f"Erro fatal na inicialização da aplicação: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()