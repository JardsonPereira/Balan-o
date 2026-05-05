import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="ContabilApp - Sistema Integrado", layout="wide")

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

# --- FUNÇÃO PARA GERAR PDF (DRE + BALANCETE) ---
def gerar_pdf(df_periodo, data_ini, data_fim, user_email):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(190, 10, "Relatorio Contabil Consolidado", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(190, 10, f"Periodo: {data_ini} ate {data_fim} | Usuario: {user_email}", ln=True, align="C")
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)

    def calc_valor_pdf(nat, tipo_dev=True):
        sub = df_periodo[df_periodo['natureza'] == nat]
        d, c = sub[sub['tipo'] == 'Débito']['valor'].sum(), sub[sub['tipo'] == 'Crédito']['valor'].sum()
        return (d - c) if tipo_dev else (c - d)

    rec = calc_valor_pdf('Receita', False)
    desp = calc_valor_pdf('Despesa', True)
    ebitda = rec - desp
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "1. Demonstracao do Resultado (DRE)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(100, 7, f"Receita Bruta: R$ {rec:,.2f}", ln=True)
    pdf.cell(100, 7, f"Despesas Operacionais: R$ {desp:,.2f}", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 7, f"RESULTADO LIQUIDO: R$ {ebitda:,.2f}", ln=True)
    return bytes(pdf.output())

# --- AUTENTICAÇÃO ---
def gerenciar_acesso():
    st.sidebar.title("🔐 Acesso")
    menu = st.sidebar.radio("Escolha", ["Login", "Criar Conta"])
    email = st.sidebar.text_input("E-mail").lower().strip()
    senha = st.sidebar.text_input("Senha", type="password")
    if menu == "Login":
        if st.sidebar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception: st.sidebar.error("Erro no login.")
    else:
        if st.sidebar.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada!")
            except Exception as e: st.sidebar.error(f"Erro: {e}")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

user_id = st.session_state.user.id

@st.cache_data(ttl=600)
def carregar_dados(u_id):
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        temp_df = pd.DataFrame(res.data)
        if not temp_df.empty:
            temp_df['data_lancamento'] = pd.to_datetime(temp_df['data_lancamento']).dt.date
        return temp_df
    except Exception: return pd.DataFrame()

df = carregar_dados(user_id)

# --- FORMULÁRIO LATERAL ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.user.email}**")
    if st.button("Sair"):
        st.session_state.user = None
        st.cache_data.clear()
        st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df.empty:
        st.header("📝 Editar Lançamento")
        reg = df[df['id'] == st.session_state.edit_id].iloc[0]
        if st.button("Cancelar Edição"):
            st.session_state.edit_id = None
            st.rerun()
    else:
        st.header("➕ Novo Lançamento")
        reg = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago", "data_lancamento": datetime.now().date()}

    with st.form(key=f"form_{st.session_state.form_count}"):
        desc_input = st.text_input("Descrição", value=reg['descricao']).upper().strip()
        data_f = st.date_input("Data", value=reg['data_lancamento'])
        nat = st.selectbox("Grupo", ["Ativo", "Passivo", "Receita", "Despesa"], index=0)
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(reg['valor']))
        status_pag = st.selectbox("Status", ["Entrada", "Pago", "Pendente"], index=0)
        just = st.text_area("Justificativa", value=reg['justificativa'])
        
        if st.form_submit_button("Confirmar"):
            payload = {"user_id": user_id, "descricao": desc_input, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just, "status": status_pag, "data_lancamento": str(data_f)}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.cache_data.clear()
            st.session_state.form_count += 1
            st.rerun()

# --- CSS ---
st.markdown("""<style>
    .metric-card { background: #f8fafc; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; border-radius: 12px 12px 0 0; }
    .conta-rodape { padding: 8px; background: #f8fafc; text-align: center; font-weight: 700; border-top: 1px solid #e2e8f0; border-radius: 0 0 12px 12px; }
</style>""", unsafe_allow_html=True)

st.title("📑 Sistema Contábil Digital")

# --- NAVEGAÇÃO ---
col_nav = st.columns(5)
opcoes_menu = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes_menu):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()
f1, f2, f3 = st.columns([2, 2, 1])
with f1: data_ini = st.date_input("Início", value=datetime.now().date().replace(day=1))
with f2: data_fim = st.date_input("Fim", value=datetime.now().date())

df_periodo = df[(df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)] if not df.empty else pd.DataFrame()

