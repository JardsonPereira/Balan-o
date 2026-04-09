import streamlit as st
import pandas as pd

# 1. Configuração para Celular
st.set_page_config(
    page_title="Balancete Pro",
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

# 4. Processamento e Exibição
if not st.session_state.lancamentos.empty:
    df_base = st.session_state.lancamentos
    resumo_lista = []
    
    # Agrupamento por conta única para gerar o saldo
    for conta in df_base['Descrição'].unique():
        d_conta = df_base[df_base['Descrição'] == conta]
        v_deb = d_conta[d_conta['Tipo'] == 'Débito']['Valor'].sum()
        v_cre = d_conta[d_conta['Tipo'] == 'Crédito']['Valor'].sum()
        v_nat = d_conta['Natureza'].iloc[0]
        v_sub = d_conta['Subgrupo'].iloc[0]
        
        # Cálculo de saldo devedor ou credor
        s_devedor = max(0.0, v_deb - v_cre)
        s_credor = max(0.0, v_cre - v_deb)
        
        resumo_lista.append({
            'Conta': conta, 
            'Natureza': v_nat, 
            'Subgrupo': v_sub, 
            'D': s_devedor, 
            'C': s_credor
        })
    
    df_res = pd.DataFrame(resumo_lista)

    # 5. Visualização das Tabelas (Balanço Patrimonial)
    st.subheader("📈 Balanço Patrimonial")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.write("**ATIVO**")
        df_ac = df_res[(df_res['Natureza'] == "Ativo") & (df_res['Subgrupo'] == "Circulante")]
        if not df_ac.empty:
            st.caption("Circulante")
            st.dataframe(df_ac[['Conta', 'D']], hide_index=True, use_container_width=True)
        
        df_anc = df_res[(df_res['Natureza'] == "Ativo") & (df_res['Subgrupo'] == "Não Circulante")]
        if not df_anc.empty:
            st.caption("Não Circulante")
            st.dataframe(df_anc[['Conta', 'D']], hide_index=True, use_container_width=True)
        st.info(f"Total Ativo: R${(df_ac['D'].sum() + df_anc['D'].sum()):,.2f}")

    with c2:
        st.write("**PASSIVO**")
        df_pc = df_res[(df_res['Natureza'] == "Passivo") & (df_res['Subgrupo'] == "Circulante")]
        if not df_pc.empty:
            st.caption("Circulante")
            st.dataframe(df_pc[['Conta', 'C']], hide_index=True, use_container_width=True)
            
        df_pnc = df_res[(df_res['Natureza'] == "Passivo") & (df_res['Subgrupo'] == "Não Circulante")]
        if not df_pnc.empty:
            st.caption("Não Circulante")
            st.dataframe(df_pnc[['Conta', 'C']], hide_index=True, use_container_width=True)
        st.info(f"Total Passivo: R${(df_pc['C'].sum() + df_pnc['C'].sum()):,.2f}")

    with c3:
        st.write("**P. LÍQUIDO**")
        df_pl = df_res[df_res['Natureza'] == "Patrimônio Líquido"]
        if not df_pl.empty:
            st.dataframe(df_pl[['Conta', 'C']], hide_index=True, use_container_width=True)
        st.info(f"Total PL: R${df_pl['C'].sum():,.2f}")

    # 6. Resultados do Exercício
    st.divider()
    st.subheader("📊 Resultado do Exercício")
    df_resultado = df_res[df_res['Natureza'].isin(["Receita", "Despesa"])]
    if not df_resultado.empty:
        st.dataframe(df_resultado[['Conta', 'Natureza', 'D', 'C']], hide_index=True, use_container_width=True)
    
    # 7. Verificação de Equilíbrio Contábil
    st.divider()
    res_devedor = df_res['D'].sum()
    res_credor = df_res['C'].sum()
    
    st.subheader("🏁 Verificação de Saldos")
    col_a, col_b = st.columns(2)
    col_a.metric("Total Devedor", f"R${res_devedor:,.2f}")
    col_b.metric("Total Credor", f"R${res_credor:,.2f}")

    if round(res_devedor, 2) == round(res_credor, 2):
        st.success("✅ O Balancete fechou corretamente!")
    else:
        st.error(f"❌ Diferença de R${abs(res_devedor - res_credor):,.2f}")

    # 8. Gestão e Exclusão
    with st.expander("⚙️ Gerenciar Lançamentos"):
        for i, row in df_base.iterrows():
            col_t, col_b = st.columns([4, 1])
            col_t.write(f"{row['Descrição']} | R${row['Valor']:.2f} ({row['Tipo']})")
            if col_b.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df_base[df_base['ID'] != row['ID']]
                st.rerun()
else:
    st.info("Toque no '+' para realizar o primeiro lançamento.")
