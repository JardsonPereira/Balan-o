import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS PARA CORREÇÃO DEFINITIVA DE ROLAGEM E VISUAL ---
st.markdown("""
    <style>
    /* Força o scroll na página inteira e remove travas de altura */
    html, body, [data-testid="stAppViewContainer"] {
        overflow: auto !important;
        height: auto !important;
    }

    /* Ajuste do container de conteúdo */
    .main .block-container {
        padding-bottom: 150px !important; /* Espaço extra no fim para nunca cortar */
    }

    /* Estilo dos Cards de Gestão */
    .gestao-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 8px;
    }
    .badge-natureza {
        background-color: #f1f5f9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
    }
    
    /* Cabeçalhos da DRE */
    .dre-header { font-size: 16px !important; font-weight: bold !important; color: #1E3A8A; margin: 0; }
    .dre-value { font-size: 24px !important; font-weight: 900 !important; margin-bottom: 15px; }
    .resumo-dre-linha { font-size: 1.1em; font-weight: bold; padding: 12px; border-radius: 8px; margin-bottom: 8px; }
    
    /* Estilo dos botões pequenos de gestão */
    .stButton > button {
        padding: 2px 10px;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📑 Sistema Contábil Integrado")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['Descrição', 'Natureza', 'Tipo', 'Valor', 'Justificativa']
    )
if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None

# 3. Barra Lateral
with st.sidebar:
    lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
    
    if st.session_state.edit_index is not None:
        idx = st.session_state.edit_index
        row_edit = st.session_state.lancamentos.iloc[idx]
        st.header(f"📝 Editar Lançamento")
        if st.button("❌ Cancelar Edição"):
            st.session_state.edit_index = None
            st.rerun()
    else:
        st.header(f"➕ Novo Lançamento")
        row_edit = None

    with st.form("form_contabil", clear_on_submit=True):
        contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
        idx_conta = (contas_existentes.index(row_edit['Descrição']) + 1) if (row_edit is not None and row_edit['Descrição'] in contas_existentes) else 0
        escolha_conta = st.selectbox("Conta Existente", ["-- Selecione --"] + contas_existentes, index=idx_conta)
        nova_conta_input = st.text_input("Nova Conta").upper().strip()
        
        idx_nat = lista_nat.
