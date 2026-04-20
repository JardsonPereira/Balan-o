import streamlit as st
import pandas as pd
import subprocess
import sys

# --- GARANTIA DE INSTALAÇÃO ---
try:
    from supabase import create_client, Client
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase"])
    from supabase import create_client, Client

# --- CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="Contabilidade Digital", layout="wide")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets no Streamlit Cloud.")
    st.stop()

# --- SISTEMA DE ACESSO ---
if 'user' not in st.session_state:
    st.session_state.user = None

def gerenciar_acesso():
    st.sidebar.title("🔐 Acesso")
    aba = st.sidebar.radio("Escolha", ["Login", "Criar Conta", "Recuperar Senha"])
    email = st.sidebar.text_input("E-mail").lower().strip()

    if aba == "Criar Conta":
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada! Tente fazer login agora.")
            except Exception as e:
                if "already registered" in str(e).lower():
                    st.sidebar.warning("📧 E-mail já cadastrado. Tente o Login.")
                else:
                    st.sidebar.error(f"Erro: {e}")

    elif aba == "Login":
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception:
                st.sidebar.error("E-mail ou senha inválidos.")

    elif aba == "Recuperar Senha":
        if st.sidebar.button("Enviar link de recuperação"):
            try:
                supabase.auth.reset_password_for_email(email)
                st.sidebar.success("Link enviado! Verifique seu e-mail.")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

# --- SISTEMA PÓS-LOGIN ---
user_id = st.session_state.user.id
st.sidebar.write(f"Usuário: {st.session_state.user.email}")
if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

def buscar_dados():
    res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
    return pd.DataFrame(res.data)

df = buscar_dados()

# --- LANÇAMENTOS ---
with st.sidebar:
    st.divider()
    with st.form("contabil", clear_on_submit=True):
        desc = st.text_input("Conta").upper()
        nat = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.radio("Tipo", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.01)
        just = st.text_area("Justificativa")
        if st.form_submit_button("Lançar"):
            supabase.table("lancamentos").insert({
                "user_id": user_id, "descricao": desc, "natureza": nat,
                "tipo": tipo, "valor": valor, "justificativa": just
            }).execute()
            st.rerun()

# --- DASHBOARD ---
if not df.empty:
    t1, t2, t3 = st.tabs(["📊 Razonetes", "📈 DRE", "⚙️ Gestão"])
    
    with t1:
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            with st.expander(f"📖 {conta}"):
                st.write("**Justificativas registradas:**")
                for j in df_c['justificativa'].unique(): st.caption(f"- {j}")
                st.table(df_c[['tipo', 'valor']])

    with t2:
        receitas = df[df['natureza'] == 'Receita']['valor'].sum()
        despesas = df[df['natureza'] == 'Despesa']['valor'].sum()
        lucro = receitas - despesas
        
        st.subheader("Demonstração do Resultado (DRE)")
        col1, col2 = st.columns(2)
        col1.metric("Receita Total", f"R$ {receitas:,.2f}")
        col2.metric("Resultado Líquido", f"R$ {lucro:,.2f}")

        if receitas > 0:
            st.write("---")
            st.write("**Análise Vertical (em relação à Receita):**")
            st.write(f"Receita Operacional: 100%")
            st.write(f"Despesas: -{(despesas/receitas)*100:.2f}%")
            st.write(f"Margem Líquida: {(lucro/receitas)*100:.2f}%")

    with t3:
        for idx, row in df.iterrows():
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"{row['descricao']} | R$ {row['valor']}")
            if c2.button("Excluir", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
