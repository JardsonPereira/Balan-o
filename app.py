import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client, Client

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Terminal Contábil v2.0", layout="wide")

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

# --- FUNÇÃO GERAR PDF (CORRIGIDA PARA BYTES PURO) ---
def gerar_pdf_bytes(dados, titulo_relatorio):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    # Removendo acentos do título para compatibilidade total
    pdf.cell(190, 10, txt=titulo_relatorio.upper(), ln=True, align="C")
    pdf.ln(10)
    
    # Cabeçalho
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(80, 8, "CONTA", border=1)
    pdf.cell(35, 8, "DEBITO", border=1)
    pdf.cell(35, 8, "CREDITO", border=1)
    pdf.cell(40, 8, "SALDO", border=1)
    pdf.ln()
    
    # Dados
    pdf.set_font("Helvetica", "", 9)
    for _, row in dados.iterrows():
        # Limpa caracteres especiais da conta
        conta_limpa = str(row["CONTA"]).encode('ascii', 'ignore').decode('ascii')
        pdf.cell(80, 7, conta_limpa, border=1)
        pdf.cell(35, 7, f"{row['DEBITO']:,.2f}", border=1)
        pdf.cell(35, 7, f"{row['CREDITO']:,.2f}", border=1)
        pdf.cell(40, 7, f"{row['SALDO']:,.2f}", border=1)
        pdf.ln()
    
    # SOLUÇÃO DO ERRO: Converter explicitamente o output para bytes
    pdf_output = pdf.output()
    if isinstance(pdf_output, bytearray):
        return bytes(pdf_output)
    return pdf_output

