import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 1. CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="Contabilidade Digital Pro", layout="wide")

# Conexão com as Secrets do Streamlit Cloud
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro: Configure as Secrets (SUPABASE_URL e SUPABASE_KEY) no painel do Streamlit.")
    st.stop()

# --- 2. CSS PARA ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .gestao-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; 
                   box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 8px; }
    .dre-header { font-size: 16px; font-weight: bold; color: #1E3A8A; }
    .dre-value { font-size: 24px; font-weight: 900; margin-bottom: 15px; }
    .resumo-dre-linha { font-size: 1.1em; font-weight: bold; padding: 12px; border-radius: 8px; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE ACESSO (LOGIN/CADASTRO) ---
if 'user' not in st.session_state:
    st.session_state.user = None

def autenticacao():
    st.sidebar.title("🔐 Acesso ao Sistema")
    menu = st.sidebar.radio("Escolha", ["Login", "Cadastrar Novo Usuário"])
    email = st.sidebar.text_input("E-mail")
    senha = st.sidebar.text_input("Senha", type="password")

    if menu == "Cadastrar Novo Usuário":
        if st.sidebar.button("Criar Conta"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada! Verifique seu e-mail e faça login.")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")
    else:
        if st.sidebar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception:
                st.sidebar.error("E-mail ou senha incorretos.")

if st.session_state.user is None:
    autenticacao()
    st.info("👋 Bem-vindo! Por favor, faça login ou cadastre-se na barra lateral.")
    st.stop()

# --- 4. ÁREA DO SISTEMA (LOGADO) ---
user_id = st.session_state.user.id
st.sidebar.write(f"Logado como: **{st.session_state.user.email}**")
if st.sidebar.button("Sair/Logout"):
    st.session_state.user = None
    st.rerun()

st.title("📑 Sistema Contábil Integrado")

# Funções de Dados
def carregar_dados():
    res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
    return pd.DataFrame(res.data)

df_db = carregar_dados()

# --- 5. BARRA LATERAL: NOVO LANÇAMENTO ---
with st.sidebar:
    st.divider()
    st.header("➕ Novo Lançamento")
    with st.form("form_contabil", clear_on_submit=True):
        contas_existentes = sorted(df_db['descricao'].unique().tolist()) if not df_db.empty else []
        escolha_conta = st.selectbox("Conta Existente", ["-- Selecione --"] + contas_existentes)
        nova_conta = st.text_input("OU Nova Conta").upper().strip()
        
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        justificativa = st.text_area("Justificativa")
        
        if st.form_submit_button("Confirmar Dados", use_container_width=True):
            nome_final = nova_conta if nova_conta else (escolha_conta if escolha_conta != "-- Selecione --" else None)
            if nome_final and valor > 0:
                supabase.table("lancamentos").insert({
                    "user_id": user_id, "descricao": nome_final, "natureza": natureza,
                    "tipo": tipo, "valor": valor, "justificativa": justificativa
                }).execute()
                st.rerun()

# --- 6. INTERFACE PRINCIPAL ---
if not df_db.empty:
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE", "⚙️ Gestão"])
    
    # Aba Razonetes
    with tab_raz:
        for conta in sorted(df_db['descricao'].unique()):
            df_c = df_db[df_db['descricao'] == conta]
            with st.expander(f"📖 Razonete: {conta}"):
                c_d, c_c = st.columns(2)
                v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                c_d.write("**DÉBITO**")
                for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows(): c_d.caption(f"R$ {float(r['valor']):,.2f}")
                c_c.write("**CRÉDITO**")
                for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows(): c_c.caption(f"R$ {float(r['valor']):,.2f}")
                st.write(f"**Saldo: R$ {abs(v_d - v_c):,.2f}**")

    # Aba Gestão (Excluir)
    with tab_ges:
        for _, row in df_db.iterrows():
            col_txt, col_btn = st.columns([0.8, 0.2])
            col_txt.markdown(f'<div class="gestao-card">{row["descricao"]} | R$ {float(row["valor"]):,.2f}</div>', unsafe_allow_html=True)
            if col_btn.button("🗑️", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Nenhum lançamento encontrado. Utilize a barra lateral para começar.")
