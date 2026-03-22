import pandas as pd
from datetime import datetime
from src.utils.logger import get_logger
from src.utils.google_sheets import open_worksheet

logger = get_logger(__name__)


class TransacaoModel:
    """Modelo conectado ao Google Sheets para transações."""

    def __init__(self):
        self.gc = None
        self.planilha = None
        self.worksheet = None
        self.disponivel = False

        self.gc, self.planilha, self.worksheet = open_worksheet("Transacoes")
        self.disponivel = self.worksheet is not None

        if not self.disponivel:
            logger.warning("TransacaoModel iniciado sem conexão com a aba 'Transacoes'.")

    def _worksheet_pronto(self) -> bool:
        if self.worksheet is None:
            logger.error("Worksheet 'Transacoes' não está inicializado.")
            return False
        return True

    def salvar_transacao(
        self,
        data_operacao: str,
        ticker: str,
        tipo: str,
        quantidade: int,
        preco_unitario: float,
        taxas: float
    ) -> bool:
        if not self._worksheet_pronto():
            return False

        try:
            ticker = str(ticker).upper().strip()
            tipo = str(tipo).upper().strip()

            total_operacao = (
                (quantidade * preco_unitario) + taxas
                if tipo == "COMPRA"
                else (quantidade * preco_unitario) - taxas
            )

            id_transacao = datetime.now().strftime("%Y%m%d%H%M%S")

            nova_linha = [
                id_transacao,
                data_operacao,
                ticker,
                tipo,
                quantidade,
                preco_unitario,
                taxas,
                total_operacao
            ]

            self.worksheet.append_row(nova_linha)
            logger.info(f"Sucesso: {tipo} de {ticker} salva no Google Sheets.")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar transação: {e}", exc_info=True)
            return False

    def obter_historico(self) -> pd.DataFrame:
        if not self._worksheet_pronto():
            return pd.DataFrame()

        try:
            dados = self.worksheet.get_all_records()
            if not dados:
                return pd.DataFrame()

            df = pd.DataFrame(dados)

            # Padroniza os nomes das colunas
            df.columns = [str(col).strip().lower() for col in df.columns]

            colunas_numericas = ["quantidade", "preco_unitario", "taxas", "total_operacao"]
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            return df

        except Exception as e:
            logger.error(f"Erro ao ler histórico da aba 'Transacoes': {e}", exc_info=True)
            return pd.DataFrame()

    def obter_resumo_carteira(self) -> dict:
        df = self.obter_historico()
        if df.empty:
            return {"total_investido": 0.0, "qtd_ativos": 0}

        if "tipo" not in df.columns or "total_operacao" not in df.columns or "ticker" not in df.columns:
            logger.error("Colunas esperadas não encontradas na aba 'Transacoes'.")
            return {"total_investido": 0.0, "qtd_ativos": 0}

        df_compras = df[df["tipo"] == "COMPRA"]
        total = df_compras["total_operacao"].sum()
        ativos_unicos = df["ticker"].nunique()

        return {
            "total_investido": float(total),
            "qtd_ativos": int(ativos_unicos)
        }

    def obter_posicao_atual(self) -> pd.DataFrame:
        df = self.obter_historico()
        if df.empty:
            return pd.DataFrame()

        colunas_necessarias = {"tipo", "ticker", "quantidade", "total_operacao"}
        if not colunas_necessarias.issubset(df.columns):
            logger.error("Colunas obrigatórias ausentes para montar posição atual.")
            return pd.DataFrame()

        df_compras = df[df["tipo"] == "COMPRA"].copy()
        if df_compras.empty:
            return pd.DataFrame()

        carteira = df_compras.groupby("ticker").agg(
            quantidade_total=("quantidade", "sum"),
            valor_total_investido=("total_operacao", "sum")
        ).reset_index()

        carteira["preco_medio"] = (
            carteira["valor_total_investido"] / carteira["quantidade_total"]
        )

        return carteira