import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client, Client

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="ERP Contábil Pro", layout="wide", initial_sidebar_state="expanded")

# Conexão Supabase
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets.")
    st.stop()

# --- ESTADOS ---
if 'user' not in st.session_state: st.session_state.user = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'menu_opcao' not in st.session_state: st.session_state.menu_opcao = "📊 Razonetes"
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = "login"

# --- FUNÇÃO GERAR PDF ---
def gerar_pdf_bytes(dados, titulo_relatorio):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(190, 10, txt=titulo_relatorio.upper(), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(110, 8, "CONTA", border=1)
    pdf.cell(40, 8, "DEBITO", border=1)
    pdf.cell(40, 8, "CREDITO", border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for _, row in dados.iterrows():
        conta_limpa = str(row["CONTA"]).encode('ascii', 'ignore').decode('ascii')
        pdf.cell(110, 7, conta_limpa, border=1)
        pdf.cell(40, 7, f"{row['DEBITO']:,.2f}", border=1)
        pdf.cell(40, 7, f"{row['CREDITO']:,.2f}", border=1)
        pdf.ln()
    pdf_output = pdf.output()
    return bytes(pdf_output) if isinstance(pdf_output, bytearray) else pdf_output

# --- INTERFACE DE AUTENTICAÇÃO ---
def tela_autenticacao():
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='color: #1e3a8a; font-family: sans-serif;'>ERP CONTÁBIL PRO</h1>
            <p style='color: #64748b;'>Sistema Integrado de Gestão Financeira</p>
        </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.container(border=True):
            if st.session_state.auth_mode == "login":
                st.subheader("Entrar no Sistema")
                email = st.text_input("Usuário").lower().strip()
                senha = st.text_input("Senha", type="password")
                if st.button("Acessar Painel", use_container_width=True, type="primary"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state.user = res.user
                        st.rerun()
                    except: st.error("Acesso negado.")
                st.divider()
                if st.button("Solicitar Novo Cadastro", use_container_width=True): st.session_state.auth_mode = "cadastro"; st.rerun()

            elif st.session_state.auth_mode == "cadastro":
                st.subheader("Nova Conta")
                new_email = st.text_input("E-mail corporativo").lower().strip()
                new_pass = st.text_input("Senha", type="password")
                if st.button("Finalizar Registro", use_container_width=True, type="primary"):
                    try:
                        supabase.auth.sign_up({"email": new_email, "password": new_pass})
                        st.success("Verifique seu e-mail para ativar!")
                    except Exception as e: st.error(f"Erro: {e}")
                if st.button("Voltar ao Login", use_container_width=True): st.session_state.auth_mode = "login"; st.rerun()

if st.session_state.user is None:
    tela_autenticacao()
    st.stop()

# --- CARREGAR DADOS ---
user_id = st.session_state.user.id
res_db = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
df = pd.DataFrame(res_db.data)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 🏢 Enterprise Panel")
    st.caption(f"Logado como: {st.session_state.user.email}")
    if st.button("Encerrar Sessão", use_container_width=True): st.session_state.user = None; st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df.empty:
        st.subheader("📝 Editar Registro")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.subheader("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"f_{st.session_state.form_count}"):
        contas_lista = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        sel = st.selectbox("Conta Contábil", ["(NOVA CONTA)"] + contas_lista)
        desc = st.text_input("Título da Conta", value=item_edit['descricao']).upper() if sel == "(NOVA CONTA)" else sel
        nat = st.selectbox("Grupo Financeiro", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit['natureza']))
        tipo = st.radio("Natureza da Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor Nominal (R$)", min_value=0.0, step=10.0, value=float(item_edit['valor']))
        just = st.text_input("Histórico/Justificativa", value=item_edit['justificativa'])
        if st.form_submit_button("Efetivar Registro", use_container_width=True, type="primary"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
            if st.session_state.edit_id: supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
            else: supabase.table("lancamentos").insert(payload).execute()
            st.session_state.edit_id = None; st.session_state.form_count += 1; st.rerun()

# --- CSS SISTEMA REAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }
    .razonete-card { background: white; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 1.5rem; overflow: hidden; }
    .razonete-header { background: #0f172a; color: white; padding: 8px; font-weight: 600; font-size: 0.85rem; text-align: center; }
    .t-account-body { display: flex; min-height: 80px; position: relative; border-bottom: 1px solid #e2e8f0; }
    .t-account-body::after { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: #e2e8f0; }
    .t-col { flex: 1; padding: 10px; font-size: 0.8rem; }
    .total-footer { background: #f8fafc; padding: 8px; text-align: center; font-weight: bold; font-size: 0.8rem; color: #1e293b; }
    .group-label { background: #e2e8f0; color: #1e293b; padding: 6px 12px; border-radius: 6px; font-weight: 700; margin: 1.5rem 0 1rem 0; font-size: 0.75rem; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- CORPO PRINCIPAL ---
st.markdown("<h2 style='color: #0f172a; font-weight: 700;'>Dashboard Contábil</h2>", unsafe_allow_html=True)

nav = st.columns(4)
if nav[0].button("📊 Razonetes", use_container_width=True): st.session_state.menu_opcao = "📊 Razonetes"
if nav[1].button("🧾 Balancete", use_container_width=True): st.session_state.menu_opcao = "🧾 Balancete"
if nav[2].button("📈 DRE", use_container_width=True): st.session_state.menu_opcao = "📈 DRE"
if nav[3].button("⚙️ Gestão", use_container_width=True): st.session_state.menu_opcao = "⚙️ Gestão"

st.divider()

if not df.empty:
    opcao = st.session_state.menu_opcao
    
    if opcao == "📊 Razonetes":
        for n_label in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df[df['natureza'] == n_label]
            if not df_g.empty:
                st.markdown(f"<div class='group-label'>{n_label}</div>", unsafe_allow_html=True)
                contas = sorted(df_g['descricao'].unique())
                cols_raz = st.columns(3)
                for i, c_nome in enumerate(contas):
                    with cols_raz[i % 3]:
                        df_c = df_g[df_g['descricao'] == c_nome]
                        v_d = df_c[df_c['tipo']=='Débito']['valor'].sum()
                        v_c = df_c[df_c['tipo']=='Crédito']['valor'].sum()
                        saldo = v_d - v_c
                        
                        # Renderização segura para evitar vazamento de código
                        st.markdown(f"<div class='razonete-card'><div class='razonete-header'>{c_nome}</div>", unsafe_allow_html=True)
                        
                        t1, t2 = st.columns(2)
                        with t1:
                            st.markdown("<div style='font-size: 10px; color: gray; border-bottom: 1px solid #eee; margin-bottom: 5px;'>DÉBITO</div>", unsafe_allow_html=True)
                            for v in df_c[df_c['tipo']=='Débito']['valor']:
                                st.markdown(f"<div style='color:green; font-size:12px;'>{v:,.2f}</div>", unsafe_allow_html=True)
                        with t2:
                            st.markdown("<div style='font-size: 10px; color: gray; border-bottom: 1px solid #eee; margin-bottom: 5px; text-align: right;'>CRÉDITO</div>", unsafe_allow_html=True)
                            for v in df_c[df_c['tipo']=='Crédito']['valor']:
                                st.markdown(f"<div style='color:red; font-size:12px; text-align: right;'>{v:,.2f}</div>", unsafe_allow_html=True)
                        
                        st.markdown(f"<div class='total-footer'>SALDO: R$ {abs(saldo):,.2f} ({'D' if saldo>=0 else 'C'})</div></div>", unsafe_allow_html=True)

    elif opcao == "🧾 Balancete":
        st.subheader("Balancete de Verificação")
        bal_list = []
        for c_n in sorted(df['descricao'].unique()):
            temp = df[df['descricao'] == c_n]
            d_s, c_s = temp[temp['tipo'] == 'Débito']['valor'].sum(), temp[temp['tipo'] == 'Crédito']['valor'].sum()
            bal_list.append({"CONTA": c_n, "DEBITO": d_s, "CREDITO": c_s})
        df_bal = pd.DataFrame(bal_list)
        st.table(df_bal.style.format({c: "{:,.2f}" for c in ["DEBITO", "CREDITO"]}))
        
        pdf_data = gerar_pdf_bytes(df_bal, "BALANCETE")
        st.download_button("💾 Exportar PDF", data=pdf_data, file_name="balancete.pdf")

    elif opcao == "📈 DRE":
        st.subheader("Demonstração do Resultado")
        df_rec = df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum()
        df_des = df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum()
        df_enc = df[df['natureza'] == 'Encargos Financeiros'].groupby('descricao')['valor'].sum()
        rec_t, des_t, enc_t = df_rec.sum(), df_des.sum(), df_enc.sum()
        lucro = rec_t - des_t - enc_t
        
        st.metric("LUCRO LÍQUIDO", f"R$ {lucro:,.2f}")
        with st.expander("Detalhamento de Receitas"):
            for n, v in df_rec.items(): st.write(f"{n}: R$ {v:,.2f}")
        with st.expander("Detalhamento de Despesas"):
            for n, v in df_des.items(): st.write(f"{n}: R$ {v:,.2f}")

    elif opcao == "⚙️ Gestão":
        st.subheader("Manutenção de Registros")
        for _, r in df.iterrows():
            with st.container(border=True):
                c_inf, c_btn = st.columns([4, 1])
                c_inf.write(f"**{r['descricao']}** ({r['natureza']})")
                c_inf.caption(f"Operação: {r['tipo']} | Valor: R$ {r['valor']:,.2f}")
                if c_btn.button("✏️", key=f"e_{r['id']}"): 
                    st.session_state.edit_id = r['id']; st.rerun()
                if c_btn.button("🗑️", key=f"d_{r['id']}"): 
                    supabase.table("lancamentos").delete().eq("id", r['id']).execute(); st.rerun()
else:
    st.info("Nenhum lançamento encontrado.")
