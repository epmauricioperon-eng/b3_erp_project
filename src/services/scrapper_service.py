import pandas as pd
import requests
from io import StringIO
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ProventosScraperService:
    """
    Serviço de extração de proventos utilizando o Fundamentus.
    O Fundamentus é um portal de HTML simples que raramente bloqueia IPs de Nuvem (Datacenters),
    sendo ideal para deploys gratuitos no Streamlit Cloud.
    """
    
    def __init__(self):
        # Um cabeçalho simples fingindo ser um navegador comum já é suficiente aqui
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def buscar_ultimos_dividendos(self, ticker: str) -> pd.DataFrame:
        """
        Acessa a página de proventos do Fundamentus, extrai a tabela e formata as 
        colunas para manter a retrocompatibilidade com o Controller atual.
        """
        # A URL direta para a tabela de proventos de qualquer ativo no Fundamentus
        url = f"https://www.fundamentus.com.br/proventos.php?papel={ticker.upper()}&tipo=2"

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status() 
            
            html_io = StringIO(response.text)
            
            # O Fundamentus já usa o padrão brasileiro de números (vírgula para decimal)
            tabelas = pd.read_html(html_io, decimal=',', thousands='.')
            
            if tabelas and not tabelas[0].empty:
                df = tabelas[0]
                
                # O Fundamentus retorna: ['Data', 'Valor', 'Tipo', 'Data de Pagamento', 'Por quantas ações']
                # Precisamos traduzir para a "Língua" que o nosso Controller já entende:
                df.rename(columns={
                    'Data': 'DATA COM',
                    'Data de Pagamento': 'Pagamento',
                    'Valor': 'Valor',
                    'Tipo': 'Tipo'
                }, inplace=True)
                
                # Como o Fundamentus pode trazer os dados fora de ordem, forçamos a ordenação
                # do mais recente para o mais antigo usando a 'DATA COM'
                df['Data_Temp'] = pd.to_datetime(df['DATA COM'], format='%d/%m/%Y', errors='coerce')
                df = df.sort_values(by='Data_Temp', ascending=False).drop(columns=['Data_Temp'])
                
                logger.info(f"Sucesso ao extrair tabela do Fundamentus para {ticker}")
                return df
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede ao acessar Fundamentus para {ticker}: {e}")
        except Exception as e:
            logger.error(f"Erro ao processar dados do Fundamentus para {ticker}: {e}")

        return pd.DataFrame()


# --- BLOCO DE TESTE ISOLADO ---
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    logger.info("Iniciando teste isolado do Scraper via Fundamentus...")
    scraper = ProventosScraperService()
    
    ticker_teste = "MXRF11"
    df_resultado = scraper.buscar_ultimos_dividendos(ticker_teste)
    
    if not df_resultado.empty:
        logger.info(f"Tabela extraída com sucesso para {ticker_teste}!")
        print(df_resultado.head(3))
    else:
        logger.warning(f"O DataFrame retornou vazio para {ticker_teste}.")