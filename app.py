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
    st.error("Erro de conexão. Verifique as Secrets no Streamlit Cloud.")
    st.stop()

# --- ESTADOS DO SISTEMA ---
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
    pdf.cell(70, 8, "CONTA", border=1, align="C")
    pdf.cell(30, 8, "DEBITO", border=1, align="C")
    pdf.cell(30, 8, "CREDITO", border=1, align="C")
    pdf.cell(30, 8, "S. DEV", border=1, align="C")
    pdf.cell(30, 8, "S. CRE", border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for _, row in dados.iterrows():
        pdf.cell(70, 7, str(row["CONTA"])[:40], border=1)
        pdf.cell(30, 7, f"{row['DEBITO']:,.2f}", border=1, align="R")
        pdf.cell(30, 7, f"{row['CREDITO']:,.2f}", border=1, align="R")
        pdf.cell(30, 7, f"{row['SALDO DEVEDOR']:,.2f}", border=1, align="R")
        pdf.cell(30, 7, f"{row['SALDO CREDOR']:,.2f}", border=1, align="R")
        pdf.ln()
    pdf_out = pdf.output()
    return bytes(pdf_out) if isinstance(pdf_out, bytearray) else pdf_out

# --- INTERFACE DE AUTENTICAÇÃO ---
def tela_autenticacao():
    st.markdown("<div style='text-align: center; padding: 2rem 0;'><h1 style='color: #1e3a8a;'>ERP CONTÁBIL PRO</h1></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.container(border=True):
            if st.session_state.auth_mode == "login":
                st.subheader("Login")
                email = st.text_input("Usuário").lower().strip()
                senha = st.text_input("Senha", type="password")
                if st.button("Acessar", use_container_width=True, type="primary"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state.user = res.user
                        st.rerun()
                    except: st.error("Acesso negado.")
                if st.button("Criar Nova Conta", use_container_width=True): 
                    st.session_state.auth_mode = "cadastro"; st.rerun()
            elif st.session_state.auth_mode == "cadastro":
                st.subheader("Cadastro")
                new_email = st.text_input("E-mail").lower().strip()
                new_pass = st.text_input("Senha", type="password")
                if st.button("Registrar", use_container_width=True, type="primary"):
                    try:
                        supabase.auth.sign_up({"email": new_email, "password": new_pass})
                        st.success("Verifique seu e-mail para ativar!")
                    except Exception as e: st.error(f"Erro: {e}")
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
    st.markdown(f"### 🏢 Enterprise Panel")
    if st.button("Encerrar Sessão", use_container_width=True): st.session_state.user = None; st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df.empty:
        st.subheader("📝 Editar Registro")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.subheader("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "categoria_dfc": "Operacional"}

    with st.form(key=f"f_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        sel = st.selectbox("Conta Contábil", ["(NOVA)"] + contas_existentes)
        desc = st.text_input("Nome da Conta", value=item_edit['descricao']).upper() if sel == "(NOVA)" else sel
        nat = st.selectbox("Grupo", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit['natureza']))
        
        # --- NOVO: CATEGORIA DFC ---
        cat_dfc_list = ["Operacional", "Investimento", "Financiamento", "N/A (Não Financeiro)"]
        cat_dfc = st.selectbox("Categoria DFC (Fluxo de Caixa)", cat_dfc_list, index=cat_dfc_list.index(item_edit.get('categoria_dfc', 'Operacional')))
        
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_input("Histórico/Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Salvar Registro", use_container_width=True, type="primary"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just, "categoria_dfc": cat_dfc}
            if st.session_state.edit_id: supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
            else: supabase.table("lancamentos").insert(payload).execute()
            st.session_state.edit_id = None; st.session_state.form_count += 1; st.rerun()

# --- CSS VISUAL ERP ---
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .razonete-card { background: white; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 1.5rem; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .razonete-header { background: #0f172a; color: white; padding: 8px; font-weight: 600; text-align: center; font-size: 0.8rem; }
    .total-footer { background: #f8fafc; padding: 8px; text-align: center; font-weight: bold; font-size: 0.8rem; border-top: 1px solid #e2e8f0; }
    .group-label { background: #e2e8f0; color: #1e293b; padding: 5px 12px; border-radius: 4px; font-weight: 700; margin-top: 1rem; font-size: 0.7rem; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
st.markdown("<h2 style='color: #0f172a; font-weight: 700;'>Dashboard Contábil</h2>", unsafe_allow_html=True)
nav = st.columns(5)
btns = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo (DFC)", "⚙️ Gestão"]
for i, b_name in enumerate(btns):
    if nav[i].button(b_name, use_container_width=True): st.session_state.menu_opcao = b_name
st.divider()

if not df.empty:
    opcao = st.session_state.menu_opcao
    
    if opcao == "📊 Razonetes":
        for n_label in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df[df['natureza'] == n_label]
            if not df_g.empty:
                st.markdown(f"<div class='group-label'>{n_label}</div>", unsafe_allow_html=True)
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
            d_s, c_s = temp[temp['tipo'] == 'Débito']['valor'].sum(), temp[temp['tipo'] == 'Crédito']['valor'].sum()
            s = d_s - c_s
            bal_data.append({"CONTA": c_n, "DEBITO": d_s, "CREDITO": c_s, "SALDO DEVEDOR": s if s > 0 else 0, "SALDO CREDOR": abs(s) if s < 0 else 0})
        df_bal = pd.DataFrame(bal_data)
        st.table(df_bal.style.format({c: "{:,.2f}" for c in ["DEBITO", "CREDITO", "SALDO DEVEDOR", "SALDO CREDOR"]}))
        pdf_bytes = gerar_pdf_bytes(df_bal, "BALANCETE DE VERIFICACAO")
        st.download_button("📥 Baixar Relatório PDF", data=pdf_bytes, file_name="balancete.pdf")

    elif opcao == "📈 DRE":
        st.subheader("Demonstração do Resultado (DRE)")
        rec = df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum()
        des = df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros'].groupby('descricao')['valor'].sum()
        st.success(f"**LUCRO LÍQUIDO: R$ {rec.sum() - des.sum() - enc.sum():,.2f}**")
        with st.expander("(+) RECEITA BRUTA"): st.write(rec)
        with st.expander("(-) DESPESAS OPERACIONAIS"): st.write(des)
        with st.expander("(-) RESULTADO FINANCEIRO"): st.write(enc)

    elif opcao == "💸 Fluxo (DFC)":
        st.subheader("💸 DFC - Demonstração do Fluxo de Caixa")
        st.info("Pergunta central: 'Temos dinheiro para pagar os boletos hoje?' (Entradas e Saídas Reais)")
        
        df_f = df.copy()
        # Classificação de entradas e saídas reais de dinheiro
        df_f['ENTRADA'] = df_f.apply(lambda x: x['valor'] if x['tipo'] == 'Débito' else 0, axis=1)
        df_f['SAÍDA'] = df_f.apply(lambda x: x['valor'] if x['tipo'] == 'Crédito' else 0, axis=1)
        df_f['SALDO_LIQUIDO'] = df_f['ENTRADA'] - df_f['SAÍDA']

        # Agrupamento por Categoria DFC
        df_cat = df_f.groupby('categoria_dfc')[['ENTRADA', 'SAÍDA', 'SALDO_LIQUIDO']].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Fluxo Operacional", f"R$ {df_cat.loc['Operacional', 'SALDO_LIQUIDO'] if 'Operacional' in df_cat.index else 0:,.2f}")
