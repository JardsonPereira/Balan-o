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
    return bytes(pdf.output())

# --- INTERFACE DE AUTENTICAÇÃO ---
def tela_autenticacao():
    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>ERP CONTÁBIL PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.container(border=True):
            if st.session_state.auth_mode == "login":
                st.subheader("Login")
                email = st.text_input("Usuário").lower().strip()
                senha = st.text_input("Senha", type="password")
                if st.button("Acessar Painel", use_container_width=True, type="primary"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state.user = res.user
                        st.rerun()
                    except: st.error("Acesso negado.")
                if st.button("Cadastrar", use_container_width=True): st.session_state.auth_mode = "cadastro"; st.rerun()

            elif st.session_state.auth_mode == "cadastro":
                st.subheader("Nova Conta")
                new_email = st.text_input("E-mail").lower().strip()
                new_pass = st.text_input("Senha", type="password")
                if st.button("Criar Conta", use_container_width=True, type="primary"):
                    try:
                        supabase.auth.sign_up({"email": new_email, "password": new_pass})
                        st.success("Verifique seu e-mail!")
                    except Exception as e: st.error(f"Erro: {e}")
                if st.button("Voltar"): st.session_state.auth_mode = "login"; st.rerun()

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
    st.caption(f"Usuário: {st.session_state.user.email}")
    if st.button("Encerrar Sessão", use_container_width=True): st.session_state.user = None; st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df.empty:
        st.subheader("📝 Editar Lançamento")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.subheader("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"f_{st.session_state.form_count}"):
        contas_lista = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        sel = st.selectbox("Conta Contábil", ["(NOVA CONTA)"] + contas_lista)
        desc = st.text_input("Título da Conta", value=item_edit['descricao']).upper() if sel == "(NOVA CONTA)" else sel
        nat = st.selectbox("Grupo Financeiro", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit['natureza']))
        tipo = st.radio("Natureza", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_input("Histórico", value=item_edit['justificativa'])
        if st.form_submit_button("Efetivar Registro", use_container_width=True, type="primary"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
            if st.session_state.edit_id: supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
            else: supabase.table("lancamentos").insert(payload).execute()
            st.session_state.edit_id = None; st.session_state.form_count += 1; st.rerun()

# --- CSS ESTILIZAÇÃO ---
st.markdown("""
<style>
    .razonete-container { background: white; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .razonete-title { background: #0f172a; color: white; padding: 10px; text-align: center; font-weight: bold; border-radius: 8px 8px 0 0; font-size: 14px; }
    .group-header { background: #e2e8f0; padding: 8px; border-radius: 6px; font-weight: bold; margin: 20px 0 10px 0; color: #1e293b; text-transform: uppercase; font-size: 12px; }
    .total-row { background: #f8fafc; padding: 8px; border-top: 1px solid #e2e8f0; text-align: center; font-weight: bold; border-radius: 0 0 8px 8px; }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
st.markdown("<h2 style='color: #0f172a;'>Painel de Controle</h2>", unsafe_allow_html=True)
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
                st.markdown(f"<div class='group-header'>{n_label}</div>", unsafe_allow_html=True)
                cols_raz = st.columns(3)
                for i, c_nome in enumerate(sorted(df_g['descricao'].unique())):
                    with cols_raz[i % 3]:
                        df_c = df_g[df_g['descricao'] == c_nome]
                        v_d, v_c = df_c[df_c['tipo']=='Débito']['valor'].sum(), df_c[df_c['tipo']=='Crédito']['valor'].sum()
                        saldo = v_d - v_c
                        
                        # Renderização Segura do Razonete
                        st.markdown(f"<div class='razonete-container'><div class='razonete-title'>{c_nome}</div>", unsafe_allow_html=True)
                        t_col1, t_col2 = st.columns(2)
                        with t_col1:
                            st.caption("DÉBITO (D)")
                            for val in df_c[df_c['tipo'] == 'Débito']['valor']:
                                st.write(f"🟢 {val:,.2f}")
                        with t_col2:
                            st.caption("CRÉDITO (C)")
                            for val in df_c[df_c['tipo'] == 'Crédito']['valor']:
                                st.write(f"🔴 {val:,.2f}")
                        st.markdown(f"<div class='total-row'>SALDO: R$ {abs(saldo):,.2f} ({'D' if saldo>=0 else 'C'})</div></div>", unsafe_allow_html=True)

    elif opcao == "🧾 Balancete":
        st.subheader("Balancete de Verificação")
        bal_list = []
        for c_n in sorted(df['descricao'].unique()):
            temp = df[df['descricao'] == c_n]
            d_s, c_s = temp[temp['tipo'] == 'Débito']['valor'].sum(), temp[temp['tipo'] == 'Crédito']['valor'].sum()
            bal_list.append({"CONTA": c_n, "DEBITO": d_s, "CREDITO": c_s})
        df_bal = pd.DataFrame(bal_list)
        st.table(df_bal.style.format({c: "{:,.2f}" for c in ["DEBITO", "CREDITO"]}))
        st.download_button("📥 Baixar PDF", data=gerar_pdf_bytes(df_bal, "BALANCETE"), file_name="balancete.pdf")

    elif opcao == "📈 DRE":
        st.subheader("Demonstração do Resultado")
        df_rec = df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum()
        df_des = df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum()
        df_enc = df[df['natureza'] == 'Encargos Financeiros'].groupby('descricao')['valor'].sum()
        lucro = df_rec.sum() - df_des.sum() - df_enc.sum()
        st.metric("LUCRO LÍQUIDO", f"R$ {lucro:,.2f}")
        with st.expander("Detalhamento"):
            st.write("Receitas:", df_rec)
            st.write("Despesas:", df_des)

    elif opcao == "⚙️ Gestão":
        for _, r in df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{r['descricao']}** | {r['natureza']} | {r['tipo']} | R$ {r['valor']:,.2f}")
                if c2.button("✏️", key=f"e_{r['id']}"): st.session_state.edit_id = r['id']; st.rerun()
                if c2.button("🗑️", key=f"d_{r['id']}"): supabase.table("lancamentos").delete().eq("id", r['id']).execute(); st.rerun()
else:
    st.info("Nenhum lançamento encontrado.")
