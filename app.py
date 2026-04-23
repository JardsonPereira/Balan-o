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
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(190, 10, txt=titulo_relatorio.upper(), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 8)
    # Colunas conforme o novo modelo
    cols = [("CONTA", 70), ("DEBITO", 30), ("CREDITO", 30), ("S. DEV", 30), ("S. CRE", 30)]
    for txt, w in cols: pdf.cell(w, 8, txt, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for _, row in dados.iterrows():
        pdf.cell(70, 7, str(row["CONTA"])[:40], border=1)
        pdf.cell(30, 7, f"{row['DEBITO']:,.2f}", border=1, align="R")
        pdf.cell(30, 7, f"{row['CREDITO']:,.2f}", border=1, align="R")
        pdf.cell(30, 7, f"{row['SALDO DEVEDOR']:,.2f}", border=1, align="R")
        pdf.cell(30, 7, f"{row['SALDO CREDOR']:,.2f}", border=1, align="R")
        pdf.ln()
    return bytes(pdf.output()) if isinstance(pdf.output(), bytearray) else pdf.output()

# --- INTERFACE DE AUTENTICAÇÃO ---
def tela_autenticacao():
    st.markdown("<div style='text-align: center; padding: 2rem 0;'><h1 style='color: #1e3a8a;'>ERP CONTÁBIL PRO</h1></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.container(border=True):
            if st.session_state.auth_mode == "login":
                st.subheader("Entrar")
                email = st.text_input("Usuário").lower().strip()
                senha = st.text_input("Senha", type="password")
                if st.button("Acessar", use_container_width=True, type="primary"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state.user = res.user
                        st.rerun()
                    except: st.error("Erro de acesso.")
                if st.button("Criar Conta", use_container_width=True): st.session_state.auth_mode = "cadastro"; st.rerun()
            elif st.session_state.auth_mode == "cadastro":
                st.subheader("Nova Conta")
                new_email = st.text_input("E-mail").lower().strip()
                new_pass = st.text_input("Senha", type="password")
                if st.button("Registrar", use_container_width=True, type="primary"):
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
    if st.button("Sair", use_container_width=True): st.session_state.user = None; st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df.empty:
        st.subheader("📝 Editar")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.subheader("➕ Novo")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"f_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        sel = st.selectbox("Conta", ["(NOVA)"] + contas_existentes)
        desc = st.text_input("Nome da Conta", value=item_edit['descricao']).upper() if sel == "(NOVA)" else sel
        nat = st.selectbox("Grupo", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_input("Histórico", value=item_edit['justificativa'])
        if st.form_submit_button("Salvar", use_container_width=True, type="primary"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
            if st.session_state.edit_id: supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
            else: supabase.table("lancamentos").insert(payload).execute()
            st.session_state.edit_id = None; st.session_state.form_count += 1; st.rerun()

# --- CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .razonete-card { background: white; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 1.5rem; overflow: hidden; }
    .razonete-header { background: #0f172a; color: white; padding: 8px; font-weight: 600; text-align: center; font-size: 0.8rem; }
    .total-footer { background: #f8fafc; padding: 8px; text-align: center; font-weight: bold; font-size: 0.8rem; border-top: 1px solid #e2e8f0; }
    .group-label { background: #e2e8f0; color: #1e293b; padding: 5px 12px; border-radius: 4px; font-weight: 700; margin-top: 1rem; font-size: 0.7rem; }
</style>
""", unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
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
                st.markdown(f"<div class='group-label'>{n_label.upper()}</div>", unsafe_allow_html=True)
                cols_raz = st.columns(3)
                for i, c_nome in enumerate(sorted(df_g['descricao'].unique())):
                    with cols_raz[i % 3]:
                        df_c = df_g[df_g['descricao'] == c_nome]
                        v_d, v_c = df_c[df_c['tipo']=='Débito']['valor'].sum(), df_c[df_c['tipo']=='Crédito']['valor'].sum()
                        saldo = v_d - v_c
                        st.markdown(f"<div class='razonete-card'><div class='razonete-header'>{c_nome}</div>", unsafe_allow_html=True)
                        t1, t2 = st.columns(2)
                        with t1:
                            st.caption("DÉBITO")
                            for v in df_c[df_c['tipo']=='Débito']['valor']: st.write(f"R$ {v:,.2f}")
                        with t2:
                            st.caption("CRÉDITO")
                            for v in df_c[df_c['tipo']=='Crédito']['valor']: st.write(f"R$ {v:,.2f}")
                        st.markdown(f"<div class='total-footer'>SALDO: R$ {abs(saldo):,.2f} ({'D' if saldo>=0 else 'C'})</div></div>", unsafe_allow_html=True)

    elif opcao == "🧾 Balancete":
        st.subheader("Balancete de Verificação")
        bal_data = []
        for c_n in sorted(df['descricao'].unique()):
            temp = df[df['descricao'] == c_n]
            d_s = temp[temp['tipo'] == 'Débito']['valor'].sum()
            c_s = temp[temp['tipo'] == 'Crédito']['valor'].sum()
            saldo_atual = d_s - c_s
            bal_data.append({
                "CONTA": c_n,
                "DEBITO": d_s,
                "CREDITO": c_s,
                "SALDO DEVEDOR": saldo_atual if saldo_atual > 0 else 0,
                "SALDO CREDOR": abs(saldo_atual) if saldo_atual < 0 else 0
            })
        df_bal = pd.DataFrame(bal_data)
        
        # Exibição da Tabela conforme modelo
        st.table(df_bal.style.format({c: "{:,.2f}" for c in ["DEBITO", "CREDITO", "SALDO DEVEDOR", "SALDO CREDOR"]}))
        
        # Totais
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Débito", f"{df_bal['DEBITO'].sum():,.2f}")
        c2.metric("Total Crédito", f"{df_bal['CREDITO'].sum():,.2f}")
        c3.metric("Total Devedor", f"{df_bal['SALDO DEVEDOR'].sum():,.2f}")
        c4.metric("Total Credor", f"{df_bal['SALDO CREDOR'].sum():,.2f}")
        
        pdf_bytes = gerar_pdf_bytes(df_bal, "BALANCETE DE VERIFICACAO")
        st.download_button("📥 Baixar PDF", data=pdf_bytes, file_name="balancete.pdf")

    elif opcao == "📈 DRE":
        st.subheader("DRE Detalhada")
        rec = df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum()
        des = df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros'].groupby('descricao')['valor'].sum()
        st.success(f"LUCRO LÍQUIDO: R$ {(rec.sum() - des.sum() - enc.sum()):,.2f}")
        with st.expander("Ver Receitas"): st.write(rec)
        with st.expander("Ver Despesas"): st.write(des)

    elif opcao == "⚙️ Gestão":
        st.subheader("Manutenção")
        for _, r in df.iterrows():
            with st.container(border=True):
                c_a, c_b = st.columns([4, 1])
                c_a.write(f"**{r['descricao']}** | {r['natureza']} | {r['tipo']}")
                if c_b.button("✏️", key=f"e_{r['id']}"): st.session_state.edit_id = r['id']; st.rerun()
                if c_b.button("🗑️", key=f"d_{r['id']}"): supabase.table("lancamentos").delete().eq("id", r['id']).execute(); st.rerun()
else:
    st.info("Inicie os lançamentos na barra lateral.")
