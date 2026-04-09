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
    
    for conta in df_base['Descrição'].unique():
        d_conta = df_base[df_base['Descrição'] == conta]
        v_deb = d_conta[d_conta['Tipo'] == 'Débito']['Valor'].sum()
        v_cre = d_conta[d_conta['Tipo'] == 'Crédito']['Valor'].sum()
        v_nat = d_conta['Natureza'].iloc[0]
        v_sub = d_conta['Subgrupo'].iloc[0]
        
        s_devedor = max(0, v_deb - v_cre)
        s_credor = max(0, v_cre - v_deb)
        resumo_lista.append({'Conta': conta, '
