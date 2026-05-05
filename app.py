import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
from fpdf import FPDF
import io

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
if 'confirm_reset' not in st.session_state: st.session_state.confirm_reset = False

# --- FUNÇÃO PARA GERAR PDF ---
def gerar_pdf(df_periodo, data_ini, data_fim, user_email):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    
    pdf.cell(190, 10, "Relatorio Contabil Consolidado", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(190, 10, f"Periodo: {data_ini} ate {data_fim} | Usuario: {user_email}", ln=True, align="C")
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)

    # 1. DRE
    def calc_valor_pdf(natureza, tipo_devedor=True):
        sub = df_periodo[df_periodo['natureza'] == natureza]
        d = sub[sub['tipo'] == 'Débito']['valor'].sum()
        c = sub[sub['tipo'] == 'Crédito']['valor'].sum()
        return (d - c) if tipo_devedor else (c - d)

    receitas = calc_valor_pdf('Receita', False)
    despesas = calc_valor_pdf('Despesa', True)
    encargos = calc_valor_pdf('Encargos Financeiros', True)
    ebitda = receitas - despesas
    lucro_periodo = ebitda - encargos

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "1. Demonstracao do Resultado (DRE)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(100, 7, f"Receita Bruta: R$ {receitas:,.2f}", ln=True)
    pdf.cell(100, 7, f"Despesas Operacionais: R$ {despesas:,.2f}", ln=True)
    pdf.cell(100, 7, f"EBITDA: R$ {ebitda:,.2f}", ln=True)
    pdf.cell(100, 7, f"Lucro Liquido: R$ {lucro_periodo:,.2f}", ln=True)
    pdf.ln(5)

    # 2. Balancete Patrimonial Simplificado
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "2. Balancete Patrimonial", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    
    total_ativo = calc_valor_pdf('Ativo', True)
    total_passivo = calc_valor_pdf('Passivo', False)
    total_pl = calc_valor_pdf('Patrimônio Líquido', False)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(140, 7, "Total Ativo", border="B")
    pdf.cell(50, 7, f"R$ {total_ativo:,.2f}", border="B", ln=True, align="R")
    pdf.cell(140, 7, "Total Passivo", border="B")
    pdf.cell(50, 7, f"R$ {total_passivo:,.2f}", border="B", ln=True, align="R")
    pdf.cell(140, 7, "Patrimonio Liquido (Base)", border="B")
    pdf.cell(50, 7, f"R$ {total_pl:,.2f}", border="B", ln=True, align="R")
    pdf.cell(140, 7, "Resultado do Periodo (Lucro/Prejuizo)", border="B")
    pdf.cell(50, 7, f"R$ {lucro_periodo:,.2f}", border="B", ln=True, align="R")
    pdf.ln(5)

    # 4. Listagem Detalhada
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "3. Listagem Detalhada de Lancamentos", ln=True)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(20, 7, "Data", 1)
    pdf.cell(40, 7, "Conta", 1)
    pdf.cell(25, 7, "Grupo", 1)
    pdf.cell(20, 7, "Valor", 1)
    pdf.cell(25, 7, "Status", 1)
    pdf.cell(60, 7, "Justificativa", 1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 6)
    for _, row in df_periodo.sort_values('data_lancamento').iterrows():
        pdf.cell(20, 6, str(row['data_lancamento']), 1)
        pdf.cell(40, 6, str(row['descricao'])[:30].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(25, 6, str(row['natureza']).encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(20, 6, f"{row['valor']:,.2f}", 1)
        pdf.cell(25, 6, str(row['status']), 1)
        pdf.cell(60, 6, str(row['justificativa'])[:45].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.ln()

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
            if 'status' not in temp_df.columns: temp_df['status'] = 'Pago'
            if 'justificativa' not in temp_df.columns: temp_df['justificativa'] = ''
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
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago", "data_lancamento": datetime.now().date()}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        idx_conta = opcoes_conta.index(item_edit['descricao']) if st.session_state.edit_id and item_edit['descricao'] in contas_existentes else 0
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        desc = st.text_input("Nome da Nova Conta", value="").upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel
        data_f = st.date_input("Data do Lançamento", value=item_edit.get('data_lancamento', datetime.now().date()))
        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        opcoes_status = ["Pago", "Entrada", "Pendente", "Investimento", "Transferência Interna"]
        status_pag = st.selectbox("Status Financeiro", opcoes_status, index=opcoes_status.index(item_edit['status']) if item_edit['status'] in opcoes_status else 0)
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar Lançamento"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just, "status": status_pag, "data_lancamento": str(data_f)}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.cache_data.clear()
            st.session_state.form_count += 1
            st.rerun()

# --- LÓGICA DE NAVEGAÇÃO E PERÍODO ---
col_nav = st.columns(5)
opcoes_menu = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes_menu):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()
f1, f2, f3 = st.columns([2, 2, 1])
with f1: data_ini = st.date_input("Início do Período", value=datetime.now().date().replace(day=1))
with f2: data_fim = st.date_input("Fim do Período", value=datetime.now().date())

df_periodo = df[(df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)] if not df.empty else df

with f3:
    if not df_periodo.empty:
        try:
            pdf_bytes = gerar_pdf(df_periodo, data_ini, data_fim, st.session_state.user.email)
            st.download_button(label="📥 Baixar PDF", data=pdf_bytes, file_name=f"relatorio.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e: st.error(f"Erro PDF: {e}")

# --- ABAS ---
if df.empty and st.session_state.menu_opcao != "⚙️ Gestão":
    st.info("Nenhum lançamento encontrado.")
else:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for grupo in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df_periodo[df_periodo['natureza'] == grupo]
            if not df_g.empty:
                st.markdown(f"### {grupo}")
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    df_c = df_g[df_g['descricao'] == conta]
                    v_d, v_c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                    saldo = (v_d - v_c) if grupo in ["Ativo", "Despesa", "Encargos Financeiros"] else (v_c - v_d)
                    with cols[i % 3]:
                        st.markdown(f"**{conta}**  \nSaldo: R$ {saldo:,.2f}")

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("🧾 Balancete de Verificação")
        bal_data = []
        for conta in sorted(df_periodo['descricao'].unique()):
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "D": d, "C": c, "SD": d-c if d>c else 0, "SC": c-d if c>d else 0})
        st.table(pd.DataFrame(bal_data))

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 DRE")
        def tot(n, t): 
            sub = df_periodo[df_periodo['natureza'] == n]
            return sub[sub['tipo'] == t]['valor'].sum() - sub[sub['tipo'] != t]['valor'].sum()
        rec = df_periodo[df_periodo['natureza'] == 'Receita'][df_periodo['tipo'] == 'Crédito']['valor'].sum()
        desp = df_periodo[df_periodo['natureza'] == 'Despesa'][df_periodo['tipo'] == 'Débito']['valor'].sum()
        ebitda = rec - desp
        st.write(f"Receita: R$ {rec:,.2f}")
        st.write(f"Despesa: R$ {desp:,.2f}")
        st.info(f"EBITDA: R$ {ebitda:,.2f}")

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Fluxo de Caixa (Saldo Acumulado)")
        
        def calc_caixa(limite):
            # LÓGICA DE CARREGAMENTO: Filtra TUDO até a data limite
            sub = df[df['data_lancamento'] <= limite]
            return sub[sub['status'] == "Entrada"]['valor'].sum() - sub[sub['status'] == "Pago"]['valor'].sum()

        # Saldo Inicial: Tudo ANTES do período selecionado
        si = calc_caixa(data_ini - timedelta(days=1))
        # Saldo Final: Tudo até o FIM do período selecionado
        sf = calc_caixa(data_fim)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Saldo Inicial (Carregado)", f"R$ {si:,.2f}")
        m2.metric("Variação no Mês", f"R$ {sf-si:,.2f}", delta=f"{sf-si:,.2f}")
        m3.metric("Saldo Final", f"R$ {sf:,.2f}")
        
        df_f = df_periodo[df_periodo['status'].isin(["Entrada", "Pago"])]
        st.dataframe(df_f[['data_lancamento', 'descricao', 'valor', 'status', 'justificativa']], use_container_width=True)

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        if st.button("🚨 Reset Total"):
            supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
            st.cache_data.clear()
            st.rerun()
        for _, row in df.sort_values('data_lancamento', ascending=False).iterrows():
            st.write(f"{row['data_lancamento']} - {row['descricao']} - R$ {row['valor']} ({row['status']})")
            if st.button("🗑️", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.cache_data.clear()
                st.rerun()
