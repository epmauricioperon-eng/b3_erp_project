import pandas as pd
import gspread
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DividendoModel:
    """Modelo conectado ao Google Sheets para dividendos."""
    
    def __init__(self):
        try:
            self.gc = gspread.service_account(filename="credenciais_google.json")
            self.planilha = self.gc.open("ERP_B3_Database")
            self.worksheet = self.planilha.worksheet("Dividendos")
        except Exception as e:
            logger.error(f"Erro ao conectar no Google Sheets: {e}")

    def salvar_dividendo(self, data_pagamento: str, ticker: str, tipo_provento: str, 
                         quantidade_base: int, valor_unitario: float, valor_total: float) -> bool:
        try:
            nova_linha = [data_pagamento, ticker.upper(), tipo_provento.upper(), 
                          quantidade_base, valor_unitario, valor_total]
            
            # Manda para a nuvem!
            self.worksheet.append_row(nova_linha)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dividendo na Nuvem: {e}")
            return False

    def obter_todos_dividendos(self) -> pd.DataFrame:
        try:
            dados = self.worksheet.get_all_records()
            if not dados:
                return pd.DataFrame()
            
            df = pd.DataFrame(dados)
            # Garante formato numérico
            colunas_numericas = ['quantidade_base', 'valor_unitario', 'valor_total']
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
            df['data_pagamento'] = pd.to_datetime(df['data_pagamento'])
            df['ano'] = df['data_pagamento'].dt.year
            df['mes_nome'] = df['data_pagamento'].dt.strftime('%B')
            df['mes_numero'] = df['data_pagamento'].dt.month
            
            return df
        except Exception as e:
            logger.error(f"Erro ao ler dividendos da Nuvem: {e}")
            return pd.DataFrame()

    def obter_resumo_dividendos(self) -> dict:
        df = self.obter_todos_dividendos()
        if df.empty:
            return {"total_recebido": 0.0}
        
        total = df['valor_total'].sum()
        return {"total_recebido": float(total)}