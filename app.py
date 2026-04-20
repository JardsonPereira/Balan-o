import streamlit as st
import pandas as pd
import subprocess
import sys
import os

# --- 1. GARANTIA DE INSTALAÇÃO ---
try:
    from supabase import create_client, Client
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase"])
    from supabase import create_client, Client

# --- 2. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema Contábil Integrado", layout="wide")

# --- 3. CONEXÃO COM SUPABASE ---
try:
    # Lembre-se: SUPABASE_URL (https://...) e SUPABASE_KEY (anon public)
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("🚨 Erro de conexão! Verifique as Secrets no Streamlit Cloud.")
    st.stop()

# --- 4. ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .dre-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #1E3A8A; margin-bottom: 10px; }
    .percent-text { color: #6c757d; font-size: 0.9em; font-weight: normal; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. SISTEMA DE AUTENTICAÇÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

def gerenciar_acesso():
    st.sidebar.title("🔐 Acesso ao Sistema")
    menu = st.sidebar.radio("Selecione uma opção", ["Login", "Criar Conta", "Recuperar Senha"])
    
    email = st.sidebar.text_input("E-mail").lower().strip()

    if menu == "Criar Conta":
        senha = st.sidebar.text_input("Defina uma Senha", type="password")
        if st.sidebar.button("Cadastrar Usuário", use_container_width=True):
            if email and senha:
                try:
                    supabase.auth.sign_up({"email": email, "password": senha})
                    st.sidebar.success("✅ Conta criada com sucesso!")
                    st.sidebar.info("Se não conseguir logar, verifique se o Supabase exige confirmação por e-mail.")
                except Exception as e:
                    if "already registered" in str(e).lower():
                        st.sidebar.warning("⚠️ Este e-mail já possui cadastro. Use a opção de Login.")
                    else:
                        st.sidebar.error(f"Erro: {e}")
            else:
                st.sidebar.error("Preencha todos os campos.")

    elif menu == "Login":
        senha = st.sidebar.text_input("Sua Senha", type="password")
        if st.sidebar.button("Entrar", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception:
                st.sidebar.error("❌ E-mail ou senha inválidos.")

    elif menu == "Recuperar Senha":
        st.sidebar.info("Enviaremos um link para redefinir sua senha.")
        if st.sidebar.button("Enviar E-mail de Recuperação", use_container_width=True):
            if email:
                try:
                    supabase.auth.reset_password_for_email(email)
                    st.sidebar.success(f"📧 Link enviado para {email}")
                except Exception as e:
                    st.sidebar.error(f"Erro ao enviar: {e}")
            else:
                st.sidebar.warning("Informe o e-mail cadastrado.")

# Verificação de Bloqueio
if st.session_state.user is None:
    gerenciar_acesso()
    st.info("👋 Bem-vindo! Faça login na barra lateral para acessar seus dados contábeis.")
    st.stop()

# --- 6. INTERFACE DO SISTEMA (LOGADO) ---
user_id = st.session_state.user.id
st.sidebar.write(f"👤 Logado: **{st.session_state.user.email}**")
if st.sidebar.button("Sair / Logout"):
    st.session_state.user = None
    st.rerun()

# --- 7. BUSCA DE DADOS ---
def carregar_dados():
    res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
    return pd.DataFrame(res.data)

df = carregar_dados()

# --- 8. LANÇAMENTOS (BARRA LATERAL) ---
with st.sidebar:
    st.divider()
    st.header("➕ Novo Lançamento")
    with st.form("form_contabil", clear_on_submit=True):
        desc = st.text_input("Nome da Conta").upper().strip()
        nat = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        just = st.text_area("Justificativa / Histórico")
        
        if st.form_submit_button("Confirmar Lançamento", use_container_width=True):
            if desc:
                supabase.table("lancamentos").insert({
                    "user_id": user_id, "descricao": desc, "natureza": nat,
                    "tipo": tipo, "valor": valor, "justificativa": just
                }).execute()
                st.rerun()

# --- 9. PAINEL PRINCIPAL ---
st.title("📊 Painel de Controle Contábil")

if not df.empty:
    tab1, tab2, tab3 = st.tabs(["📖 Razonetes", "📈 DRE (Resultado)", "⚙️ Gestão"])

    with tab1:
        st.subheader("Livro Razão Digital")
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            with st.expander(f"Conta: {conta} ({df_c['natureza'].iloc[0]})"):
                col_d, col_c = st.columns(2)
                v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                
                col_d.write("**DÉBITO**")
                for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows():
                    col_d.caption(f"R$ {float(r['valor']):,.2f} - {r['justificativa']}")
                
                col_c.write("**CRÉDITO**")
                for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows():
                    col_c.caption(f"R$ {float(r['valor']):,.2f} - {r['justificativa']}")
                
                st.divider()
                st.write(f"**Saldo: R$ {abs(v_d - v_c):,.2f}**")

    with tab2:
        st.subheader("Análise de Resultado")
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        desp = df[df['natureza'] == 'Despesa']['valor'].sum()
        lucro = rec - desp
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Receita Total", f"R$ {rec:,.2f}")
        c2.metric("Despesa Total", f"R$ {desp:,.2f}")
        c3.metric("Resultado Líquido", f"R$ {lucro:,.2f}")

        # Análise Vertical
        if rec > 0:
            st.markdown('<div class="dre-card">', unsafe_allow_html=True)
            st.write(f"**Receita Operacional:** 100%")
            st.write(f"**Despesas:** -{(desp/rec)*100:.2f}%")
            st.write(f"**Margem de Lucro:** {(lucro/rec)*100:.2f}%")
            st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.subheader("Excluir Lançamentos")
        for idx, row in df.iterrows():
            c_info, c_btn = st.columns([0.8, 0.2])
            c_info.write(f"🗑️ {row['descricao']} | {row['tipo']} | R$ {float(row['valor']):,.2f}")
            if c_btn.button("Excluir", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.warning("Nenhum lançamento encontrado para este usuário.")
