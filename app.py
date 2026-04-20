import streamlit as st
import pandas as pd
import subprocess
import sys
import os

# --- GARANTIA DE INSTALAÇÃO ---
def install_and_import(package):
    try:
        return __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return __import__(package)

plotly_go = install_and_import("plotly").graph_objects
from supabase import create_client, Client

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema Contábil Integrado", layout="wide")

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
    menu = st.sidebar.radio("Escolha", ["Login", "Criar Conta", "Recuperar Senha"])
    email = st.sidebar.text_input("E-mail").lower().strip()

    if menu == "Criar Conta":
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada! Tente logar.")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")
    elif menu == "Login":
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception:
                st.sidebar.error("Credenciais inválidas.")
    elif menu == "Recuperar Senha":
        if st.sidebar.button("Enviar link"):
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
    t1, t2, t3, t4 = st.tabs(["📊 Razonetes", "🧾 Balancete", "📈 DRE Interativa", "⚙️ Gestão"])
    
    with t1:
        st.subheader("Livro Razão")
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            with st.expander(f"📖 {conta} ({df_c['natureza'].iloc[0]})"):
                st.table(df_c[['tipo', 'valor', 'justificativa']])

    with t2:
        st.subheader("Balancete de Verificação")
        
        # Lógica do Balancete
        balancete_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            debitos = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            creditos = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            balancete_data.append({
                "Conta": conta,
                "Débito (Devedor)": debitos,
                "Crédito (Credor)": creditos
            })
        
        bal_df = pd.DataFrame(balancete_data)
        st.table(bal_df.style.format({"Débito (Devedor)": "R$ {:.2f}", "Crédito (Credor)": "R$ {:.2f}"}))
        
        total_d = bal_df["Débito (Devedor)"].sum()
        total_c = bal_df["Crédito (Credor)"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Total Devedor", f"R$ {total_d:,.2f}")
        c2.metric("Total Credor", f"R$ {total_c:,.2f}")
        
        if round(total_d, 2) == round(total_c, 2):
            st.success("✅ Balancete em Equilíbrio: Débitos e Créditos conferem!")
        else:
            st.error("⚠️ Balancete Desequilibrado: Verifique as partidas dobradas.")

    with t3:
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        desp = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        lucro = rec - desp - enc
        
        # Gráficos e Métricas (Mantidos da versão anterior)
        c1, c2, c3 = st.columns(3)
        c1.metric("Receita", f"R$ {rec:,.2f}")
        c2.metric("Custos/Gastos", f"R$ {desp+enc:,.2f}", delta_color="inverse")
        c3.metric("Lucro Líquido", f"R$ {lucro:,.2f}")

        fig = plotly_go.Figure(plotly_go.Waterfall(
            x = ["Receita", "Despesas", "Encargos", "LUCRO"],
            measure = ["relative", "relative", "relative", "total"],
            y = [rec, -desp, -enc, 0],
            connector = {"line":{"color":"#444"}}
        ))
        st.plotly_chart(fig, use_container_width=True)

    with t4:
        for idx, row in df.iterrows():
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"{row['descricao']} | R$ {row['valor']:.2f}")
            if c2.button("Apagar", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Aguardando lançamentos para gerar o Balancete.")
