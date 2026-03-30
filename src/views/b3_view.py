import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)

def render_main_page(controller) -> None:
    logger.info("Renderizando a View principal (Streamlit).")
    
    with st.sidebar:
        st.header("⚙️ Ferramentas")
        st.markdown("Exporte sua posição consolidada com cotações atualizadas.")
        
        if st.button("📄 Gerar Relatório PDF", use_container_width=True):
            with st.spinner("Desenhando PDF..."):
                caminho_pdf = controller.gerar_relatorio_pdf()
                if caminho_pdf:
                    with open(caminho_pdf, "rb") as pdf_file:
                        st.download_button(
                            label="⬇️ Baixar Extrato (PDF)",
                            data=pdf_file,
                            file_name="Extrato_Carteira_B3.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    st.success("PDF pronto para download!")
                else:
                    st.error("Erro interno ao gerar o documento.")

    st.title("📈 Gestão de Ativos B3")
    
    resumo_rv, posicao_df = controller.obter_painel_consolidado()
    historico_df = controller.obter_historico()
    resumo_div_global = controller.obter_resumo_dividendos_total()
    
    def formatar_moeda(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Investido", value=formatar_moeda(resumo_rv.get('total_investido', 0)))
    with col2:
        st.metric(label="Saldo Atual Ativos", value=formatar_moeda(resumo_rv.get('saldo_atual', 0)))
    with col3:
        st.metric(
            label="Rentabilidade Global", 
            value=formatar_moeda(resumo_rv.get('rentabilidade_rs', 0)),
            delta=f"{resumo_rv.get('rentabilidade_pct', 0):.2f}%"
        )
    with col4:
        st.metric(label="Total Dividendos", value=formatar_moeda(resumo_div_global.get('total_recebido', 0)), help="Histórico total acumulado.")

    st.markdown("---")
    
    aba_rv, aba_dividendos, aba_historico, aba_lancamento = st.tabs([
        "💼 Renda Variável", "💰 Meus Dividendos", "📄 Histórico", "➕ Lançamentos"
    ])

    with aba_rv:
        st.subheader("Dashboard de Portfólio e Gestão de Risco")
        if not posicao_df.empty:
            df_grafico = posicao_df[posicao_df['valor_atual'] > 0].copy()
            
            if not df_grafico.empty:
                col_donut, col_bar = st.columns(2)
                
                with col_donut:
                    st.markdown("**Composição da Carteira**")
                    fig_carteira = px.pie(
                        df_grafico, values='valor_atual', names='ticker', hole=0.45
                    )
                    fig_carteira.update_traces(
                        textposition='inside', textinfo='percent+label',
                        marker=dict(line=dict(color='#FFFFFF', width=2))
                    )
                    fig_carteira.update_layout(showlegend=False, margin=dict(t=10, b=10, l=0, r=0), height=350)
                    st.plotly_chart(fig_carteira, use_container_width=True)

                with col_bar:
                    st.markdown("**Exposição por Ativo (Teto 15%)**")
                    df_bar = df_grafico.sort_values(by='peso_carteira', ascending=False)
                    fig_bar = px.bar(df_bar, x='ticker', y='peso_carteira', text='peso_carteira')
                    
                    cores_barras = ['#FF4B4B' if peso > 15 else '#1F77B4' for peso in df_bar['peso_carteira']]
                    fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside', marker_color=cores_barras)
                    fig_bar.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Limite 15%", annotation_position="top right")
                    fig_bar.update_layout(xaxis_title=None, yaxis_title="Peso na Carteira (%)", margin=dict(t=10, b=10, l=0, r=0), height=350, yaxis_ticksuffix="%")
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            st.markdown("---")
            st.dataframe(
                posicao_df, use_container_width=True, hide_index=True,
                column_config={
                    "ticker": "Ativo",
                    "quantidade_total": st.column_config.NumberColumn("Qtd"),
                    "preco_medio": st.column_config.NumberColumn("Preço Médio", format="R$ %.2f"),
                    "valor_total_investido": st.column_config.NumberColumn("Total Investido", format="R$ %.2f"),
                    "preco_atual": st.column_config.NumberColumn("Cotação Atual", format="R$ %.2f"),
                    "valor_atual": st.column_config.NumberColumn("Saldo Atual", format="R$ %.2f"),
                    "peso_carteira": st.column_config.NumberColumn("Peso (%)", format="%.2f %%"),
                    "status_rebalanceamento": "Ação (Regra 15%)",
                    "rentabilidade_rs": st.column_config.NumberColumn("Lucro/Prejuízo", format="R$ %.2f"),
                    "rentabilidade_pct": st.column_config.NumberColumn("Rentab. (%)", format="%.2f %%")
                }
            )
        else:
            st.info("Sua carteira está vazia.")

    with aba_dividendos:
        st.subheader("Dashboard de Proventos")
        todos_dividendos_df = controller.obter_historico_completo_dividendos()
        
        if not todos_dividendos_df.empty:
            col_filt_1, col_filt_2, col_filt_3 = st.columns([1.5, 1.5, 3])
            anos_disponiveis = sorted(todos_dividendos_df['ano'].unique(), reverse=True)
            ano_atual = datetime.now().year
            if ano_atual not in anos_disponiveis:
                anos_disponiveis.insert(0, ano_atual)
            ano_selecionado = col_filt_1.selectbox("Ano", anos_disponiveis)
            
            meses_ano_df = todos_dividendos_df[todos_dividendos_df['ano'] == ano_selecionado]
            meses_disponiveis = ["Todos"] + sorted(meses_ano_df['mes_nome'].unique()) if not meses_ano_df.empty else ["Todos"]
            mes_selecionado = col_filt_2.selectbox("Mês", meses_disponiveis)
            
            ativos_disponiveis = ["Todos"] + sorted(todos_dividendos_df['ticker'].unique())
            ativo_selecionado = col_filt_3.multiselect("Filtrar por Ativo", ativos_disponiveis, default="Todos")
            
            st.markdown("---")
            df_filtrado = todos_dividendos_df[todos_dividendos_df['ano'] == ano_selecionado]
            if mes_selecionado != "Todos":
                df_filtrado = df_filtrado[df_filtrado['mes_nome'] == mes_selecionado]
            if "Todos" not in ativo_selecionado and ativo_selecionado:
                df_filtrado = df_filtrado[df_filtrado['ticker'].isin(ativo_selecionado)]
                
            if not df_filtrado.empty:
                dividendos_anuais = df_filtrado.groupby(['mes_nome', 'mes_numero'])['valor_total'].sum().reset_index().sort_values(by='mes_numero')
                fig = px.bar(
                    dividendos_anuais, x='mes_nome', y='valor_total', text='valor_total', 
                    labels={'mes_nome': 'Mês', 'valor_total': 'Valor Recebido (R$)'}, template="plotly_white"
                )
                fig.update_traces(
                    marker_color=['#000080' if i % 2 == 0 else '#4169E1' for i in range(len(dividendos_anuais))],
                    texttemplate='R$ %{text:,.2f}', textposition='outside', marker_line_color='rgb(8,48,107)', marker_line_width=1.5, opacity=0.8
                )
                fig.update_layout(title_text=f"Evolução de Dividendos em {ano_selecionado}", xaxis_title=None, yaxis_title=None)
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                col_res_1, col_res_2 = st.columns(2)
                with col_res_1:
                    st.metric(label=f"Total Recebido em {ano_selecionado}", value=formatar_moeda(df_filtrado['valor_total'].sum()))
                with col_res_2:
                    st.metric(label="Total a Receber", value="Em breve...")
                
                # --- NOVA UI: TABELA NA ESQUERDA, EXCLUIR NA DIREITA ---
                st.markdown("---")
                col_tabela_div, col_perigo_div = st.columns([2.5, 1])
                
                with col_tabela_div:
                    st.markdown("##### 📋 Detalhamento dos Proventos")
                    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
                
                with col_perigo_div:
                    st.markdown("##### ⚠️ Excluir Lançamento")
                    st.write("Identifique o ID na tabela ao lado para removê-lo.")
                    colunas = df_filtrado.columns.tolist()
                    col_id_nome = 'id_provento' if 'id_provento' in colunas else ('id_dividendo' if 'id_dividendo' in colunas else colunas[0])
                    lista_ids_div = df_filtrado[col_id_nome].astype(str).tolist()
                    id_div_selecionado = st.selectbox("ID do Dividendo", lista_ids_div)
                    
                    if st.button("Confirmar Exclusão", type="primary", use_container_width=True, key="btn_del_div"):
                        sucesso = controller.excluir_dividendo(id_div_selecionado)
                        if sucesso:
                            st.success(f"Removido!")
                            st.rerun()
                        else:
                            st.error("Erro ao excluir.")
            else:
                st.info("Nenhum registro encontrado para os filtros selecionados.")
        else:
            st.info("Sua base de dividendos está vazia.")

    with aba_historico:
        st.subheader("Histórico Completo (Compras/Vendas)")
        if not historico_df.empty:
            # --- MESMA UI PREMIUM PARA O HISTÓRICO ---
            col_tabela_hist, col_perigo_hist = st.columns([2.5, 1])
            
            with col_tabela_hist:
                st.markdown("##### 📋 Extrato de Operações")
                st.dataframe(historico_df, use_container_width=True, hide_index=True)
                
            with col_perigo_hist:
                st.markdown("##### ⚠️ Excluir Lançamento")
                st.write("Identifique o ID na tabela ao lado para removê-lo.")
                if 'id_transacao' in historico_df.columns:
                    lista_ids = historico_df['id_transacao'].astype(str).tolist()
                    id_selecionado = st.selectbox("ID da Transação", lista_ids)
                    
                    if st.button("Confirmar Exclusão", type="primary", use_container_width=True, key="btn_del_hist"):
                        sucesso = controller.excluir_transacao(id_selecionado)
                        if sucesso:
                            st.success(f"Removido!")
                            st.rerun()
                        else:
                            st.error("Erro ao excluir.")
                else:
                    st.warning("Coluna 'id_transacao' não encontrada.")
        else:
            st.info("O histórico de transações está vazio.")

    with aba_lancamento:
        st.subheader("Central de Lançamentos")
        tipo_lancamento = st.radio("O que você deseja registrar hoje?", ["🛒 Compra / Venda de Ativos", "💰 Recebimento de Proventos"], horizontal=True)
        st.markdown("---")

        if tipo_lancamento == "🛒 Compra / Venda de Ativos":
            with st.form("form_nova_transacao", clear_on_submit=True):
                col_a, col_b, col_c = st.columns(3)
                data_operacao = col_a.date_input("Data da Operação")
                ticker = col_b.text_input("Ticker (Ex: PETR4, MXRF11)")
                tipo = col_c.selectbox("Tipo", ["COMPRA", "VENDA"])

                col_d, col_e, col_f = st.columns(3)
                quantidade = col_d.number_input("Quantidade", min_value=1, step=1)
                preco_unitario = col_e.number_input("Preço Unitário (R$)", min_value=0.01, step=0.01, format="%.2f")
                taxas = col_f.number_input("Taxas/Emolumentos (R$)", min_value=0.0, step=0.01, value=0.0, format="%.2f")

                if st.form_submit_button("Registrar Transação"):
                    sucesso = controller.registrar_transacao(
                        data_operacao.strftime("%Y-%m-%d"), ticker.strip().upper(), tipo, quantidade, preco_unitario, taxas
                    )
                    if sucesso:
                        st.success("Operação registrada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao registrar. Verifique os dados e a conexão com o Google Sheets.")
        else:
            with st.form("form_novo_dividendo", clear_on_submit=True):
                col_a, col_b, col_c = st.columns(3)
                data_pagamento = col_a.date_input("Data do Pagamento")
                ticker = col_b.text_input("Ticker (Ex: PETR4, MXRF11)")
                tipo_provento = col_c.selectbox("Tipo de Provento", ["DIVIDENDO", "JCP", "RENDIMENTO"])

                col_d, col_e, col_f = st.columns(3)
                quantidade_base = col_d.number_input("Quantidade Base (Opcional)", min_value=0, step=1)
                valor_unitario = col_e.number_input("Valor por Cota (R$)", min_value=0.00, step=0.01, format="%.2f")
                valor_total = col_f.number_input("Valor Total Recebido (R$)", min_value=0.01, step=0.01, format="%.2f")

                if st.form_submit_button("Registrar Provento"):
                    sucesso = controller.registrar_dividendo(
                        data_pagamento.strftime("%Y-%m-%d"), ticker.strip().upper(), tipo_provento, 
                        quantidade_base, valor_unitario, valor_total
                    )
                    if sucesso:
                        st.success(f"Provento de {ticker.upper()} registrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao registrar provento. Verifique os dados.")