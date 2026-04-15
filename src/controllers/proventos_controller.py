import pandas as pd
from datetime import datetime
from src.models.transacao_model import TransacaoModel
from src.models.dividendo_model import DividendoModel
from src.services.scrapper_service import ProventosScraperService
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ProventosController:
    """
    Controlador responsável pela lógica de negócios dos Proventos.
    Cruza dados de mercado (web) com a carteira do usuário (banco).
    """

    def __init__(self):
        self.transacao_model = TransacaoModel()
        self.scraper_service = ProventosScraperService()
        self.dividendo_model = DividendoModel()

    def _limpar_valor(self, valor_str) -> float:
        """Versão robusta: trata negativos, múltiplos pontos e espaços fantasmas."""
        if pd.isna(valor_str) or valor_str == '' or valor_str is None:
            return 0.0
        
        if isinstance(valor_str, (int, float)):
            return float(valor_str)

        # 1. Limpeza inicial: remove R$, espaços e caracteres não numéricos (exceto , . e -)
        v_str = str(valor_str).strip().replace('R$', '').replace(' ', '')
        
        # 2. Se houver ponto e vírgula (Ex: 1.250,30)
        if '.' in v_str and ',' in v_str:
            # Remove o ponto (milhar) e troca a vírgula por ponto (decimal)
            v_str = v_str.replace('.', '').replace(',', '.')
        
        # 3. Se houver apenas vírgula (Ex: 1250,30)
        elif ',' in v_str:
            v_str = v_str.replace(',', '.')
            
        # 4. Caso especial: Múltiplos pontos como milhar sem vírgula (Ex: 1.250.000)
        # Se houver mais de um ponto, provavelmente são todos separadores de milhar
        elif v_str.count('.') > 1:
            v_str = v_str.replace('.', '')

        try:
            return float(v_str)
        except ValueError:
            logger.error(f"Não foi possível converter o valor: {valor_str}")
            return 0.0

    def calcular_proventos_a_receber(self) -> pd.DataFrame:
        logger.info("Iniciando motor de cálculo de proventos a receber...")
        
        carteira_atual = self.transacao_model.obter_posicao_atual()
        if carteira_atual.empty:
            logger.warning("Carteira vazia. Não há ativos para consultar dividendos.")
            return pd.DataFrame()
        
        ativos_na_carteira = carteira_atual['ticker'].unique().tolist()
        resultados = []
        hoje = datetime.now().date()

        for ticker in ativos_na_carteira:
            df_dividendos = self.scraper_service.buscar_ultimos_dividendos(ticker)
            if df_dividendos.empty:
                continue 
            
            try:
                # O Pulo do Gato: Analisamos os 5 últimos anúncios, 
                # para não perder dividendos duplos ou múltiplos pagamentos no mês.
                for _, anuncio in df_dividendos.head(5).iterrows():
                    data_com_str = str(anuncio.get('DATA COM', ''))
                    data_pagamento_str = str(anuncio.get('Pagamento', ''))
                    
                    if not data_com_str or str(data_com_str).upper() == 'NAN':
                        continue

                    # Converte a data de pagamento para comparar
                    data_pagamento_dt = pd.to_datetime(data_pagamento_str, format="%d/%m/%Y", errors='coerce')
                    
                    if pd.isna(data_pagamento_dt) or data_pagamento_dt.date() <= hoje:
                        continue # Já passou ou é hoje, ignora na previsão

                    valor_rendimento = self._limpar_valor(anuncio.get('Valor', 0.0))
                    qtde_elegivel = self.transacao_model.obter_quantidade_na_data_com(ticker, data_com_str)
                    
                    if qtde_elegivel > 0:
                        total_receber = round((qtde_elegivel * valor_rendimento), 2)
                        
                        resultados.append({
                            'Ticker': ticker,
                            'Data Com': data_com_str,
                            'Data Pagamento': data_pagamento_str,
                            'Valor Unitário (R$)': valor_rendimento,
                            'Quantidade Elegível': qtde_elegivel,
                            'Total a Receber (R$)': total_receber
                        })
                        
            except Exception as e:
                logger.error(f"Erro ao processar matemática de dividendos para {ticker}: {e}", exc_info=True)
        
        return pd.DataFrame(resultados)

    def obter_proventos_pendentes_de_confirmacao(self) -> list:
        """
        Busca proventos cuja data de pagamento já passou ou é hoje, 
        mas que ainda não foram registrados no banco de dados.
        """
        logger.info("Iniciando varredura de proventos pendentes de confirmação...")
        
        carteira_atual = self.transacao_model.obter_posicao_atual()
        if carteira_atual.empty:
            return []
            
        ativos_na_carteira = carteira_atual['ticker'].unique().tolist()
        df_recebidos = self.dividendo_model.obter_todos_dividendos()
        
        pendentes = []
        hoje = datetime.now().date()

        for ticker in ativos_na_carteira:
            df_dividendos = self.scraper_service.buscar_ultimos_dividendos(ticker)
            if df_dividendos.empty:
                continue
                
            try:
                # Verificamos os últimos 5 pagamentos para garantir que nada ficou para trás
                for _, anuncio in df_dividendos.head(5).iterrows():
                    data_com_str = str(anuncio.get('DATA COM', ''))
                    data_pagamento_str = str(anuncio.get('Pagamento', ''))
                    tipo_str = str(anuncio.get('Tipo', 'Rendimento')).upper()
                    
                    if not data_com_str or str(data_com_str).upper() == 'NAN':
                        continue

                    data_pagamento_dt = pd.to_datetime(data_pagamento_str, format="%d/%m/%Y", errors='coerce')
                    
                    if pd.isna(data_pagamento_dt) or data_pagamento_dt.date() > hoje:
                        continue # Ainda não foi pago, ignora na confirmação
                        
                    data_db_format = data_pagamento_dt.strftime("%Y-%m-%d")
                    
                    # Verificação no Banco de Dados se já foi recebido
                    ja_recebido = False
                    if not df_recebidos.empty:
                        filtro = (df_recebidos['ticker'] == ticker) & (df_recebidos['data_pagamento'] == data_db_format)
                        if not df_recebidos[filtro].empty:
                            ja_recebido = True
                    
                    if not ja_recebido:
                        qtde_elegivel = self.transacao_model.obter_quantidade_na_data_com(ticker, data_com_str)
                        valor_rendimento = self._limpar_valor(anuncio.get('Valor', 0.0))
                        
                        if qtde_elegivel > 0:
                            total_receber = round((qtde_elegivel * valor_rendimento), 2)
                            pendentes.append({
                                'ticker': ticker,
                                'data_pagamento': data_db_format, 
                                'tipo_provento': tipo_str,
                                'quantidade_base': qtde_elegivel,
                                'valor_unitario': valor_rendimento,
                                'valor_total': total_receber
                            })
                            logger.info(f"Pendente encontrado: {ticker} - R$ {total_receber}")
                            
            except Exception as e:
                logger.error(f"Erro ao verificar pendência para {ticker}: {e}")
                
        return pendentes

    def confirmar_recebimento_em_lote(self, lista_proventos: list) -> bool:
        """
        Recebe uma lista de proventos selecionados e os registra no banco de dados.
        """
        sucesso_global = True
        for prov in lista_proventos:
            logger.info(f"Confirmando recebimento de {prov['ticker']} - R$ {prov['valor_total']}")
            res = self.dividendo_model.salvar_dividendo(
                prov['data_pagamento'], 
                prov['ticker'], 
                prov['tipo_provento'],
                int(prov['quantidade_base']), 
                float(prov['valor_unitario']), 
                float(prov['valor_total'])
            )
            if not res:
                sucesso_global = False
                logger.error(f"Falha ao confirmar provento de {prov['ticker']}")
        
        return sucesso_global

    # =========================================================================
    # FUNÇÕES ADICIONADAS PARA O FUNCIONAMENTO DA VIEW (CARD E ABA DIVIDENDOS)
    # =========================================================================

    def obter_resumo_dividendos_total(self) -> dict:
        """Calcula a soma de todos os dividendos já recebidos na história."""
        try:
            df = self.dividendo_model.obter_todos_dividendos()
            if df.empty or 'valor_total' not in df.columns:
                return {'total_recebido': 0.0}
            
            total_acumulado = df['valor_total'].sum()
            return {'total_recebido': float(total_acumulado)}
        except Exception as e:
            logger.error(f"Erro ao somar dividendos globais: {e}", exc_info=True)
            return {'total_recebido': 0.0}

    def obter_historico_completo_dividendos(self) -> pd.DataFrame:
        """Retorna o DataFrame completo de dividendos para a aba de histórico/gráficos."""
        return self.dividendo_model.obter_todos_dividendos()

# --- BLOCO DE TESTE ---
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    controller = ProventosController()
    print("Testando instâncias de métodos:")
    print("Possui previsão? ", hasattr(controller, 'calcular_proventos_a_receber'))
    print("Possui pendência? ", hasattr(controller, 'obter_proventos_pendentes_de_confirmacao'))
    print("Possui resumo global? ", hasattr(controller, 'obter_resumo_dividendos_total'))