import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(page_title="Balancete Pro", layout="wide")

st.title("📑 Balancete e Razonetes")

# 2. Inicialização do Banco de Dados em Memória
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Subgrupo', 'Tipo', 'Valor']
    )
    st.session_state.id_cont = 0

# 3. Formulário de Entrada
with st.expander("➕ Realizar Novo Lançamento", expanded=True):
    with st.form("form_contabil", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            desc = st.text_input("Nome da Conta (Ex: Mercadorias)")
            natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        with col2:
            sub = st.selectbox("Subgrupo (Se Ativo/Passivo)", ["Circulante", "Não Circulante", "N/A"])
            tipo = st.selectbox("Tipo de Lançamento", ["Débito", "Crédito"])
        
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento"):
            if desc:
                # Lógica de Subgrupo Automático
                f_sub = sub if natureza in ["Ativo", "Passivo"] else "N/A"
                
                novo_dado = pd.DataFrame([{
                    'ID': st.session_state.id_cont,
                    'Descrição': desc.upper().strip(),
                    'Natureza': natureza,
                    'Subgrupo': f_sub,
                    'Tipo': tipo,
                    'Valor': valor
                }])
                
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo_dado], ignore_index=True)
                st.session_state.id_cont += 1
                st.rerun()

# 4. Processamento dos Resultados (Razonetes e Saldos)
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    
    # Criando os Saldos por Conta (Razonetes Simplificados)
    resumo = []
    for conta in df['Descrição'].unique():
        filtro = df[df['Descrição'] == conta]
        debito_total = filtro[filtro['Tipo'] == 'Débito']['Valor'].sum()
        credito_total = filtro[filtro['Tipo'] == 'Crédito']['Valor'].sum()
        
        # Saldo Líquido
        s_devedor = max(0.0, debito_total - credito_total)
        s_credor = max(0.0, credito_total - debito_total)
        
        resumo.append({
            'Conta': conta,
            'Natureza': filtro['Natureza'].iloc[0],
            'Subgrupo': filtro['Subgrupo'].iloc[0],
            'D': s_devedor,
            'C': s_credor
        })
    
    df_balancete = pd.DataFrame(resumo)

    # 5. EXIBIÇÃO: Razonetes e Histórico
    st.divider()
    st.subheader("📝 Lançamentos e Razonetes")
    tab1, tab2 = st.tabs(["Histórico de Lançamentos", "Saldos das Contas"])
    
    with tab1:
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tab2:
        st.dataframe(df_balancete, use_container_width=True, hide_index=True)

    # 6. EXIBIÇÃO: Balanço Patrimonial
    st.divider()
    st.subheader("📈 Balanço Patrimonial")
    col_at, col_ps, col_pl = st.columns(3)

    with col_at:
        st.info("**ATIVO**")
        a_circ = df_balancete[(df_balancete['Natureza'] == "Ativo") & (df_balancete['Subgrupo'] == "Circulante")]
        a_ncirc = df_balancete[(df_balancete['Natureza'] == "Ativo") & (df_balancete['Subgrupo'] == "Não Circulante")]
        if not a_circ.empty: st.write("Circulante"); st.table(a_circ[['Conta', 'D']])
        if not a_ncirc.empty: st.write("Não Circulante"); st.table(a_ncirc[['Conta', 'D']])
        st.write(f"**Total Ativo:** R$ {a_circ['D'].sum() + a_ncirc['D'].sum():,.2f}")

    with col_ps:
        st.info("**PASSIVO**")
        p_circ = df_balancete[(df_balancete['Natureza'] == "Passivo") & (df_balancete['Subgrupo'] == "Circulante")]
        p_ncirc = df_balancete[(df_balancete['Natureza'] == "Passivo") & (df_balancete['Subgrupo'] == "Não Circulante")]
        if not p_circ.empty: st.write("Circulante"); st.table(p_circ[['Conta', 'C']])
        if not p_ncirc.empty: st.write("Não Circulante"); st.table(p_ncirc[['Conta', 'C']])
        st.write(f"**Total Passivo:** R$ {p_circ['C'].sum() + p_ncirc['C'].sum():,.2f}")

    with col_pl:
        st.info("**PATRIMÔNIO LÍQUIDO**")
        pl_data = df_balancete[df_balancete['Natureza'] == "Patrimônio Líquido"]
        if not pl_data.empty: st.table(pl_data[['Conta', 'C']])
        st.write(f"**Total PL:** R$ {pl_data['C'].sum():,.2f}")

    # 7. Verificação Final de Equilíbrio
    st.divider()
    tot_d = df_balancete['D'].sum()
    tot_c = df_balancete['C'].sum()
    
    if round(tot_d, 2) == round(tot_c, 2):
        st.success(f"✅ Balancete Fechado! Total Devedor: R${tot_d:,.2f} | Total Credor: R${tot_c:,.2f}")
    else:
        st.error(f"❌ Diferença Encontrada! D: R${tot_d:,.2f} | C: R${tot_c:,.2f}")

    # Botão para Limpar Tudo
    if st.button("🗑️ Limpar Todos os Lançamentos"):
        st.session_state.lancamentos = pd.DataFrame(columns=['ID', 'Descrição', 'Natureza', 'Subgrupo', 'Tipo', 'Valor'])
        st.session_state.id_cont = 0
        st.rerun()

else:
    st.warning("Aguardando o primeiro lançamento para gerar os relatórios.")
