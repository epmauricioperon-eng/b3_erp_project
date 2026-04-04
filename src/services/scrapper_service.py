import requests
import pandas as pd
from datetime import datetime
from src.utils.logger import get_logger
from io import StringIO

logger = get_logger(__name__)

class ProventosScraperService:
    """
    Serviço responsável por buscar dados de proventos futuros na web.
    Separado da UI (Streamlit) e dos Controllers de cálculo.
    """
    
    def __init__(self):
        # Sites financeiros bloqueiam robôs. Precisamos de um User-Agent de navegador real.
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }

    def buscar_ultimos_dividendos(self, ticker: str) -> pd.DataFrame:
        """
        Busca a tabela de dividendos. Tenta rota de FIIs, se falhar, tenta FIAGROs.
        """
        from io import StringIO
        
        rotas = [
            f"https://statusinvest.com.br/fundos-imobiliarios/{ticker.lower()}",
            f"https://statusinvest.com.br/fiagros/{ticker.lower()}"
        ]

        for url in rotas:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                
                # Se a página não existir (ex: erro 404), ele pula para o próximo except
                response.raise_for_status() 
                
                html_io = StringIO(response.text)
                tabelas = pd.read_html(html_io, decimal=',', thousands='.')
                
                if tabelas:
                    logger.info(f"Sucesso ao extrair tabela de {ticker} na URL: {url}")
                    return tabelas[0]
                    
            except requests.exceptions.RequestException:
                # Falhou nesta rota, o loop vai tentar a próxima
                continue
            except ValueError:
                continue

        logger.error(f"Nenhuma tabela encontrada para {ticker} nem como FII, nem como FIAGRO.")
        return pd.DataFrame()
        
        # --- BLOCO DE TESTE ISOLADO ---
# Adicione este bloco no final do arquivo src/services/scrapper_service.py

if __name__ == "__main__":
    import logging
    
    # Configuração básica de log apenas para visualizarmos no terminal durante este teste
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Iniciando teste isolado do Scraper de Dividendos...")
    
    # 1. Instanciamos o nosso serviço
    scraper = ProventosScraperService()
    
    # 2. Definimos o FII que queremos testar
    ticker_teste = "MXRF11"
    
    # 3. Executamos a extração
    df_resultado = scraper.buscar_ultimos_dividendos(ticker_teste)
    
    # 4. Avaliamos o resultado
    if not df_resultado.empty:
        logger.info(f"Tabela extraída com sucesso para {ticker_teste}! Inspecionando os dados:")
        
        # O print aqui é intencional apenas para visualizarmos o formato do DataFrame no terminal
        print("\n" + "="*50)
        print(df_resultado.head()) # Exibe as 5 primeiras linhas
        print("="*50 + "\n")
        
        logger.info("Colunas encontradas na tabela:")
        print(df_resultado.columns.tolist())
    else:
        logger.warning(f"O DataFrame retornou vazio para {ticker_teste}. O site pode ter bloqueado a requisição ou a estrutura da tabela mudou.")