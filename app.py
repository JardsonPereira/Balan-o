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
    df = st.session_state.lancamentos
    resumo = []
    
    # Agrupamento para o Balancete
    for conta in df['Descrição'].unique():
        d_conta = df[df['Descrição'] == conta]
        deb = d_conta[d_conta['Tipo'] == 'Débito']['Valor'].sum()
        cre = d_conta[d_conta['Tipo'] == 'Crédito']['Valor'].sum()
        nat = d_conta['Natureza'].iloc[0]
        sub = d_conta['Subgrupo'].iloc[0]
        
        saldo_dev = max(0, deb - cre)
        saldo_cre = max(0, cre - deb)
        resumo.append({'Conta': conta, 'Natureza': nat, 'Subgrupo': sub, 'D': saldo_dev, 'C': saldo_cre})
    
    df_res = pd.DataFrame(resumo)

    # 5. Visualização das Tabelas
    st.subheader("📈 Balanço Patrimonial")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.write("**ATIVO**")
        # Circulante
        df_ac = df_res[(df_res['Natureza'] == "Ativo") & (df_res['Subgrupo'] == "Circulante")]
        if not df_ac.empty:
            st.caption("Circulante")
            st.dataframe(df_ac[['Conta', 'D']], hide_index=True, use_container_width=True)
        # Não Circulante
        df_anc = df_res[(df_res['Natureza'] == "Ativo") & (df_res['Subgrupo'] == "Não Circulante")]
        if not df_anc.empty:
            st.caption("Não Circulante")
            st.dataframe(df_anc[['Conta', 'D']], hide_index=True, use_container_width=True)
        st.info(f"Total Ativo: R${(df_ac['D'].sum() + df_anc['D'].sum()):,.2f}")

    with c2:
        st.write("**PASSIVO**")
        # Circulante
        df_pc = df_res[(df_res['Natureza'] == "Passivo") & (df_res['Subgrupo'] == "Circulante")]
        if not df_pc.empty:
            st.caption("Circulante")
            st.dataframe(df_pc[['Conta', 'C']], hide_index=True, use_container_width=True)
        # Não Circulante
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

    # 6. Resultados
    st.divider()
    st.subheader("📊 Resultado do Exercício")
    df_resultado = df_res[df_res['Natureza'].isin(["Receita", "Despesa"])]
    if not df_resultado.empty:
        st.dataframe(df_resultado[['Conta', 'Natureza', 'D', 'C']], hide_index=True, use_container_width=True)
    
    # 7. Verificação de Equilíbrio
    st.divider()
    tot
