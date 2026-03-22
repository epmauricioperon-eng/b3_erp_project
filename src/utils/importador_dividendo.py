import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

def realizar_migracao_dividendos(caminho_excel: str = "data/planilha_legado.xlsx") -> None:
    """Extrai dados da aba 'Dividendos' e converte para o modelo do ERP."""
    logger.info(f"Iniciando extração de dados da aba 'Dividendos' em {caminho_excel}")
    
    try:
        # 1. Extração - Lendo apenas a aba 'Dividendos'
        # Usamos o 'Dtype=str' no Produto para garantir que o Pandas não confunda o ticker com números
        df_origem = pd.read_excel(caminho_excel, sheet_name='Dividendos', dtype={'Produto': str})
        
        # 2. Transformação - Mapeamento de Colunas
        df_destino = pd.DataFrame()
        
        # Formato YYYY-MM-DD para o banco de dados
        df_destino['data_pagamento'] = pd.to_datetime(df_origem['Data']).dt.strftime('%Y-%m-%d')
        
        # Limpeza do Ticker (ex: " PETR4 " vira "PETR4")
        df_destino['ticker'] = df_origem['Produto'].str.upper().str.strip()
        
        # Tipo de Provento (ex: "DIVIDENDO", "JCP")
        df_destino['tipo_provento'] = df_origem['Movimentação'].str.upper().str.strip()
        
        df_destino['quantidade_base'] = df_origem['Quantidade'].astype(int)
        df_destino['valor_unitario'] = df_origem['Preço unitário'].astype(float)
        df_destino['valor_total'] = df_origem['Valor da Operação'].astype(float)
        
        # 3. Carga - Salvando o CSV oficial de dividendos
        caminho_csv = "data/dividendos.csv"
        df_destino.to_csv(caminho_csv, index=False)
        
        logger.info(f"Sucesso! {len(df_destino)} registros de dividendos migrados perfeitamente para {caminho_csv}")
        
    except FileNotFoundError:
        logger.error(f"Arquivo Excel não encontrado em {caminho_excel}. Verifique se o nome está correto.")
    except KeyError as e:
        logger.error(f"Uma das colunas esperadas não foi encontrada na aba 'Dividendos'. Erro: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado durante a migração de dividendos: {e}", exc_info=True)

if __name__ == "__main__":
    realizar_migracao_dividendos()