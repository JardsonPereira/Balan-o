import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 1. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. CONEXÃO COM SUPABASE ---
# As chaves devem estar nas Secrets do Streamlit Cloud
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro nas Secrets: Verifique se SUPABASE_URL e SUPABASE_KEY estão configuradas.")
    st.stop()

# --- 3. ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .gestao-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; 
                   box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 8px; }
    .badge-natureza { background-color: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: bold; }
    .resumo-dre-linha { font-size: 1.1em; font-weight: bold; padding: 12px; border-radius: 8px; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. SISTEMA DE AUTENTICAÇÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

def area_login():
    st.sidebar.title("🔐 Acesso ao Sistema")
    escolha = st.sidebar.radio("Selecione", ["Login", "Criar Nova Conta"])
    email = st.sidebar.text_input("E-mail")
    senha = st.sidebar.text_input("Senha", type="password")

    if escolha == "Criar Nova Conta":
        if st.sidebar.button("Registrar"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada! Verifique seu e-mail e faça login.")
            except Exception as e:
                st.sidebar.error(f"Erro ao cadastrar: {e}")
    else:
        if st.sidebar.button("Entrar"):
            try:
                auth_res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = auth_res.user
                st.rerun()
            except Exception:
                st.sidebar.error("E-mail ou senha incorretos.")

# Se não estiver logado, para o código aqui e mostra apenas o login
if st.session_state.user is None:
    area_login()
    st.info("👋 Bem-vindo! Utilize a barra lateral para acessar sua conta ou criar uma nova.")
    st.stop()

# --- 5. INTERFACE DO SISTEMA (PÓS-LOGIN) ---
user_id = st.session_state.user.id
st.sidebar.write(f"Conectado como: **{st.session_state.user.email}**")
if st.sidebar.button("Sair (Logout)"):
    st.session_state.user = None
    st.rerun()

st.title("📑 Sistema Contábil Integrado")

# Funções de Banco de Dados
def carregar_lancamentos():
    # Busca apenas os dados do usuário logado
    res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
    return pd.DataFrame(res.data)

df_db = carregar_lancamentos()

# --- 6. BARRA LATERAL: ENTRADA DE DADOS ---
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
                novo_registro = {
                    "user_id": user_id,
                    "descricao": nome_final,
                    "natureza": natureza,
                    "tipo": tipo,
                    "valor": valor,
                    "justificativa": justificativa
                }
                supabase.table("lancamentos").insert(novo_registro).execute()
                st.success("Lançamento realizado!")
                st.rerun()

# --- 7. PAINEL PRINCIPAL (TABS) ---
if not df_db.empty:
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE", "⚙️ Gestão"])
    
    with tab_raz:
        for conta in sorted(df_db['descricao'].unique()):
            df_c = df_db[df_db['descricao'] == conta]
            with st.expander(f"📖 Razonete: {conta} | {df_c['natureza'].iloc[0]}"):
                c_d, c_c = st.columns(2)
                v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                
                c_d.markdown("**DÉBITO**")
                for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows(): 
                    c_d.caption(f"R$ {float(r['valor']):,.2f}")
                
                c_c.markdown("**CRÉDITO**")
                for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows(): 
                    c_c.caption(f"R$ {float(r['valor']):,.2f}")
                
                st.divider()
                st.write(f"**Saldo Final: R$ {abs(v_d - v_c):,.2f} ({'Devedor' if v_d >= v_c else 'Credor'})**")

    with tab_ges:
        st.subheader("📋 Histórico de Lançamentos")
        for _, row in df_db.iterrows():
            with st.container():
                col_info, col_del = st.columns([0.85, 0.15])
                col_info.markdown(f"""
                <div class="gestao-card">
                    <b>{row['descricao']}</b> ({row['natureza']})<br>
                    <span style="color: {'blue' if row['tipo'] == 'Débito' else 'green'}">
                        {row['tipo']}: R$ {float(row['valor']):,.2f}
                    </span><br>
                    <small><i>{row['justificativa']}</i></small>
                </div>
                """, unsafe_allow_html=True)
                if col_del.button("🗑️", key=f"del_{row['id']}"):
                    supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                    st.rerun()
else:
    st.warning("Nenhum lançamento registrado para este usuário.")
