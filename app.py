import streamlit as st
import pandas as pd
import subprocess
import sys
import plotly.graph_objects as go # Biblioteca para gráficos interativos

# --- GARANTIA DE INSTALAÇÃO ---
try:
    from supabase import create_client, Client
    import plotly
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase", "plotly"])
    from supabase import create_client, Client

# --- CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="Sistema Contábil Integrado", layout="wide")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets.")
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
                st.sidebar.success("Link enviado!")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

# --- SISTEMA PÓS-LOGIN ---
user_id = st.session_state.user.id
st.sidebar.write(f"👤 Logado: **{st.session_state.user.email}**")
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
        desc = st.text_input("Nome da Conta").upper().strip()
        nat = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        just = st.text_area("Justificativa")
        if st.form_submit_button("Confirmar Lançamento"):
            if desc:
                supabase.table("lancamentos").insert({"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}).execute()
                st.rerun()

# --- DASHBOARD PRINCIPAL ---
st.title("📑 Painel Contábil Digital")

if not df.empty:
    t1, t2, t3 = st.tabs(["📊 Razonetes", "📈 DRE Interativa", "⚙️ Gestão"])
    
    with t1:
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            with st.expander(f"📖 Conta: {conta}"):
                c_d, c_c = st.columns(2)
                v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                c_d.markdown("**DÉBITO**")
                for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows(): c_d.caption(f"R$ {r['valor']:.2f} - {r['justificativa']}")
                c_c.markdown("**CRÉDITO**")
                for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows(): c_c.caption(f"R$ {r['valor']:.2f} - {r['justificativa']}")
                st.write(f"**Saldo: R$ {abs(v_d - v_c):,.2f}**")

    with t2:
        # CÁLCULOS
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        desp = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        lucro = rec - desp - enc
        
        st.subheader("Análise Visual de Resultado")
        
        # Métricas em destaque
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Receita Total", f"R$ {rec:,.2f}")
        m2.metric("Despesas Adm.", f"R$ {desp:,.2f}", delta_color="inverse")
        m3.metric("Encargos Fin.", f"R$ {enc:,.2f}", delta_color="inverse")
        m4.metric("Lucro Líquido", f"R$ {lucro:,.2f}", delta=f"{(lucro/rec*100) if rec>0 else 0:.1f}%")

        col_graf1, col_graf2 = st.columns(2)

        with col_graf1:
            st.write("**Composição de Gastos**")
            if (desp + enc) > 0:
                fig_pie = go.Figure(data=[go.Pie(labels=['Despesas', 'Encargos'], values=[desp, enc], hole=.3)])
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Sem gastos para exibir gráfico.")

        with col_graf2:
            st.write("**Fluxo do Resultado (Waterfall)**")
            fig_water = go.Figure(go.Waterfall(
                orientation = "v",
                measure = ["relative", "relative", "relative", "total"],
                x = ["Receita", "Despesas", "Encargos", "LUCRO"],
                textposition = "outside",
                text = [f"+{rec}", f"-{desp}", f"-{enc}", f"={lucro}"],
                y = [rec, -desp, -enc, 0],
                connector = {"line":{"color":"rgb(63, 63, 63)"}},
            ))
            st.plotly_chart(fig_water, use_container_width=True)

        st.divider()
        st.write("**📊 Análise Vertical Detalhada:**")
        if rec > 0:
            st.progress(1.0, text=f"Receita: 100%")
            st.progress(min(desp/rec, 1.0), text=f"Despesas Administrativas: {(desp/rec)*100:.2f}%")
            st.progress(min(enc/rec, 1.0), text=f"Encargos Financeiros: {(enc/rec)*100:.2f}%")
        
    with t3:
        st.subheader("Histórico")
        for idx, row in df.iterrows():
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"🗑️ {row['descricao']} | R$ {row['valor']:.2f}")
            if c2.button("Apagar", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Nenhum lançamento encontrado.")
