import pandas as pd
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)

def realizar_migracao(caminho_excel: str = "data/planilha_legado.xlsx") -> None:
    """Extrai dados da planilha antiga e converte para o modelo do ERP."""
    logger.info(f"Iniciando extração de dados da aba 'Compras' em {caminho_excel}")
    
    try:
        # 1. Extração (Extract) - Lendo apenas a aba de compras
        df_origem = pd.read_excel(caminho_excel, sheet_name='Compras')
        
        # 2. Transformação (Transform) - De/Para das colunas
        df_destino = pd.DataFrame()
        
        # Tratando datas (garantindo o formato YYYY-MM-DD)
        df_destino['data_operacao'] = pd.to_datetime(df_origem['Data']).dt.strftime('%Y-%m-%d')
        
        # Limpando espaços extras nos códigos (ex: " PETR4 " vira "PETR4")
        df_destino['ticker'] = df_origem['Código'].astype(str).str.upper().str.strip()
        
        # Como a aba é "Compras", cravamos o tipo
        df_destino['tipo'] = 'COMPRA'
        
        df_destino['quantidade'] = df_origem['Quantidade'].astype(int)
        df_destino['preco_unitario'] = df_origem['Preço Médio Executado'].astype(float)
        
        # Matemética fina: O Total do seu Excel pode embutir taxas. Vamos extraí-las.
        total_excel = df_origem['Total'].astype(float)
        custo_bruto = df_destino['quantidade'] * df_destino['preco_unitario']
        taxas_calculadas = total_excel - custo_bruto
        
        # Evitando taxas negativas por arredondamento
        df_destino['taxas'] = taxas_calculadas.apply(lambda x: round(x, 2) if x > 0 else 0.0)
        df_destino['total_operacao'] = total_excel.round(2)
        
        # Gerando IDs únicos para cada linha da sua planilha legada
        agora = datetime.now().strftime("%Y%m%d%H%M%S")
        df_destino['id_transacao'] = [f"{agora}_{i}" for i in range(len(df_destino))]
        
        # 3. Carga (Load) - Organizando colunas e salvando o CSV oficial
        colunas_finais = [
            "id_transacao", "data_operacao", "ticker", "tipo", 
            "quantidade", "preco_unitario", "taxas", "total_operacao"
        ]
        df_destino = df_destino[colunas_finais]
        
        caminho_csv = "data/transacoes.csv"
        df_destino.to_csv(caminho_csv, index=False)
        
        logger.info(f"Sucesso! {len(df_destino)} registros migrados perfeitamente para {caminho_csv}")
        
    except FileNotFoundError:
        logger.error("Arquivo excel não encontrado. Verifique se o nome é 'planilha_legado.xlsx' e está na pasta 'data/'.")
    except Exception as e:
        logger.error(f"Erro inesperado durante a migração: {e}", exc_info=True)

if __name__ == "__main__":
    realizar_migracao()