# --- ABA FLUXO DE CAIXA (COM TRANSPORTE DE SALDO) ---
if st.session_state.menu_opcao == "💸 Fluxo de Caixa":
    st.subheader("🌊 Fluxo de Caixa com Transporte de Saldo")
    
    def calc_acumulado(limite_data, natureza=None):
        if df.empty: return 0.0
        sub = df[df['data_lancamento'] <= limite_data]
        if natureza: sub = sub[sub['natureza'] == natureza]
        if natureza == "Ativo" or natureza is None:
            return sub[sub['status'] == "Entrada"]['valor'].sum() - sub[sub['status'] == "Pago"]['valor'].sum()
        if natureza == "Passivo":
            return sub[sub['tipo'] == "Crédito"]['valor'].sum() - sub[sub['tipo'] == "Débito"]['valor'].sum()
        return 0.0

    si = calc_acumulado(data_ini - timedelta(days=1))
    sf = calc_acumulado(data_fim)
    pa_total = calc_acumulado(data_fim, "Passivo")

    m1, m2, m3 = st.columns(3)
    m1.metric("Saldo Inicial (Vindo do Mês Anterior)", f"R$ {si:,.2f}")
    m2.metric("Saldo Final (Transporta para o Próximo)", f"R$ {sf:,.2f}", delta=f"{sf-si:,.2f}")
    m3.metric("Passivo Total Acumulado", f"R$ {pa_total:,.2f}")

    st.divider()
    
    # Detalhe do Passivo para evitar o erro da imagem image_f4bcde.png
    def filtrar_desc(natureza, keywords):
        if df.empty: return 0.0
        sub = df[(df['data_lancamento'] <= data_fim) & (df['natureza'] == natureza)]
        mask = sub['descricao'].str.contains('|'.join(keywords), case=False, na=False)
        df_f = sub[mask]
        return df_f[df_f['tipo'] == 'Crédito'].valor.sum() - df_f[df_f['tipo'] == 'Débito'].valor.sum()

    forn = filtrar_desc('Passivo', ['FORNECEDOR', 'BOLETO', 'COMPRA'])
    emp = filtrar_desc('Passivo', ['EMPRESTIMO', 'BANCO', 'FINANC'])
    trib = filtrar_desc('Passivo', ['IMPOSTO', 'TRIBUTO', 'DAS'])
    outros_pa = pa_total - (forn + emp + trib)

    col_pa, col_info = st.columns([2, 1])
    with col_pa:
        st.markdown("#### 💸 Detalhamento das Dívidas (Passivo)")
        df_pa_vis = pd.DataFrame([
            {"Item": "🤝 Fornecedores", "Valor": forn},
            {"Item": "🏦 Empréstimos", "Valor": emp},
            {"Item": "⚖️ Tributos", "Valor": trib},
            {"Item": "📋 Outras Obrigações", "Valor": outros_pa},
            {"Item": "📉 TOTAL ACUMULADO", "Valor": pa_total}
        ])
        st.table(df_pa_vis.style.format({"Valor": "R$ {:,.2f}"}))
    with col_info:
        st.info(f"O saldo de **R$ {sf:,.2f}** será o ponto de partida para o período após {data_fim}.")

# --- ABA RAZONETES ---
elif st.session_state.menu_opcao == "📊 Razonetes":
    if df_periodo.empty: st.info("Sem dados.")
    else:
        for grupo in ["Ativo", "Passivo", "Receita", "Despesa"]:
            df_g = df_periodo[df_periodo['natureza'] == grupo]
            if not df_g.empty:
                st.markdown(f"### {grupo}")
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    df_c = df_g[df_g['descricao'] == conta]
                    v_d, v_c = df_c[df_c['tipo'] == 'Débito'].valor.sum(), df_c[df_c['tipo'] == 'Crédito'].valor.sum()
                    saldo = (v_d - v_c) if grupo == "Ativo" else (v_c - v_d)
                    with cols[i % 3]:
                        st.markdown(f'<div class="conta-card"><div class="conta-titulo">{conta}</div>', unsafe_allow_html=True)
                        st.write(f"D: R$ {v_d:,.2f} | C: R$ {v_c:,.2f}")
                        st.markdown(f'<div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>', unsafe_allow_html=True)

# --- OUTRAS ABAS ---
elif st.session_state.menu_opcao == "⚙️ Gestão":
    if st.button("🚨 Resetar"):
        supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
        st.cache_data.clear()
        st.rerun()
