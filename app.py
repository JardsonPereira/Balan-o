import streamlit as st
import pandas as pd

# 1. Configuração para Celular
st.set_page_config(
    page_title="Balancete Mobile Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📑 Balancete Detalhado")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(columns=['ID', 'Descrição', 'Natureza', 'Subgrupo', 'Tipo', 'Valor'])
    st.session_state.id_cont = 0

# 3. Interface de Entrada
with st.expander("➕ Novo Lançamento", expanded=True):
    with st.form("form_contabil", clear_on_submit=True):
        desc = st.text_input("Descrição (Ex: Caixa, Fornecedores)")
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        
        sub_escolhido = st.selectbox("Subgrupo (Se Ativo/Passivo)", ["Circulante", "Não Circulante", "N/A"])
        
        tipo = st.selectbox("Operação", ["Débito", "Crédito"])
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento"):
            if desc and valor > 0:
                final_sub = sub_escolhido if natureza in ["Ativo", "Passivo"] else "N/A"
                
                novo = pd.DataFrame([{
                    'ID': st.session_state.id_cont, 
                    'Descrição': desc.upper(), 
                    'Natureza': natureza, 
                    'Subgrupo': final_sub,
                    'Tipo': tipo, 
                    'Valor': valor
                }])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.session_state.id_cont += 1
                st.rerun()

# 4. Processamento dos Dados
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    resumo = []
    for conta in df['Descrição'].unique():
        d_conta = df[df['Descrição'] == conta]
        deb = d_conta[d_conta['Tipo'] == 'Débito']['Valor'].sum()
        cre = d_conta[d_conta['Tipo'] == 'Crédito']['Valor'].sum()
        nat = d_conta['Natureza'].iloc[0]
        sub = d_conta['Subgrupo'].iloc[0]
        
        saldo_dev = max(0, deb - cre)
        saldo_cre = max(0, cre - deb)
        resumo.append({'Conta': conta, 'Natureza': nat, 'Subgrupo': sub, 'D': saldo_dev, 'C': saldo_cre})
    
    df_resumo = pd.DataFrame(resumo)

    # 5. Balanço Patrimonial
    st.subheader("📈 Balanço Patrimonial")
    col_ativo, col_passivo, col_pl = st.columns(3)

    with col_ativo:
        st.markdown("### ATIVO")
        st.write("**Circulante**")
        df_ac = df_resumo[(df_resumo['Natureza'] == "Ativo") & (df_resumo['Subgrupo'] == "Circulante")]
        st.dataframe(df_ac[['Conta', 'D']], use_container_width=True, hide_index=True)
        
        st.write("**Não Circulante**")
        df_anc = df_resumo[(df_resumo['Natureza'] == "Ativo") & (df_resumo['Subgrupo'] == "Não Circulante")]
        st.dataframe(df_anc[['Conta', 'D']], use_container_width=True, hide_index=True)
        total_a = df_ac['D'].sum() + df_anc['D'].sum()
        st.info(f"Total Ativo: R$ {total_a:,.2f}")

    with col_passivo:
        st.markdown("### PASSIVO")
        st.write("**Circulante**")
        df_pc = df_resumo[(df_resumo['Natureza'] == "Passivo") & (df_resumo['Subgrupo'] == "Circulante")]
        st.dataframe(df_pc[['Conta', 'C']], use_container_width=True, hide_index=True)
        
        st.write("**Não Circulante**")
        df_pnc = df_resumo[(df_resumo['Natureza'] == "Passivo") & (df_resumo['Subgrupo'] == "Não Circulante")]
        st.dataframe(df_pnc[['Conta', 'C']], use_container_width=True, hide_index=True)
        total_p = df_pc['C'].sum() + df_pnc['C'].sum()
        st.info(f"Total Passivo: R$ {total_p:,.2f}")

    with col_pl:
        st.markdown("### P. LÍQUIDO")
        df_pl = df_resumo[df_resumo['Natureza'] == "Patrimônio Líquido"]
        st.dataframe(df_pl[['Conta', 'C']], use_container_width=True, hide_index=True)
        total_pl = df_pl['C'].sum()
        st.info(f"Total PL: R$ {total_pl:,.2f}")

    # 6. Contas de Resultado
    st.divider()
    st.subheader("📊 Contas de Resultado")
    df_res = df_resumo[df_resumo['Natureza'].isin(["Receita", "Despesa"])][['Conta', 'Natureza', 'D', 'C']]
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    # 7. VERIFICAÇÃO FINAL (Saldo Devedor == Saldo Credor)
    st.divider()
    t_devedor = df_resumo['D'].sum()
    t_credor = df_resumo['C'].sum()
    
    st.subheader("🏁 Verificação de Saldos")
    c1, c2 = st.columns(2)
    c1.metric("Total Devedor", f"R$ {t_devedor:,.2f}")
    c2.metric("Total Credor", f"R$ {t_credor:,.2f}")

    if round(t_devedor, 2) == round(t_credor, 2):
        st.success("✅ O
