import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="ContabilApp - Pro", layout="wide")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets no Streamlit Cloud.")
    st.stop()

# --- ESTADOS DO SISTEMA ---
if 'user' not in st.session_state: st.session_state.user = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'menu_opcao' not in st.session_state: st.session_state.menu_opcao = "📊 Razonetes"

# --- FUNÇÃO PARA GERAR PDF ---
def gerar_pdf(df_periodo, data_ini, data_fim, user_email, saldo_ini, saldo_fim):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(190, 10, "Relatorio Contabil Consolidado", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(190, 10, f"Periodo: {data_ini} ate {data_fim} | Usuario: {user_email}", ln=True, align="C")
    pdf.ln(5)
    pdf.cell(190, 10, f"Saldo Inicial Transportado: R$ {saldo_ini:,.2f} | Saldo Final: R$ {saldo_fim:,.2f}", ln=True, align="L")
    pdf.line(10, 35, 200, 35)
    pdf.ln(10)
    return bytes(pdf.output())

# --- AUTENTICAÇÃO ---
def gerenciar_acesso():
    st.sidebar.title("🔐 Acesso")
    menu = st.sidebar.radio("Escolha", ["Login", "Criar Conta"])
    email = st.sidebar.text_input("E-mail").lower().strip()
    senha = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Confirmar"):
        try:
            if menu == "Login":
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
            else:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada! Tente logar.")
            st.rerun()
        except Exception: st.sidebar.error("Erro na autenticação.")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

# --- CARGA DE DADOS ---
@st.cache_data(ttl=60)
def carregar_dados(u_id):
    res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
    temp_df = pd.DataFrame(res.data)
    if not temp_df.empty:
        temp_df['data_lancamento'] = pd.to_datetime(temp_df['data_lancamento']).dt.date
    return temp_df

df = carregar_dados(st.session_state.user.id)

# --- LOGICA DE SALDO TRANSPORTADO ---
def calc_saldo_ate(data_limite):
    if df.empty: return 0.0
    # Filtra tudo antes da data limite para compor o saldo inicial
    df_passado = df[df['data_lancamento'] <= data_limite]
    entradas = df_passado[df_passado['status'] == "Entrada"]['valor'].sum()
    saidas = df_passado[df_passado['status'] == "Pago"]['valor'].sum()
    return entradas - saidas

# --- INTERFACE ---
with st.sidebar:
    st.write(f"👤 {st.session_state.user.email}")
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()
    st.divider()
    st.header("➕ Novo Lançamento")
    # Form simplificado aqui por brevidade, mantenha sua lógica de campos original
    with st.form("add_form", clear_on_submit=True):
        desc = st.text_input("Descrição").upper()
        data_l = st.date_input("Data", datetime.now())
        valor = st.number_input("Valor", min_value=0.0)
        tipo = st.radio("Tipo", ["Débito", "Crédito"], horizontal=True)
        nat = st.selectbox("Grupo", ["Ativo", "Passivo", "Receita", "Despesa", "Patrimônio Líquido"])
        status = st.selectbox("Status", ["Entrada", "Pago", "Pendente"])
        if st.form_submit_button("Salvar"):
            supabase.table("lancamentos").insert({
                "user_id": st.session_state.user.id, "descricao": desc, "data_lancamento": str(data_l),
                "valor": valor, "tipo": tipo, "natureza": nat, "status": status
            }).execute()
            st.cache_data.clear()
            st.rerun()

# --- FILTROS DE PERÍODO ---
st.title("📑 Painel Contábil Digital")
f1, f2 = st.columns(2)
with f1: data_ini = st.date_input("Início", datetime.now().date().replace(day=1))
with f2: data_fim = st.date_input("Fim", datetime.now().date())

# Cálculos de Saldo (O segredo do transporte está aqui)
saldo_inicial = calc_saldo_ate(data_ini - timedelta(days=1))
df_periodo = df[(df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)] if not df.empty else pd.DataFrame()
movimentacao_periodo = 0.0
if not df_periodo.empty:
    ent = df_periodo[df_periodo['status'] == "Entrada"]['valor'].sum()
    sai = df_periodo[df_periodo['status'] == "Pago"]['valor'].sum()
    movimentacao_periodo = ent - sai
saldo_final = saldo_inicial + movimentacao_periodo

# --- NAVEGAÇÃO ---
opcoes = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa"]
aba_sel = st.segmented_control("Menu", opcoes, default="📊 Razonetes")

if df.empty:
    st.warning("Nenhum dado cadastrado. Adicione um lançamento na lateral.")
else:
    if aba_sel == "📊 Razonetes":
        st.subheader("📊 Razonetes (T)")
        grupos = ["Ativo", "Passivo", "Receita", "Despesa"]
        for g in grupos:
            df_g = df_periodo[df_periodo['natureza'] == g]
            if not df_g.empty:
                st.markdown(f"#### {g}")
                cols = st.columns(3)
                for i, conta in enumerate(df_g['descricao'].unique()):
                    df_c = df_g[df_g['descricao'] == conta]
                    with cols[i % 3]:
                        st.markdown(f"**{conta}**")
                        v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        st.write(f"D: R$ {v_d:,.2f} | C: R$ {v_c:,.2f}")
                        st.divider()

    elif aba_sel == "🧾 Balancete":
        st.subheader("🧾 Balancete de Verificação")
        bal = []
        for conta in df_periodo['descricao'].unique():
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal.append({"Conta": conta, "Débito": d, "Crédito": c, "Saldo": d-c})
        st.table(pd.DataFrame(bal))

    elif aba_sel == "📈 DRE":
        st.subheader("📈 DRE")
        receitas = df_periodo[df_periodo['natureza'] == "Receita"]['valor'].sum()
        despesas = df_periodo[df_periodo['natureza'] == "Despesa"]['valor'].sum()
        st.metric("Receita Bruta", f"R$ {receitas:,.2f}")
        st.metric("Despesas Operacionais", f"R$ {despesas:,.2f}")
        st.metric("Resultado Líquido", f"R$ {receitas - despesas:,.2f}")

    elif aba_sel == "💸 Fluxo de Caixa":
        st.subheader("💸 Fluxo de Caixa com Saldo Transportado")
        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo Inicial (do mês anterior)", f"R$ {saldo_inicial:,.2f}")
        c2.metric("Movimentação do Mês", f"R$ {movimentacao_periodo:,.2f}", delta=movimentacao_periodo)
        c3.metric("Saldo Final em Caixa", f"R$ {saldo_final:,.2f}")
        
        st.info(f"O saldo de **R$ {saldo_final:,.2f}** será o saldo inicial para o período após {data_fim}.")
