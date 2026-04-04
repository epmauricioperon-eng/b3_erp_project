import pandas as pd
from src.models.transacao_model import TransacaoModel
from src.models.dividendo_model import DividendoModel
from src.services.cotacao_service import CotacaoService
from src.services.pdf_service import PdfService
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TransacaoController:
    """Controlador unificado para gerenciar o ERP de Ativos B3."""
    
    def __init__(self):
        self.model = TransacaoModel()
        self.dividendo_model = DividendoModel()
        self.cotacao_service = CotacaoService()
        self.pdf_service = PdfService()

    def registrar_transacao(self, data_operacao: str, ticker: str, tipo: str, 
                            quantidade: int, preco_unitario: float, taxas: float) -> bool:
        try:
            if quantidade <= 0 or preco_unitario <= 0 or taxas < 0:
                logger.warning(f"Tentativa de registro inválido para {ticker}: Valores negativos/zerados.")
                return False
            if not ticker or len(ticker.strip()) < 4:
                logger.warning("Tentativa de registro com Ticker inválido.")
                return False
                
            return self.model.salvar_transacao(data_operacao, ticker, tipo, quantidade, preco_unitario, taxas)
        
        except Exception as e:
            logger.error(f"Controller: Erro ao registrar transação - {e}", exc_info=True)
            return False

    def excluir_transacao(self, id_transacao: str) -> bool:
        """Ponte para exclusão de um registro via ID."""
        try:
            if not id_transacao:
                return False
            return self.model.excluir_transacao(id_transacao)
        except Exception as e:
            logger.error(f"Controller: Erro ao excluir transação {id_transacao} - {e}", exc_info=True)
            return False

    def obter_historico(self) -> pd.DataFrame:
        try:
            df = self.model.obter_historico()
            
            if df is None or df.empty:
                return pd.DataFrame()
                
            if 'data_operacao' in df.columns:
                df['data_operacao'] = pd.to_datetime(df['data_operacao'], errors='coerce')
                df = df.sort_values(by='data_operacao', ascending=False)
            
            return df
            
        except Exception as e:
            logger.error(f"Controller: Erro ao processar histórico - {e}", exc_info=True)
            return pd.DataFrame()

    def obter_painel_consolidado(self) -> tuple:
        """Gera o painel mestre de ativos com cálculo de peso na carteira."""
        try:
            resumo = self.model.obter_resumo_carteira()
            df_posicao = self.model.obter_posicao_atual()

            # --- AQUI ESTÁ A DEFESA CONTRA A TELA VERMELHA ---
            if df_posicao is None or df_posicao.empty:
                logger.info("Nenhuma posição atual encontrada ou falha de conexão. Retornando painel zerado.")
                resumo_vazio = resumo if isinstance(resumo, dict) else {'total_investido': 0.0, 'qtd_ativos': 0}
                resumo_vazio.update({'saldo_atual': 0.0, 'rentabilidade_rs': 0.0, 'rentabilidade_pct': 0.0})
                return resumo_vazio, pd.DataFrame()

            tickers = df_posicao['ticker'].tolist()
            
            cotacoes_online = self.cotacao_service.obter_cotacoes_b3(tickers)
            if not cotacoes_online:
                logger.warning("Cotações online indisponíveis. Usando último preço médio como fallback.")
                df_posicao['preco_atual'] = df_posicao['preco_medio']
            else:
                df_posicao['preco_atual'] = df_posicao['ticker'].map(cotacoes_online).fillna(df_posicao['preco_medio'])

            df_posicao['valor_atual'] = df_posicao['quantidade_total'] * df_posicao['preco_atual']
            df_posicao['rentabilidade_rs'] = df_posicao['valor_atual'] - df_posicao['valor_total_investido']
            
            df_posicao['rentabilidade_pct'] = df_posicao.apply(
                lambda row: (row['rentabilidade_rs'] / row['valor_total_investido']) * 100 if row['valor_total_investido'] > 0 else 0,
                axis=1
            )

            saldo_atual = df_posicao['valor_atual'].sum()
            
            if saldo_atual > 0:
                df_posicao['peso_carteira'] = (df_posicao['valor_atual'] / saldo_atual) * 100
            else:
                df_posicao['peso_carteira'] = 0.0
                
            df_posicao['status_rebalanceamento'] = df_posicao['peso_carteira'].apply(
                lambda x: '🚨 Reduzir' if x > 15 else '✅ OK'
            )
            # --- CÁLCULO DO YIELD ON COST (YOC) ---
            df_div = self.obter_historico_completo_dividendos()
            if not df_div.empty and 'ticker' in df_div.columns and 'valor_total' in df_div.columns:
                # Agrupa e soma todos os dividendos já recebidos por cada fundo
                divs_agrupados = df_div.groupby('ticker')['valor_total'].sum().reset_index()
                divs_agrupados.rename(columns={'valor_total': 'total_dividendos_recebidos'}, inplace=True)
                
                # Une (Merge) a soma dos dividendos na nossa tabela principal da carteira
                df_posicao = pd.merge(df_posicao, divs_agrupados, on='ticker', how='left')
                
                # Fundos que nunca pagaram dividendos ficam com NaN, substituímos por zero
                df_posicao['total_dividendos_recebidos'] = df_posicao['total_dividendos_recebidos'].fillna(0)
            else:
                df_posicao['total_dividendos_recebidos'] = 0.0

            # A Matemática Final do YOC (%)
            df_posicao['yoc_pct'] = df_posicao.apply(
                lambda row: (row['total_dividendos_recebidos'] / row['valor_total_investido']) * 100 if row['valor_total_investido'] > 0 else 0.0,
                axis=1
            )
            # --------------------------------------
            total_investido = resumo.get('total_investido', 0.0)
            rentabilidade_total_rs = saldo_atual - total_investido
            rentabilidade_total_pct = (rentabilidade_total_rs / total_investido) * 100 if total_investido > 0 else 0.0

            resumo.update({
                'saldo_atual': saldo_atual,
                'rentabilidade_rs': rentabilidade_total_rs,
                'rentabilidade_pct': rentabilidade_total_pct
            })

            df_posicao = df_posicao.sort_values(by='peso_carteira', ascending=False)
            
            return resumo, df_posicao

        except Exception as e:
            logger.error(f"Controller: Falha crítica ao gerar painel consolidado - {e}", exc_info=True)
            return {'total_investido': 0.0, 'saldo_atual': 0.0, 'rentabilidade_rs': 0.0, 'rentabilidade_pct': 0.0}, pd.DataFrame()

    def gerar_relatorio_pdf(self) -> str:
        try:
            resumo, df_posicao = self.obter_painel_consolidado()
            return self.pdf_service.gerar_extrato_carteira(resumo, df_posicao)
        except Exception as e:
            logger.error(f"Controller: Erro ao acionar PdfService - {e}", exc_info=True)
            return ""

    def registrar_dividendo(self, data_pagamento: str, ticker: str, tipo_provento: str, 
                            quantidade_base: int, valor_unitario: float, valor_total: float) -> bool:
        try:
            if valor_total <= 0:
                return False
            if not ticker or len(ticker.strip()) < 4:
                return False
            return self.dividendo_model.salvar_dividendo(
                data_pagamento, ticker, tipo_provento, quantidade_base, valor_unitario, valor_total
            )
        except Exception as e:
            logger.error(f"Controller: Erro ao registrar dividendo - {e}", exc_info=True)
            return False

    def obter_resumo_dividendos_total(self) -> dict:
        try:
            return self.dividendo_model.obter_resumo_dividendos()
        except Exception as e:
            logger.error(f"Controller: Erro ao obter resumo de dividendos - {e}", exc_info=True)
            return {'total_recebido': 0.0}

    def obter_historico_completo_dividendos(self) -> pd.DataFrame:
        try:
            df = self.dividendo_model.obter_todos_dividendos()
            if df is None:
                return pd.DataFrame()
            return df
        except Exception as e:
            logger.error(f"Controller: Erro ao obter histórico de dividendos - {e}", exc_info=True)
            return pd.DataFrame()
        
    def excluir_dividendo(self, id_provento: str) -> bool:
        """Ponte para exclusão de um registro de dividendo via ID."""
        try:
            if not id_provento:
                return False
            return self.dividendo_model.excluir_dividendo(id_provento)
        except Exception as e:
            logger.error(f"Controller: Erro ao excluir dividendo {id_provento} - {e}", exc_info=True)
            return False