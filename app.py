import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client, Client

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Terminal Contábil v2.0", layout="wide")

# Conexão Supabase (Lógica Original Mantida)
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets.")
    st.stop()

# --- ESTADOS (Estrutura Atualizada Mantida) ---
if 'user' not in st.session_state: st.session_state.user = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'menu_opcao' not in st.session_state: st.session_state.menu_opcao = "📊 Razonetes"

# --- FUNÇÃO GERAR PDF (Nova Opção Acrescentada) ---
def gerar_pdf_contabil(dados, titulo_relatorio):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, txt="RELATORIO CONTABIL DIGITAL", ln=True, align="C")
    pdf.set_font("Arial", "I", 10)
    pdf.cell(190, 10, txt=f"Tipo: {titulo_relatorio}", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(80, 8, "CONTA", border=1)
    pdf.cell(35, 8, "DEBITO", border=1)
    pdf.cell(35, 8, "CREDITO", border=1)
    pdf.cell(40, 8, "SALDO", border=1)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in dados.iterrows():
        pdf.cell(80, 7, str(row["CONTA"]), border=1)
        pdf.cell(35, 7, f"{row['DEBITO']:,.2f}", border=1)
        pdf.cell(35, 7, f"{row['CREDITO']:,.2f}", border=1)
        pdf.cell(40, 7, f"{row['SALDO']:,.2f}", border=1)
        pdf.ln()
    return pdf.output()

# --- LOGIN ---
if st.session_state.user is None:
    st.markdown("<h2 style='text-align: center; font-family: monospace;'>SISTEMA CONTABIL - ACESSO</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        email = st.text_input("Usuario")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Falha no login.")
    st.stop()

user_id = st.session_state.user.id

# Carregar Dados (Lógica de Cache/Supabase)
res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
df = pd.DataFrame(res.data)

# --- SIDEBAR (INPUT ORIGINAL) ---
with st.sidebar:
    st.markdown("### 📟 TERMINAL OPERACIONAL")
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()
    st.divider()
    
    if st.session_state.edit_id:
        st.subheader("📝 EDITAR")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.subheader("➕ NOVO")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"f_{st.session_state.form_count}"):
        contas = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        conta_sel = st.selectbox("CONTA", ["(NOVA CONTA)"] + contas)
        desc = st.text_input("NOME", value=item_edit['descricao']).upper() if conta_sel == "(NOVA CONTA)" else conta_sel
        nat = st.selectbox("GRUPO", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit['natureza']))
        tipo = st.radio("TIPO", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("VALOR", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_input("HISTORICO", value=item_edit['justificativa'])
        
        if st.form_submit_button("PROCESSAR LANÇAMENTO"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.session_state.form_count += 1
            st.rerun()

# --- CSS TERMINAL (Aprimorado) ---
st.markdown("""
<style>
    .terminal-header { background: #1e293b; color: #38bdf8; padding: 10px; font-family: monospace; border-radius: 4px; border-left: 5px solid #38bdf8; margin-bottom: 20px; }
    .razonete-box { border: 2px solid #1e293b; border-radius: 4px; background: white; margin-bottom: 20px; font-family: monospace; }
    .razonete-header { background: #1e293b; color: white; text-align: center; padding: 5px; font-weight: bold; border-bottom: 2px solid #1e293b; }
    .col-label { font-size: 10px; color: #64748b; font-weight: bold; border-bottom: 1px solid #e2e8f0; margin-bottom: 5px; }
    .total-box { background: #f1f5f9; border-top: 2px solid #1e293b; padding: 5px; text-align: right; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='terminal-header'>TERMINAL DE CONSULTA CONTABIL > BASE DE DADOS</div>", unsafe_allow_html=True)

# Navegação (Abas de Sistema)
n1, n2, n3, n4 = st.columns(4)
if n1.button("📊 Razonetes", use_container_width=True): st.session_state.menu_opcao = "📊 Razonetes"
if n2.button("🧾 Balancete", use_container_width=True): st.session_state.menu_opcao = "🧾 Balancete"
if n3.button("📈 DRE", use_container_width=True): st.session_state.menu_opcao = "📈 DRE"
if n4.button("⚙️ Gestão", use_container_width=True): st.session_state.menu_opcao = "⚙️ Gestão"

st.divider()

if not df.empty:
    opcao = st.session_state.menu_opcao
    
    if opcao == "📊 Razonetes":
        for nat in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df[df['natureza'] == nat]
            if not df_g.empty:
                st.subheader(f"📁 GRUPO: {nat.upper()}")
                cols = st.columns(2)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    with cols[i % 2]:
                        df_c = df_g[df_g['descricao'] == conta]
                        v_d, v_c = df_c[df_c['tipo']=='Débito']['valor'].sum(), df_c[df_c['tipo']=='Crédito']['valor'].sum()
                        saldo = v_d - v_c
                        
                        # Layout fixo para evitar erro de tags HTML vazando
                        st.markdown(f"<div class='razonete-box'><div class='razonete-header'>{conta}</div>", unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("<div style='padding:5px;'><div class='col-label'>DEBITO (D)</div>", unsafe_allow_html=True)
                            for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows():
                                st.write(f"🟢 {r['valor']:,.2f}")
                            st.markdown("</div>", unsafe_allow_html=True)
                        with c2:
                            st.markdown("<div style='padding:5px;'><div class='col-label' style='text-align:right'>CREDITO (C)</div>", unsafe_allow_html=True)
                            for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows():
                                st.markdown(f"<div style='text-align:right; color:red;'>{r['valor']:,.2f} 🔴</div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='total-box'>SALDO ATUAL: R$ {abs(saldo):,.2f} ({'D' if saldo>=0 else 'C'})</div></div>", unsafe_allow_html=True)

    elif opcao == "🧾 Balancete":
        st.subheader("BALANCETE GERAL")
        bal_data = []
        for c in sorted(df['descricao'].unique()):
            temp = df[df['descricao'] == c]
            d, cr = temp[temp['tipo'] == 'Débito']['valor'].sum(), temp[temp['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"CONTA": c, "DEBITO": d, "CREDITO": cr, "SALDO": d-cr})
        df_bal = pd.DataFrame(bal_data)
        st.table(df_bal)
        st.download_button("📥 Gerar PDF do Balancete", gerar_pdf_contabil(df_bal, "BALANCETE"), "balancete.pdf")

    elif opcao == "📈 DRE":
        st.subheader("RESULTADO DO EXERCICIO")
        rec, des, enc = df[df['natureza'] == 'Receita']['valor'].sum(), df[df['natureza'] == 'Despesa']['valor'].sum(), df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        st.code(f"TOTAL RECEITAS: {rec:,.2f}\nTOTAL DESPESAS: {des:,.2f}\nENC. FINANCEIR.: {enc:,.2f}\n--------------------------\nRESULTADO FINAL: {rec-des-enc:,.2f}")

    elif opcao == "⚙️ Gestão":
        st.subheader("MANUTENÇÃO DE DADOS")
        for _, r in df.iterrows():
            with st.expander(f"ID {r['id']} - {r['descricao']} (R$ {r['valor']:,.2f})"):
                if st.button("Remover Registro", key=f"del_{r['id']}"):
                    supabase.table("lancamentos").delete().eq("id", r['id']).execute()
                    st.rerun()
else:
    st.info("Terminal vazio. Insira um lançamento na barra lateral.")
