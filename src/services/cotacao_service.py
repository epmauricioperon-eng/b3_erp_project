import yfinance as yf
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CotacaoService:
    """Serviço para buscar cotações em tempo real de APIs externas."""
    
    def obter_cotacoes_b3(self, tickers: list) -> dict:
        """Busca o preço atual de uma lista de tickers da B3."""
        cotacoes = {}
        logger.info(f"Service: Buscando cotações online para {len(tickers)} ativos...")
        
        for ticker in tickers:
            try:
                # O Yahoo Finance exige o sufixo .SA para a bolsa brasileira
                acao = yf.Ticker(f"{ticker}.SA")
                historico = acao.history(period="1d")
                
                if not historico.empty:
                    # Pega o último preço de fechamento/atual
                    preco_atual = float(historico['Close'].iloc[-1])
                    cotacoes[ticker] = round(preco_atual, 2)
                else:
                    logger.warning(f"Service: Sem dados para {ticker}.")
                    cotacoes[ticker] = 0.0
                    
            except Exception as e:
                logger.error(f"Service: Falha ao buscar cotação de {ticker}: {e}")
                cotacoes[ticker] = 0.0
                
        return cotacoes