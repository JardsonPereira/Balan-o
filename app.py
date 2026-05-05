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

    def calc_valor_pdf(nat, tipo_dev=True):
        sub = df_periodo[df_periodo['natureza'] == nat]
        d, c = sub[sub['tipo'] == 'Débito']['valor'].sum(), sub[sub['tipo'] == 'Crédito']['valor'].sum()
        return (d - c) if tipo_dev else (c - d)

    rec = calc_valor_pdf('Receita', False)
    desp = calc_valor_pdf('Despesa', True)
    enc = calc_valor_pdf('Encargos Financeiros', True)
    ebitda = rec - desp
    lucro = ebitda - enc

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "1. Demonstracao do Resultado (DRE)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(100, 7, f"Receita Bruta: R$ {rec:,.2f}", ln=True)
    pdf.cell(100, 7, f"Despesas Operacionais: R$ {desp:,.2f}", ln=True)
    pdf.cell(100, 7, f"EBITDA: R$ {ebitda:,.2f}", ln=True)
    pdf.cell(100, 7, f"Encargos Financeiros: R$ {enc:,.2f}", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 7, f"LUCRO LIQUIDO: R$ {lucro:,.2f}", ln=True)
    pdf.ln(10)

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
        reg = df[df['id'] == st.session_state.edit_id].iloc[0]
        if st.button("Cancelar Edição"):
            st.session_state.edit_id = None
            st.rerun()
    else:
        st.header("➕ Novo Lançamento")
        reg = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago", "data_lancamento": datetime.now().date()}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        idx_conta = opcoes_conta.index(reg['descricao']) if reg['descricao'] in contas_existentes else 0
        
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        desc_input = st.text_input("Nome da Conta", value=reg['descricao']).upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel
        data_f = st.date_input("Data", value=reg['data_lancamento'])
        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(reg['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if reg['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(reg['valor']))
        opcoes_status = ["Pago", "Entrada", "Pendente", "Investimento", "Transferência Interna"]
        status_pag = st.selectbox("Status Financeiro", opcoes_status, index=opcoes_status.index(reg['status']) if reg['status'] in opcoes_status else 0)
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
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; border-radius: 12px 12px 0 0; }
    .conta-rodape { padding: 8px; background: #f8fafc; text-align: center; font-weight: 700; border-top: 1px solid #e2e8f0; border-radius: 0 0 12px 12px; }
    .valor-deb { color: #059669; font-size: 0.8rem; padding: 2px 10px; font-weight: 600; }
    .valor-cre { color: #dc2626; font-size: 0.8rem; text-align: right; padding: 2px 10px; font-weight: 600; }
    .metric-card { background: #f8fafc; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>""", unsafe_allow_html=True)

st.title("📑 Sistema Contábil Digital")

# --- NAVEGAÇÃO ---
col_nav = st.columns(5)
opcoes_menu = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes_menu):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()
f1, f2, f3 = st.columns([2, 2, 1])
with f1: data_ini = st.date_input("Início do Período", value=datetime.now().date().replace(day=1))
with f2: data_fim = st.date_input("Fim do Período", value=datetime.now().date())

df_periodo = df[(df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)] if not df.empty else pd.DataFrame()

# --- CONTEÚDO DAS ABAS ---
if df_periodo.empty and st.session_state.menu_opcao != "⚙️ Gestão":
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
                        st.markdown(f'<div class="conta-card"><div class="conta-titulo">{conta}</div>', unsafe_allow_html=True)
                        c_deb, c_cre = st.columns(2)
                        with c_deb:
                            for _, r in df_c[df_c['tipo']=='Débito'].iterrows(): st.markdown(f'<div class="valor-deb">D: {r["valor"]:,.2f}</div>', unsafe_allow_html=True)
                        with c_cre:
                            for _, r in df_c[df_c['tipo']=='Crédito'].iterrows(): st.markdown(f'<div class="valor-cre">C: {r["valor"]:,.2f}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>', unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("🧾 Balancete de Verificação")
        bal_data = []
        for conta in sorted(df_periodo['descricao'].unique()):
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c, "SD": d-c if d>c else 0, "SC": c-d if c>d else 0})
        df_bal = pd.DataFrame(bal_data)
        st.table(df_bal.style.format(precision=2))

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 Demonstração do Resultado (DRE)")
        rec = df_periodo[(df_periodo['natureza'] == 'Receita') & (df_periodo['tipo'] == 'Crédito')]['valor'].sum() - df_periodo[(df_periodo['natureza'] == 'Receita') & (df_periodo['tipo'] == 'Débito')]['valor'].sum()
        desp = df_periodo[(df_periodo['natureza'] == 'Despesa') & (df_periodo['tipo'] == 'Débito')]['valor'].sum() - df_periodo[(df_periodo['natureza'] == 'Despesa') & (df_periodo['tipo'] == 'Crédito')]['valor'].sum()
        ebitda = rec - desp
        st.metric("Resultado Líquido", f"R$ {ebitda:,.2f}")

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Fluxo de Caixa Acumulado")
        
        # --- LÓGICA DE SALDOS ACUMULADOS ---
        def calc_acumulado(limite_data, natureza=None):
            if df.empty: return 0.0
            sub = df[df['data_lancamento'] <= limite_data]
            if natureza: sub = sub[sub['natureza'] == natureza]
            
            if natureza == "Ativo" or natureza is None:
                entradas = sub[sub['status'] == "Entrada"]['valor'].sum()
                saidas = sub[sub['status'] == "Pago"]['valor'].sum()
                return entradas - saidas
            
            if natureza == "Passivo":
                c = sub[sub['tipo'] == "Crédito"]['valor'].sum()
                d = sub[sub['tipo'] == "Débito"]['valor'].sum()
                return c - d
            return 0.0

        si = calc_acumulado(data_ini - timedelta(days=1))
        sf = calc_acumulado(data_fim)
        pa_total = calc_acumulado(data_fim, "Passivo")

        # --- LOGICA DE GRUPOS COM CAPTURA MELHORADA ---
        def filtrar_por_desc(natureza, keywords, limite):
            if df.empty: return 0.0
            sub = df[(df['data_lancamento'] <= limite) & (df['natureza'] == natureza)]
            mask = sub['descricao'].str.contains('|'.join(keywords), case=False, na=False)
            df_filtrado = sub[mask]
            if natureza == 'Ativo':
                return df_filtrado[df_filtrado['tipo'] == 'Débito']['valor'].sum() - df_filtrado[df_filtrado['tipo'] == 'Crédito']['valor'].sum()
            else:
                return df_filtrado[df_filtrado['tipo'] == 'Crédito']['valor'].sum() - df_filtrado[df_filtrado['tipo'] == 'Débito']['valor'].sum()

        # ATIVO
        disponivel = filtrar_por_desc('Ativo', ['CAIXA', 'BANCO', 'NUBANK', 'POUPANCA', 'CORRENTE', 'DINHEIRO'], data_fim)
        estoques = filtrar_por_desc('Ativo', ['ESTOQUE', 'MERCADORIA', 'PRODUTO'], data_fim)
        recebeis = filtrar_por_desc('Ativo', ['CLIENTES', 'RECEBER', 'VENDAS A PRAZO'], data_fim)
        outros_at = (calc_acumulado(data_fim, "Ativo")) - (disponivel + estoques + recebeis)

        # PASSIVO (DÍVIDAS) - Adicionado "Outras Obrigações" para capturar os 49k se não tiver nome específico
        fornecedores = filtrar_por_desc('Passivo', ['FORNECEDOR', 'BOLETO', 'COMPRA', 'DUPLICATA'], data_fim)
        emprestimos = filtrar_por_desc('Passivo', ['EMPRESTIMO', 'FINANCIAMENTO', 'BANCO', 'EMPREST'], data_fim)
        tributos = filtrar_por_desc('Passivo', ['IMPOSTO', 'TRIBUTO', 'DAS', 'ICMS', 'FGTS', 'SIMPLES'], data_fim)
        outras_dividas = pa_total - (fornecedores + emprestimos + tributos)

        # --- EXIBIÇÃO ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Saldo Inicial", f"R$ {si:,.2f}")
        m2.metric("Saldo Final Caixa", f"R$ {sf:,.2f}")
        m3.metric("Passivo Total", f"R$ {pa_total:,.2f}")

        st.divider()
        c_at, c_pa = st.columns(2)
        with c_at:
            st.markdown("#### 💰 Detalhe do Ativo")
            df_at_vis = pd.DataFrame([
                {"Item": "💵 Disponível", "Valor": disponivel},
                {"Item": "📦 Estoques", "Valor": estoques},
                {"Item": "⏳ Recebíveis", "Valor": recebeis},
                {"Item": "🌀 Outros Ativos", "Valor": outros_at},
                {"Item": "🏛️ TOTAL ATIVO", "Valor": disponivel + estoques + recebeis + outros_at}
            ])
            st.table(df_at_vis.style.format({"Valor": "R$ {:,.2f}"}))
        
        with c_pa:
            st.markdown("#### 💸 Detalhe do Passivo (Dívidas)")
            df_pa_vis = pd.DataFrame([
                {"Item": "🤝 Fornecedores", "Valor": fornecedores},
                {"Item": "🏦 Empréstimos", "Valor": emprestimos},
                {"Item": "⚖️ Tributos", "Valor": tributos},
                {"Item": "📋 Outras Obrigações", "Valor": outras_dividas},
                {"Item": "📉 TOTAL PASSIVO", "Valor": pa_total}
            ])
            st.table(df_pa_vis.style.format({"Valor": "R$ {:,.2f}"}))

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        if st.button("🚨 Resetar Tudo"):
            supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
            st.cache_data.clear()
            st.rerun()
