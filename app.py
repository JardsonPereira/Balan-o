import streamlit as st
import pandas as pd
from fpdf import FPDF
from supabase import create_client, Client
from datetime import datetime, date

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
    return bytes(pdf.output()) if isinstance(pdf.output(), bytearray) else pdf.output()

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

if not df.empty:
    if 'categoria_dfc' not in df.columns: df['categoria_dfc'] = 'Atividade Operacional'
    if 'data_lancamento' not in df.columns: df['data_lancamento'] = datetime.today().strftime('%Y-%m-%d')
    df['data_lancamento'] = pd.to_datetime(df['data_lancamento']).dt.date

# --- SIDEBAR OPERACIONAL ---
with st.sidebar:
    st.markdown(f"### 🏢 Enterprise Panel")
    if st.button("Encerrar Sessão", use_container_width=True): st.session_state.user = None; st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df.empty:
        st.subheader("📝 Editar Registro")
        items = df[df['id'] == st.session_state.edit_id]
        item_edit = items.iloc[0].to_dict() if not items.empty else {}
    else:
        st.subheader("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "categoria_dfc": "Atividade Operacional", "data_lancamento": date.today()}

    with st.form(key=f"f_{st.session_state.form_count}", clear_on_submit=True):
        data_sel = st.date_input("Data do Fato", value=item_edit.get('data_lancamento', date.today()))
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        sel = st.selectbox("Conta", ["(NOVA)"] + contas_existentes)
        desc = st.text_input("Nome da Conta", value=item_edit.get('descricao', "")).upper() if sel == "(NOVA)" else sel
        nat = st.selectbox("Grupo", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit.get('natureza', 'Ativo')))
        cat_dfc_list = ["Atividade Operacional", "Atividade de Investimento", "Atividade de Financiamento", "N/A (Não Financeiro)"]
        cat_dfc = st.selectbox("DFC", cat_dfc_list, index=cat_dfc_list.index(item_edit.get('categoria_dfc', 'Atividade Operacional')))
        tipo = st.radio("Tipo", ["Débito (Entrada)", "Crédito (Saída)"], horizontal=True, index=0 if item_edit.get('tipo') == 'Débito' else 1)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit.get('valor', 0.0)))
        just = st.text_input("Histórico", value=item_edit.get('justificativa', ""))
        
        if st.form_submit_button("Efetivar Registro", use_container_width=True, type="primary"):
            tipo_db = "Débito" if "Débito" in tipo else "Crédito"
            payload = {
                "user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo_db, 
                "valor": valor, "justificativa": just, "categoria_dfc": cat_dfc,
                "data_lancamento": data_sel.strftime('%Y-%m-%d')
            }
            try:
                if st.session_state.edit_id:
                    supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                    st.session_state.edit_id = None
                else:
                    supabase.table("lancamentos").insert(payload).execute()
                st.session_state.form_count += 1
                st.rerun()
            except Exception:
                st.error("Erro na comunicação com o banco de dados.")

# --- CSS ---
st.markdown("<style>.stApp { background-color: #f8fafc; } .dfc-resumo { background: #f1f5f9; padding: 15px; border-radius: 10px; border-left: 5px solid #1e3a8a; } .group-label { background: #e2e8f0; color: #1e293b; padding: 5px 12px; border-radius: 4px; font-weight: 700; margin-top: 1rem; font-size: 0.7rem; text-transform: uppercase; }</style>", unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
st.markdown("<h2 style='color: #0f172a; font-weight: 700;'>Dashboard Contábil</h2>", unsafe_allow_html=True)
nav = st.columns(5)
btns = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 DFC Real", "⚙️ Gestão"]
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
                        with st.container(border=True):
                            st.write(f"**{c_nome}**")
                            st.write(f"Saldo: R$ {abs(saldo):,.2f} ({'D' if saldo>=0 else 'C'})")

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
        st.download_button("📥 PDF", data=gerar_pdf_bytes(df_bal, "BALANCETE"), file_name="balancete.pdf")

    elif opcao == "📈 DRE":
        st.subheader("DRE (Competência)")
        rec = df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum()
        des = df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum()
        st.success(f"**LUCRO LÍQUIDO: R$ {rec.sum() - des.sum():,.2f}**")
        st.write("Receitas:", rec)
        st.write("Despesas:", des)

    elif opcao == "💸 DFC Real":
        st.subheader("💸 DFC - Fluxo por Período")
        c1, c2 = st.columns(2)
        data_i = c1.date_input("Início", value=date(date.today().year, date.today().month, 1))
        data_f = c2.date_input("Fim", value=date.today())
        
        df_f = df[(df['categoria_dfc'] != "N/A (Não Financeiro)") & 
                  (df['data_lancamento'] >= data_i) & 
                  (df['data_lancamento'] <= data_f)].copy()
        
        if not df_f.empty:
            df_f = df_f.sort_values(by='data_lancamento')
            ent, sai = df_f[df_f['tipo']=='Débito']['valor'].sum(), df_f[df_f['tipo']=='Crédito']['valor'].sum()
            saldo_ant = st.number_input("Saldo Anterior", min_value=0.0, value=0.0)
            
            resumo_html = f"<div class='dfc-resumo'>Saldo Inicial: R$ {saldo_ant:,.2f}<br>(+) Entradas: R$ {ent:,.2f}<br>(-) Saídas: R$ {sai:,.2f}<br><b>(=) SALDO FINAL: R$ {saldo_ant + ent - sai:,.2f}</b></div>"
            st.markdown(resumo_html, unsafe_allow_html=True)
            
            st.divider()
            df_cat = df_f.groupby('categoria_dfc')[['valor']].sum()
            cols = st.columns(3)
            cats = ["Atividade Operacional", "Atividade de Investimento", "Atividade de Financiamento"]
            for i, cat in enumerate(cats):
                val = df_cat.loc[cat, 'valor'] if cat in df_cat.index else 0
                cols[i].metric(cat.replace("Atividade de ", ""), f"R$ {val:,.2f}")

            st.write("#### Extrato do Período")
            st.dataframe(df_f[['data_lancamento', 'descricao', 'tipo', 'valor', 'justificativa']], use_container_width=True)
        else:
            st.warning("Nenhum dado financeiro no período.")

    elif opcao == "⚙️ Gestão":
        st.subheader("Manutenção de Registros")
        
        # --- NOVO: OPÇÃO DE RESETAR TUDO ---
        with st.expander("🚨 ZONA DE PERIGO: Resetar Lançamentos"):
            st.warning("Esta ação excluirá permanentemente TODOS os seus lançamentos desta conta.")
            confirm = st.text_input("Para confirmar, digite 'RESETAR' abaixo:")
            if st.button("EXCLUIR TUDO", type="primary"):
                if confirm == "RESETAR":
                    try:
                        supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
                        st.success("Todos os registros foram apagados com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao resetar: {e}")
                else:
                    st.error("Palavra de confirmação incorreta.")
        
        st.divider()
        
        for _, r in df.iterrows():
            with st.container(border=True):
                c_inf, c_btn = st.columns([4, 1])
                c_inf.write(f"**{r['data_lancamento'].strftime('%d/%m/%Y')} - {r['descricao']}** | R$ {r['valor']:,.2f}")
                if c_btn.button("✏️", key=f"e_{r['id']}"): 
                    st.session_state.edit_id = r['id']
                    st.rerun()
                if c_btn.button("🗑️", key=f"d_{r['id']}"): 
                    supabase.table("lancamentos").delete().eq("id", r['id']).execute()
                    st.rerun()
else:
    st.info("Sistema vazio.")
