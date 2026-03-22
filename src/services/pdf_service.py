from fpdf import FPDF
import pandas as pd
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)

class PDFReport(FPDF):
    """Classe base do PDF com cabeçalho e rodapé customizados."""
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Relatorio Gerencial - Gestao de Ativos B3', border=False, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}} - Gerado em {data_hora}', align='C')

class PdfService:
    """Serviço dedicado à construção visual de documentos PDF."""
    
    def gerar_extrato_carteira(self, resumo: dict, df_posicao: pd.DataFrame) -> str:
        logger.info("Service: Iniciando montagem do PDF da carteira...")
        try:
            pdf = PDFReport()
            pdf.alias_nb_pages() # Permite o uso do {nb} para o total de páginas
            pdf.add_page()
            
            # --- SEÇÃO 1: RESUMO ---
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, "Resumo Global", ln=True)
            
            pdf.set_font("helvetica", "", 10)
            def formatar_moeda(valor):
                return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

            # Printando os totais
            pdf.cell(60, 8, f"Total Investido: {formatar_moeda(resumo.get('total_investido', 0))}")
            pdf.ln()
            pdf.cell(60, 8, f"Saldo Atual: {formatar_moeda(resumo.get('saldo_atual', 0))}")
            pdf.ln()
            rent_pct = resumo.get('rentabilidade_pct', 0)
            pdf.cell(60, 8, f"Rentabilidade Global: {formatar_moeda(resumo.get('rentabilidade_rs', 0))} ({rent_pct:.2f}%)")
            pdf.ln(15)

            # --- SEÇÃO 2: TABELA DE ATIVOS ---
            if not df_posicao.empty:
                pdf.set_font("helvetica", "B", 11)
                pdf.cell(0, 10, "Posicao Atual dos Ativos", ln=True)
                
                # Configuração das Colunas (Larguras)
                colunas = ['Ativo', 'Qtd', 'Preco Medio', 'Cotacao', 'Saldo Atual', 'Rentab. (%)']
                larguras = [25, 15, 30, 30, 45, 45]
                
                # Cabeçalho da Tabela (Fundo Cinza)
                pdf.set_fill_color(220, 220, 220)
                pdf.set_font("helvetica", "B", 9)
                for col, w in zip(colunas, larguras):
                    pdf.cell(w, 8, col, border=1, fill=True, align='C')
                pdf.ln()

                # Linhas da Tabela
                pdf.set_font("helvetica", "", 9)
                for _, row in df_posicao.iterrows():
                    pdf.cell(larguras[0], 8, str(row['ticker']), border=1, align='C')
                    pdf.cell(larguras[1], 8, str(row['quantidade_total']), border=1, align='C')
                    pdf.cell(larguras[2], 8, formatar_moeda(row['preco_medio']), border=1, align='R')
                    pdf.cell(larguras[3], 8, formatar_moeda(row['preco_atual']), border=1, align='R')
                    pdf.cell(larguras[4], 8, formatar_moeda(row['valor_atual']), border=1, align='R')
                    
                    rent_texto = f"{formatar_moeda(row['rentabilidade_rs'])} ({row['rentabilidade_pct']:.2f}%)"
                    pdf.cell(larguras[5], 8, rent_texto, border=1, align='R')
                    pdf.ln()

            # Salva no disco temporariamente para o Streamlit poder baixar
            caminho_arquivo = "data/extrato_carteira.pdf"
            pdf.output(caminho_arquivo)
            logger.info("Service: PDF finalizado e salvo em disco.")
            
            return caminho_arquivo
            
        except Exception as e:
            logger.error(f"Service: Erro fatal ao gerar PDF: {e}", exc_info=True)
            return ""