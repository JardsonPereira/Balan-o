import streamlit as st
import pandas as pd

# 1. Configuração para Celular
st.set_page_config(
    page_title="Balancete Mobile",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📑 Balancete Pro")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor'])
    st.session_state.id_cont = 0

# 3. Interface de Entrada
with st.expander("➕ Novo Lançamento", expanded=True):
    with st.form("form_contabil", clear_on_submit=True):
        desc = st.text_input("Descrição (Ex: Caixa)")
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.selectbox("Operação", ["Débito", "Crédito"])
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento"):
            if desc and valor > 0:
                novo = pd.DataFrame([{'ID': st.session_state.id_cont, 'Descrição': desc.upper(), 
                                      'Natureza': natureza, 'Tipo': tipo, 'Valor': valor}])
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
        
        saldo_dev = max(0, deb - cre)
        saldo_cre = max(0, cre - deb)
        resumo.append({'Conta': conta, 'Natureza': nat, 'D': saldo_dev, 'C': saldo_cre})
    
    df_resumo = pd.DataFrame(resumo)

    # 5. Exibição em Colunas Distintas (Ativo | Passivo | PL)
    st.subheader("📈 Grupos Patrimoniais")
    col_ativo, col_passivo, col_pl = st.columns(3)

    with col_ativo:
        st.markdown("**Ativo**")
        df_a = df_resumo
