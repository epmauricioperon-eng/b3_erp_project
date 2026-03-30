import pandas as pd
from src.utils.logger import get_logger
from src.utils.google_sheets import open_worksheet

logger = get_logger(__name__)


class DividendoModel:
    """Modelo conectado ao Google Sheets para dividendos."""

    def __init__(self):
        self.gc = None
        self.planilha = None
        self.worksheet = None
        self.disponivel = False

        self.gc, self.planilha, self.worksheet = open_worksheet("Dividendos")
        self.disponivel = self.worksheet is not None

        if not self.disponivel:
            logger.warning("DividendoModel iniciado sem conexão com a aba 'Dividendos'.")

    def _worksheet_pronto(self) -> bool:
        if self.worksheet is None:
            logger.error("Worksheet 'Dividendos' não está inicializado.")
            return False
        return True

    def salvar_dividendo(
        self,
        data_pagamento: str,
        ticker: str,
        tipo_provento: str,
        quantidade_base: int,
        valor_unitario: float,
        valor_total: float
    ) -> bool:
        if not self._worksheet_pronto():
            return False

        try:
            nova_linha = [
                data_pagamento,
                str(ticker).upper().strip(),
                str(tipo_provento).upper().strip(),
                quantidade_base,
                valor_unitario,
                valor_total
            ]

            self.worksheet.append_row(nova_linha)
            logger.info(f"Dividendo de {ticker} salvo com sucesso.")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar dividendo: {e}", exc_info=True)
            return False

    def obter_todos_dividendos(self) -> pd.DataFrame:
        if not self._worksheet_pronto():
            return pd.DataFrame()

        try:
            dados = self.worksheet.get_all_records()
            if not dados:
                return pd.DataFrame()

            df = pd.DataFrame(dados)

            # Padroniza os nomes das colunas
            df.columns = [str(col).strip().lower() for col in df.columns]

            colunas_numericas = ["quantidade_base", "valor_unitario", "valor_total"]
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            if "data_pagamento" in df.columns:
                df["data_pagamento"] = pd.to_datetime(df["data_pagamento"], errors="coerce")
                df["ano"] = df["data_pagamento"].dt.year
                df["mes_nome"] = df["data_pagamento"].dt.strftime("%B")
                df["mes_numero"] = df["data_pagamento"].dt.month

            return df

        except Exception as e:
            logger.error(f"Erro ao ler dividendos: {e}", exc_info=True)
            return pd.DataFrame()

    def obter_resumo_dividendos(self) -> dict:
        df = self.obter_todos_dividendos()
        if df.empty or "valor_total" not in df.columns:
            return {"total_recebido": 0.0}

        total = df["valor_total"].sum()
        return {"total_recebido": float(total)}
    
    def excluir_dividendo(self, id_provento: str) -> bool:
        """Localiza e remove uma linha da aba de Dividendos baseada no ID único."""
        if not self._worksheet_pronto():
            return False
            
        try:
            todas_as_linhas = self.worksheet.get_all_values()
            linha_para_excluir = -1
            
            # Procura o ID (assumindo que o ID do provento está na primeira coluna - índice 0)
            for i, linha in enumerate(todas_as_linhas):
                if str(linha[0]) == str(id_provento):
                    linha_para_excluir = i + 1 
                    break

            if linha_para_excluir != -1:
                self.worksheet.delete_rows(linha_para_excluir)
                logger.info(f"Dividendo ID {id_provento} excluído com sucesso.")
                return True
                
            logger.warning(f"Dividendo ID {id_provento} não encontrado para exclusão.")
            return False

        except Exception as e:
            logger.error(f"Erro ao excluir dividendo {id_provento}: {e}", exc_info=True)
            return False