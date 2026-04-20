import streamlit as st
import pandas as pd
import subprocess
import sys
import os

# --- GARANTIA DE INSTALAÇÃO (BOOTSTRAP) ---
def install_and_import(package):
    try:
        return __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return __import__(package)

# Importações com garantia
plotly_go = install_and_import("plotly").graph_objects
from supabase import create_client, Client

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema Contábil Interativo", layout="wide")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets.")
    st.stop()

# --- AUTENTICAÇÃO ---
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
                st.sidebar.success("Conta criada! Tente logar.")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")
    elif aba == "Login":
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception:
                st.sidebar.error("Credenciais inválidas.")
    elif aba == "Recuperar Senha":
        if st.sidebar.button("Enviar link de recuperação"):
            try:
                supabase.auth.reset_password_for_email(email)
                st.sidebar.success("Link enviado!")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

# --- PÓS-LOGIN ---
user_id = st.session_state.user.id
st.sidebar.write(f"👤 Logado: **{st.session_state.user.email}**")
if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

def carregar_dados():
    res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
    return pd.DataFrame(res.data)

df = carregar_dados()

# --- LANÇAMENTOS ---
with st.sidebar:
    st.divider()
    st.header("➕ Novo Lançamento")
    with st.form("contabil", clear_on_submit=True):
        desc = st.text_input("Nome da Conta").upper().strip()
        nat = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        just = st.text_area("Justificativa")
        if st.form_submit_button("Confirmar"):
            if desc:
                supabase.table("lancamentos").insert({"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}).execute()
                st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title("📑 Painel Contábil Digital")

if not df.empty:
    t1, t2, t3 = st.tabs(["📊 Razonetes", "📈 DRE Interativa", "⚙️ Gestão"])
    
    with t1:
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            with st.expander(f"📖 {conta} ({df_c['natureza'].iloc[0]})"):
                st.table(df_c[['tipo', 'valor', 'justificativa']])

    with t2:
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        desp = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        lucro = rec - desp - enc
        
        # Métricas interativas
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receita", f"R$ {rec:,.2f}")
        c2.metric("Despesas", f"R$ {desp:,.2f}", delta_color="inverse")
        c3.metric("Encargos", f"R$ {enc:,.2f}", delta_color="inverse")
        c4.metric("Lucro Líquido", f"R$ {lucro:,.2f}", delta=f"{(lucro/rec*100) if rec>0 else 0:.1f}%")

        col_left, col_right = st.columns(2)
        
        with col_left:
            st.write("**Fluxo de Resultado**")
            fig = plotly_go.Figure(plotly_go.Waterfall(
                x = ["Receita", "Despesas", "Encargos", "LUCRO"],
                measure = ["relative", "relative", "relative", "total"],
                y = [rec, -desp, -enc, 0],
                text = [f"R${rec}", f"-R${desp}", f"-R${enc}", f"R${lucro}"],
                connector = {"line":{"color":"#444"}}
            ))
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.write("**Análise Vertical**")
            if rec > 0:
                st.write(f"Despesas: **{(desp/rec)*100:.1f}%** da Receita")
                st.write(f"Encargos: **{(enc/rec)*100:.1f}%** da Receita")
                st.write(f"Margem Líquida: **{(lucro/rec)*100:.1f}%**")
                # Gráfico de Pizza
                fig_pie = plotly_go.Figure(data=[plotly_go.Pie(labels=['Lucro', 'Despesas', 'Encargos'], 
                                                            values=[max(0, lucro), desp, enc], hole=.3)])
                st.plotly_chart(fig_pie, use_container_width=True)

    with t3:
        for idx, row in df.iterrows():
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"{row['descricao']} | R$ {row['valor']:.2f}")
            if c2.button("Apagar", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Aguardando lançamentos...")
