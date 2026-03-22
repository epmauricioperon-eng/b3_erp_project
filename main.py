import streamlit as st
import os
from dotenv import load_dotenv
from src.utils.logger import get_logger
from src.views.b3_view import render_main_page
from src.controllers.transacao_controller import TransacaoController

# Carrega as senhas secretas do arquivo .env
load_dotenv()

logger = get_logger(__name__)

def render_tela_login():
    """Desenha a interface de autenticação."""
    st.title("🔒 Acesso Restrito")
    st.markdown("Por favor, identifique-se para acessar o App de Investimentos.")

    # O formulário de login
    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password") # Esconde o que é digitado
        submit = st.form_submit_button("Entrar")

        if submit:
            # Busca as credenciais seguras que estão no .env
            user_correto = os.getenv("ADMIN_USER")
            senha_correta = os.getenv("ADMIN_PASS")

            if usuario == user_correto and senha == senha_correta:
                st.success("Acesso liberado! Carregando sistema...")
                st.session_state['autenticado'] = True
                st.rerun() # Recarrega a página agora com acesso liberado
            else:
                st.error("Usuário ou senha incorretos.")

def main() -> None:
    """Ponto de entrada do sistema."""
    try:
        # Configuração global da página TEM que ser o primeiro comando do Streamlit
        st.set_page_config(page_title="ERP B3", page_icon="📈", layout="wide")

        # Inicializa o estado de segurança na memória do navegador
        if 'autenticado' not in st.session_state:
            st.session_state['autenticado'] = False

        # O Roteador (Guard)
        if not st.session_state['autenticado']:
            render_tela_login()
        else:
            logger.info("Iniciando o sistema B3 ERP...")
            
            # Botão de Logout rápido na barra lateral
            with st.sidebar:
                if st.button("🚪 Sair do Sistema"):
                    st.session_state['autenticado'] = False
                    st.rerun()

            controller = TransacaoController()
            render_main_page(controller)

    except Exception as e:
        logger.error(f"Erro fatal na inicialização da aplicação: {e}", exc_info=True)

if __name__ == "__main__":
    main()