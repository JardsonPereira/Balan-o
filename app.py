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
st.set_page_config(page_title="Sistema Contábil Integrado", layout="wide")

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
st.sidebar.write(f"👤 Logado como: **{st.session_state.user.email}**")
if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

def buscar_dados():
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

df = buscar_dados()

# --- LANÇAMENTOS ---
with st.sidebar:
    st.divider()
    st.header("➕ Novo Lançamento")
    with st.form("contabil", clear_on_submit=True):
        desc = st.text_input("Nome da Conta (ex: Juros Passivos)").upper().strip()
        
        # ADICIONADO: Encargos Financeiros na lista
        nat = st.selectbox("Natureza", [
            "Ativo", "Passivo", "Patrimônio Líquido", 
            "Receita", "Despesa", "Encargos Financeiros"
        ])
        
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        just = st.text_area("Justificativa")
        
        if st.form_submit_button("Confirmar Lançamento", use_container_width=True):
            if desc:
                try:
                    supabase.table("lancamentos").insert({
                        "user_id": user_id, "descricao": desc, "natureza": nat,
                        "tipo": tipo, "valor": valor, "justificativa": just
                    }).execute()
                    st.success("✅ Lançamento realizado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao gravar: {e}")

# --- DASHBOARD PRINCIPAL ---
st.title("📑 Painel Contábil Digital")

if not df.empty:
    t1, t2, t3 = st.tabs(["📊 Razonetes", "📈 DRE (Resultado)", "⚙️ Gestão"])
    
    with t1:
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            with st.expander(f"📖 Conta: {conta} ({df_c['natureza'].iloc[0]})"):
                c_d, c_c = st.columns(2)
                v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                
                c_d.markdown("**DÉBITO**")
                for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows():
                    c_d.caption(f"R$ {float(r['valor']):,.2f} - {r['justificativa']}")
                
                c_c.markdown("**CRÉDITO**")
                for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows():
                    c_c.caption(f"R$ {float(r['valor']):,.2f} - {r['justificativa']}")
                
                st.divider()
                st.write(f"**Saldo: R$ {abs(v_d - v_c):,.2f}**")

    with t2:
        # CÁLCULOS DRE
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        desp_adm = df[df['natureza'] == 'Despesa']['valor'].sum()
        encargos = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        
        # Resultado Operacional antes dos encargos
        res_op = rec - desp_adm
        lucro_final = res_op - encargos
        
        st.subheader("Demonstração do Resultado")
        col1, col2, col3 = st.columns(3)
        col1.metric("Receita Bruta", f"R$ {rec:,.2f}")
        col2.metric("Encargos Financeiros", f"R$ {encargos:,.2f}", delta_color="inverse")
        col3.metric("Lucro/Prejuízo Líquido", f"R$ {lucro_final:,.2f}")

        if rec > 0:
            st.divider()
            st.write("**📊 Análise Vertical (Sobre a Receita):**")
            st.info(f"Despesas Administrativas: **{(desp_adm/rec)*100:.2f}%**")
            st.info(f"Encargos Financeiros: **{(encargos/rec)*100:.2f}%**")
            st.success(f"Margem Líquida Final: **{(lucro_final/rec)*100:.2f}%**")

    with t3:
        st.subheader("Histórico")
        for idx, row in df.iterrows():
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"🗑️ {row['descricao']} | {row['natureza']} | R$ {float(row['valor']):,.2f}")
            if c2.button("Apagar", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Nenhum lançamento encontrado.")
