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
        desc = st.text_input("Descrição (Ex: Caixa, Empréstimos)")
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        
        # Subgrupo condicional (apenas para Ativo e Passivo)
        subgrupo = "N/A"
        if natureza in ["Ativo", "Passivo"]:
            subgrupo = st.selectbox("Subgrupo", ["Circulante", "Não Circulante"])
            
        tipo = st.selectbox("Operação", ["Débito", "Crédito"])
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento"):
            if desc and valor > 0:
                novo = pd.DataFrame([{
                    'ID': st.session_state.id_cont, 
                    'Descrição': desc.upper(), 
                    'Natureza': natureza, 
                    'Subgrupo': subgrupo,
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

    # 5. Exibição Detalhada (Ativo | Passivo | PL)
    st.subheader("📈 Balanço Patrimonial")
    col_ativo, col_passivo, col_pl = st.columns(3)

    with col_ativo:
        st.markdown("### ATIVO")
        # Ativo Circulante
        st.write("**Circulante**")
        df_ac = df_resumo[(df_resumo['Natureza'] == "Ativo") & (df_resumo['Subgrupo'] == "Circulante")]
        st.dataframe(df_ac[['Conta', 'D']], use_container_width=True, hide_index=True)
        # Ativo Não Circulante
        st.write("**Não Circulante**")
        df_anc = df_resumo[(df_resumo['Natureza'] == "Ativo") & (df_resumo['Subgrupo'] == "Não Circulante")]
        st.dataframe(df_anc[['Conta', 'D']], use_container_width=True, hide_index=True)
        st.info(f"Total Ativo: R$ {df_ac['D'].sum() + df_anc['D'].sum():,.2f}")

    with col_passivo:
        st.markdown("### PASSIVO
