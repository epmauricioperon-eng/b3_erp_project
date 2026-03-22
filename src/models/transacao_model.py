import pandas as pd
import gspread
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TransacaoModel:
    """Modelo conectado ao Google Sheets para transações."""
    
    def __init__(self):
        try:
            # Conecta usando a chave do robô
            self.gc = gspread.service_account(filename="credenciais_google.json")
            self.planilha = self.gc.open("ERP_B3_Database")
            self.worksheet = self.planilha.worksheet("Transacoes")
            logger.info("Conexão com Google Sheets (Transações) estabelecida com sucesso!")
        except Exception as e:
            logger.error(f"Erro fatal ao conectar no Google Sheets: {e}")

    def salvar_transacao(self, data_operacao: str, ticker: str, tipo: str, 
                         quantidade: int, preco_unitario: float, taxas: float) -> bool:
        try:
            total_operacao = (quantidade * preco_unitario) + taxas if tipo == "COMPRA" else (quantidade * preco_unitario) - taxas
            id_transacao = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # Prepara a nova linha (na exata ordem das colunas do seu Sheets)
            nova_linha = [id_transacao, data_operacao, ticker, tipo, quantidade, preco_unitario, taxas, total_operacao]
            
            # Manda para a nuvem!
            self.worksheet.append_row(nova_linha)
            logger.info(f"Sucesso: {tipo} de {ticker} salva na Nuvem!")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar na Nuvem: {e}", exc_info=True)
            return False

    def obter_historico(self) -> pd.DataFrame:
        try:
            dados = self.worksheet.get_all_records()
            if not dados:
                return pd.DataFrame()
            
            df = pd.DataFrame(dados)
            # Garante que o Pandas entenda os números corretamente
            colunas_numericas = ['quantidade', 'preco_unitario', 'taxas', 'total_operacao']
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        except Exception as e:
            logger.error(f"Erro ao ler histórico da Nuvem: {e}")
            return pd.DataFrame()

    def obter_resumo_carteira(self) -> dict:
        df = self.obter_historico()
        if df.empty:
            return {"total_investido": 0.0, "qtd_ativos": 0}
        
        df_compras = df[df['tipo'] == 'COMPRA']
        total = df_compras['total_operacao'].sum()
        ativos_unicos = df['ticker'].nunique()
        return {"total_investido": float(total), "qtd_ativos": int(ativos_unicos)}

    def obter_posicao_atual(self) -> pd.DataFrame:
        df = self.obter_historico()
        if df.empty:
            return pd.DataFrame()

        df_compras = df[df['tipo'] == 'COMPRA'].copy()
        if df_compras.empty:
            return pd.DataFrame()

        carteira = df_compras.groupby('ticker').agg(
            quantidade_total=('quantidade', 'sum'),
            valor_total_investido=('total_operacao', 'sum')
        ).reset_index()

        carteira['preco_medio'] = carteira['valor_total_investido'] / carteira['quantidade_total']
        return carteira
    