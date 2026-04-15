import pandas as pd
import streamlit as st
from src.utils.logger import get_logger
from src.utils.google_sheets import open_worksheet

logger = get_logger(__name__)

def limpar_numero(valor) -> float:
    if pd.isna(valor) or valor == '' or valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    v_str = str(valor).strip().replace('R$', '').replace(' ', '')
    if '.' in v_str and ',' in v_str:
        v_str = v_str.replace('.', '').replace(',', '.')
    elif ',' in v_str:
        v_str = v_str.replace(',', '.')
    try:
        return float(v_str)
    except:
        return 0.0

class DividendoModel:
    def __init__(self):
        self.gc, self.planilha, self.worksheet = open_worksheet("Dividendos")
        self.disponivel = self.worksheet is not None

    def _worksheet_pronto(self) -> bool:
        return self.worksheet is not None

    def salvar_dividendo(self, data_pagamento: str, ticker: str, tipo_provento: str, quantidade: int, valor_unitario: float, valor_total: float) -> bool:
        if not self._worksheet_pronto(): return False
        try:
            nova_linha = [str(data_pagamento), str(ticker).upper().strip(), str(tipo_provento).upper().strip(), int(quantidade), float(valor_unitario), float(valor_total)]
            self.worksheet.append_row(nova_linha, value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar: {e}")
            return False

    @st.cache_data(ttl=300)
    def obter_todos_dividendos(_self) -> pd.DataFrame:
        if not _self._worksheet_pronto():
            return pd.DataFrame()

        try:
            # A MUDANÇA MÁGICA: get_all_values() ignora o padrão americano
            linhas = _self.worksheet.get_all_values()
            
            if len(linhas) <= 1: # Só tem cabeçalho ou tá vazio
                return pd.DataFrame(columns=['ticker', 'valor_total', 'ano', 'mes_numero', 'mes_nome'])

            # Monta o DataFrame manualmente e limpa os cabeçalhos
            df = pd.DataFrame(linhas[1:], columns=linhas[0])
            df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]

            # 1. O Lava Rápido (agora ele vai receber '61,03' e arrumar pra 61.03)
            for col in ["valor_unitario", "valor_total", "quantidade"]:
                if col in df.columns:
                    df[col] = df[col].apply(limpar_numero)

            # 2. O Calendário
            col_data = 'data_pagamento' if 'data_pagamento' in df.columns else (df.columns[0] if len(df.columns) > 0 else None)
            if col_data:
                df["data_pagamento_dt"] = pd.to_datetime(df[col_data], errors="coerce")
                df["ano"] = df["data_pagamento_dt"].dt.year.fillna(0).astype(int)
                df["mes_numero"] = df["data_pagamento_dt"].dt.month.fillna(0).astype(int)
                
                meses_pt = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
                df["mes_nome"] = df["mes_numero"].map(meses_pt).fillna("N/A")
            else:
                df["ano"], df["mes_numero"], df["mes_nome"] = 0, 0, "N/A"

            return df

        except Exception as e:
            logger.error(f"Erro crítico no model de dividendos: {e}")
            return pd.DataFrame(columns=['ticker', 'valor_total', 'ano', 'mes_numero', 'mes_nome'])