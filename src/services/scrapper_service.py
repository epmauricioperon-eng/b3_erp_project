import pandas as pd
import requests
from io import StringIO
import streamlit as st
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ProventosScraperService:
    """
    Serviço de extração de proventos focado no StatusInvest.
    Design limpo e direto para rodar em ambiente Localhost.
    """
    
    def __init__(self):
        # Cabeçalhos realistas para simular um navegador Chrome no Windows
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    # 2. COLOQUE ESTA ETIQUETA AQUI (Guarda na memória por 1 hora / 3600 segundos)
    
    @st.cache_data(ttl=3600)


    def buscar_ultimos_dividendos(_self, ticker: str) -> pd.DataFrame:
        ticker_limpo = str(ticker).strip().lower()
        
        # Mapeamento das 3 possíveis rotas de ativos no StatusInvest
        rotas = [
            f"https://statusinvest.com.br/fundos-imobiliarios/{ticker_limpo}",
            f"https://statusinvest.com.br/fiagros/{ticker_limpo}",
            f"https://statusinvest.com.br/acoes/{ticker_limpo}"
        ]

        for url in rotas:
            try:
                response = requests.get(url, headers=_self.headers, timeout=10)
                response.raise_for_status() 
                
                # Transforma o HTML em texto legível para o Pandas extrair as tabelas
                html_io = StringIO(response.text)
                tabelas = pd.read_html(html_io, decimal=',', thousands='.')
                
                if tabelas:
                    df_proventos = tabelas[0]
                    
                    # Validação de segurança: É realmente a tabela de dividendos?
                    if 'DATA COM' in df_proventos.columns and 'Pagamento' in df_proventos.columns:
                        logger.info(f"Proventos de {ticker.upper()} extraídos com sucesso da rota: {url}")
                        return df_proventos
                        
            except requests.exceptions.HTTPError as e:
                # O ativo não existe nessa categoria (ex: tentou FII, mas era Ação), pula pra próxima
                continue
            except Exception as e:
                logger.debug(f"Erro ao processar a rota {url} para {ticker}: {e}")
                continue

        logger.warning(f"Nenhuma tabela de proventos encontrada para {ticker.upper()}.")
        return pd.DataFrame()