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
        if quantidade <= 0 or preco_unitario <= 0 or taxas < 0:
            return False
        if not ticker or len(ticker) < 4:
            return False
        return self.model.salvar_transacao(data_operacao, ticker, tipo, quantidade, preco_unitario, taxas)

    def obter_historico(self) -> pd.DataFrame:
        df = self.model.obter_historico()
        if not df.empty:
            df['data_operacao'] = pd.to_datetime(df['data_operacao'])
            df = df.sort_values(by='data_operacao', ascending=False)
        return df

    def obter_painel_consolidado(self) -> tuple:
        """Gera o painel mestre de ativos com cálculo de peso na carteira."""
        resumo = self.model.obter_resumo_carteira()
        df_posicao = self.model.obter_posicao_atual()

        if df_posicao.empty:
            resumo.update({'saldo_atual': 0.0, 'rentabilidade_rs': 0.0, 'rentabilidade_pct': 0.0})
            return resumo, df_posicao

        tickers = df_posicao['ticker'].tolist()
        cotacoes_online = self.cotacao_service.obter_cotacoes_b3(tickers)

        df_posicao['preco_atual'] = df_posicao['ticker'].map(cotacoes_online)
        df_posicao['valor_atual'] = df_posicao['quantidade_total'] * df_posicao['preco_atual']
        
        df_posicao['rentabilidade_rs'] = df_posicao['valor_atual'] - df_posicao['valor_total_investido']
        df_posicao['rentabilidade_pct'] = (df_posicao['rentabilidade_rs'] / df_posicao['valor_total_investido']) * 100

        saldo_atual = df_posicao['valor_atual'].sum()
        
        # --- NOVA LÓGICA: CÁLCULO DE PESO E REGRA DOS 15% ---
        if saldo_atual > 0:
            df_posicao['peso_carteira'] = (df_posicao['valor_atual'] / saldo_atual) * 100
        else:
            df_posicao['peso_carteira'] = 0.0
            
        # Regra de negócio do Mauricio: Alerta visual se passar de 15%
        df_posicao['status_rebalanceamento'] = df_posicao['peso_carteira'].apply(
            lambda x: '🚨 Reduzir' if x > 15 else '✅ OK'
        )
        # ----------------------------------------------------

        rentabilidade_total_rs = saldo_atual - resumo['total_investido']
        rentabilidade_total_pct = 0.0
        if resumo['total_investido'] > 0:
            rentabilidade_total_pct = (rentabilidade_total_rs / resumo['total_investido']) * 100

        resumo.update({
            'saldo_atual': saldo_atual,
            'rentabilidade_rs': rentabilidade_total_rs,
            'rentabilidade_pct': rentabilidade_total_pct
        })

        # Ordena pelos ativos mais pesados primeiro
        df_posicao = df_posicao.sort_values(by='peso_carteira', ascending=False)
        return resumo, df_posicao

    def gerar_relatorio_pdf(self) -> str:
        resumo, df_posicao = self.obter_painel_consolidado()
        return self.pdf_service.gerar_extrato_carteira(resumo, df_posicao)

    def registrar_dividendo(self, data_pagamento: str, ticker: str, tipo_provento: str, 
                            quantidade_base: int, valor_unitario: float, valor_total: float) -> bool:
        if valor_total <= 0:
            return False
        if not ticker or len(ticker) < 4:
            return False
        return self.dividendo_model.salvar_dividendo(
            data_pagamento, ticker, tipo_provento, quantidade_base, valor_unitario, valor_total
        )

    def obter_resumo_dividendos_total(self) -> dict:
        return self.dividendo_model.obter_resumo_dividendos()

    def obter_historico_completo_dividendos(self) -> pd.DataFrame:
        return self.dividendo_model.obter_todos_dividendos()