# --- INTERFACE DE AUTENTICAÇÃO ---
def tela_autenticacao():
    st.markdown("<h2 style='text-align: center; font-family: monospace;'>SISTEMA CONTABIL - ACESSO</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if st.session_state.auth_mode == "login":
            st.subheader("Login")
            email = st.text_input("E-mail").lower().strip()
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res.user
                    st.rerun()
                except: st.error("Erro no login. Verifique e-mail e senha.")
            
            col_a, col_b = st.columns(2)
            if col_a.button("Cadastrar", use_container_width=True):
                st.session_state.auth_mode = "cadastro"; st.rerun()
            if col_b.button("Recuperar Senha", use_container_width=True):
                st.session_state.auth_mode = "recuperar"; st.rerun()

        elif st.session_state.auth_mode == "cadastro":
            st.subheader("Novo Cadastro")
            new_email = st.text_input("E-mail").lower().strip()
            new_pass = st.text_input("Senha", type="password")
            if st.button("Criar Conta", use_container_width=True):
                try:
                    supabase.auth.sign_up({"email": new_email, "password": new_pass})
                    st.success("Verifique seu e-mail para confirmar a conta!")
                except Exception as e: st.error(f"Erro: {e}")
            if st.button("Voltar"): st.session_state.auth_mode = "login"; st.rerun()

        elif st.session_state.auth_mode == "recuperar":
            st.subheader("Recuperar")
            rem_email = st.text_input("E-mail cadastrado").lower().strip()
            if st.button("Enviar link"):
                supabase.auth.reset_password_for_email(rem_email)
                st.info("Link enviado se o e-mail existir.")
            if st.button("Voltar"): st.session_state.auth_mode = "login"; st.rerun()

if st.session_state.user is None:
    tela_autenticacao()
    st.stop()

# --- CARREGAR DADOS ---
user_id = st.session_state.user.id
res_db = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
df = pd.DataFrame(res_db.data)

# --- SIDEBAR OPERACIONAL ---
with st.sidebar:
    st.markdown(f"**Operador:** {st.session_state.user.email}")
    if st.button("Sair"): st.session_state.user = None; st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df.empty:
        items = df[df['id'] == st.session_state.edit_id]
        item_edit = items.iloc[0] if not items.empty else {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}
    else:
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"f_{st.session_state.form_count}"):
        contas_lista = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        sel = st.selectbox("CONTA", ["(NOVA)"] + contas_lista)
        desc = st.text_input("NOME", value=item_edit['descricao']).upper() if sel == "(NOVA)" else sel
        nat = st.selectbox("GRUPO", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit['natureza']))
        tipo = st.radio("TIPO", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("VALOR", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_input("HISTORICO", value=item_edit['justificativa'])
        if st.form_submit_button("PROCESSAR"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
            if st.session_state.edit_id: supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
            else: supabase.table("lancamentos").insert(payload).execute()
            st.session_state.edit_id = None; st.session_state.form_count += 1; st.rerun()

# --- CSS TERMINAL ---
st.markdown("""
<style>
    .terminal-header { background: #1e293b; color: #38bdf8; padding: 10px; font-family: monospace; border-radius: 4px; border-left: 5px solid #38bdf8; margin-bottom: 20px; }
    .razonete-box { border: 2px solid #1e293b; border-radius: 4px; background: white; margin-bottom: 20px; font-family: monospace; }
    .razonete-header { background: #1e293b; color: white; text-align: center; padding: 5px; font-weight: bold; }
    .col-label { font-size: 10px; color: #64748b; font-weight: bold; border-bottom: 1px solid #e2e8f0; margin-bottom: 5px; }
    .total-box { background: #f1f5f9; border-top: 2px solid #1e293b; padding: 5px; text-align: right; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='terminal-header'>SISTEMA DE CONSULTA > MODULO CONTABIL</div>", unsafe_allow_html=True)

# Navegação
cols_nav = st.columns(4)
botoes_nav = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "⚙️ Gestão"]
for i, b_name in enumerate(botoes_nav):
    if cols_nav[i].button(b_name, use_container_width=True): st.session_state.menu_opcao = b_name

st.divider()

if not df.empty:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for n_label in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df[df['natureza'] == n_label]
            if not df_g.empty:
                st.subheader(f"📁 {n_label.upper()}")
                cols_raz = st.columns(2)
                for i, c_nome in enumerate(sorted(df_g['descricao'].unique())):
                    with cols_raz[i % 2]:
                        df_c = df_g[df_g['descricao'] == c_nome]
                        v_d, v_c = df_c[df_c['tipo']=='Débito']['valor'].sum(), df_c[df_c['tipo']=='Crédito']['valor'].sum()
                        saldo = v_d - v_c
                        st.markdown(f"<div class='razonete-box'><div class='razonete-header'>{c_nome}</div>", unsafe_allow_html=True)
                        ca, cb = st.columns(2)
                        with ca:
                            st.markdown("<div style='padding:5px;'><div class='col-label'>DEBITO (D)</div>", unsafe_allow_html=True)
                            for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows(): st.write(f"🟢 {r['valor']:,.2f}")
                            st.markdown("</div>", unsafe_allow_html=True)
                        with cb:
                            st.markdown("<div style='padding:5px;'><div class='col-label' style='text-align:right'>CREDITO (C)</div>", unsafe_allow_html=True)
                            for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows(): st.markdown(f"<div style='text-align:right; color:red;'>{r['valor']:,.2f} 🔴</div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='total-box'>SALDO: R$ {abs(saldo):,.2f} ({'D' if saldo>=0 else 'C'})</div></div>", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("BALANCETE")
        bal_list = []
        for c_n in sorted(df['descricao'].unique()):
            temp = df[df['descricao'] == c_n]
            d_s, c_s = temp[temp['tipo'] == 'Débito']['valor'].sum(), temp[temp['tipo'] == 'Crédito']['valor'].sum()
            bal_list.append({"CONTA": c_n, "DEBITO": d_s, "CREDITO": c_s, "SALDO": d_s-c_s})
        df_bal = pd.DataFrame(bal_list)
        st.table(df_bal)
        
        # Download do PDF blindado
        try:
            pdf_data = gerar_pdf_bytes(df_bal, "BALANCETE DE VERIFICACAO")
            st.download_button(
                label="📥 Baixar PDF do Balancete",
                data=pdf_data,
                file_name="balancete.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("DRE")
        rec, des, enc = df[df['natureza'] == 'Receita']['valor'].sum(), df[df['natureza'] == 'Despesa']['valor'].sum(), df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        st.code(f"RECEITA: {rec:,.2f}\nDESPESA: {des:,.2f}\nFINANC:  {enc:,.2f}\nTOTAL:   {rec-des-enc:,.2f}")

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        for _, r in df.iterrows():
            with st.expander(f"{r['descricao']} - R$ {r['valor']:,.2f}"):
                c1, c2 = st.columns(2)
                if c1.button("Editar", key=f"e_{r['id']}"): st.session_state.edit_id = r['id']; st.rerun()
                if c2.button("Excluir", key=f"d_{r['id']}"): supabase.table("lancamentos").delete().eq("id", r['id']).execute(); st.rerun()
else:
    st.info("Terminal vazio.")
