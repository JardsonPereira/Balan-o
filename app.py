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

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "2. Balancete Patrimonial", ln=True)
    
    def render_secao_pdf(titulo, nat, tipo_dev):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(190, 8, titulo, ln=True)
        pdf.set_font("Helvetica", "", 9)
        total = 0
        contas = sorted(df_periodo[df_periodo['natureza'] == nat]['descricao'].unique())
        for conta in contas:
            df_c = df_periodo[(df_periodo['natureza'] == nat) & (df_periodo['descricao'] == conta)]
            saldo = (df_c[df_c['tipo']=='Débito']['valor'].sum() - df_c[df_c['tipo']=='Crédito']['valor'].sum()) if tipo_dev else (df_c[df_c['tipo']=='Crédito']['valor'].sum() - df_c[df_c['tipo']=='Débito']['valor'].sum())
            pdf.cell(140, 6, f"  {conta}", border="B")
            pdf.cell(50, 6, f"R$ {saldo:,.2f}", border="B", ln=True, align="R")
            total += saldo
        return total

    t_at = render_secao_pdf("ATIVO", "Ativo", True)
    t_pa = render_secao_pdf("PASSIVO", "Passivo", False)
    t_pl = render_secao_pdf("PATRIMONIO LIQUIDO", "Patrimônio Líquido", False)
    
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(140, 6, "  (+) Resultado do Periodo", border="B")
    pdf.cell(50, 6, f"R$ {lucro:,.2f}", border="B", ln=True, align="R")
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(140, 8, "TOTAL ATIVO")
    pdf.cell(50, 8, f"R$ {t_at:,.2f}", ln=True, align="R")
    pdf.cell(140, 8, "TOTAL PASSIVO + PL + RESULTADO")
    pdf.cell(50, 8, f"R$ {t_pa + t_pl + lucro:,.2f}", ln=True, align="R")
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
    .liquidez-label { font-size: 0.85rem; font-weight: bold; color: #64748b; margin-bottom: 5px; }
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

with f3:
    if not df_periodo.empty:
        try:
            pdf_bytes = gerar_pdf(df_periodo, data_ini, data_fim, st.session_state.user.email)
            st.download_button(label="📥 Baixar PDF", data=pdf_bytes, file_name=f"relatorio_completo.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e: st.error(f"Erro PDF: {e}")

# --- CONTEÚDO DAS ABAS ---
if df_periodo.empty and st.session_state.menu_opcao != "⚙️ Gestão":
    st.info("Nenhum lançamento encontrado para o período selecionado.")
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
                            for _, r in df_c[df_c['tipo']=='Débito'].iterrows():
                                st.markdown(f'<div class="valor-deb">D: {r["valor"]:,.2f}</div><div class="just-box">{r["justificativa"]}</div>', unsafe_allow_html=True)
                        with c_cre:
                            for _, r in df_c[df_c['tipo']=='Crédito'].iterrows():
                                st.markdown(f'<div class="valor-cre">C: {r["valor"]:,.2f}</div><div class="just-box">{r["justificativa"]}</div>', unsafe_allow_html=True)
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
        
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("Soma Débitos", f"R$ {df_bal['Débito'].sum():,.2f}")
        tc2.metric("Soma Créditos", f"R$ {df_bal['Crédito'].sum():,.2f}")
        tc3.metric("Total Devedor", f"R$ {df_bal['SD'].sum():,.2f}")
        tc4.metric("Total Credor", f"R$ {df_bal['SC'].sum():,.2f}")

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 Demonstração do Resultado (DRE)")
        rec = df_periodo[(df_periodo['natureza'] == 'Receita') & (df_periodo['tipo'] == 'Crédito')]['valor'].sum() - df_periodo[(df_periodo['natureza'] == 'Receita') & (df_periodo['tipo'] == 'Débito')]['valor'].sum()
        desp = df_periodo[(df_periodo['natureza'] == 'Despesa') & (df_periodo['tipo'] == 'Débito')]['valor'].sum() - df_periodo[(df_periodo['natureza'] == 'Despesa') & (df_periodo['tipo'] == 'Crédito')]['valor'].sum()
        enc = df_periodo[(df_periodo['natureza'] == 'Encargos Financeiros') & (df_periodo['tipo'] == 'Débito')]['valor'].sum()
        ebitda = rec - desp
        st.metric("Receita Bruta", f"R$ {rec:,.2f}")
        st.metric("Despesas Operacionais", f"R$ {desp:,.2f}")
        st.info(f"⚡ EBITDA: R$ {ebitda:,.2f}")
        st.metric("Resultado Líquido", f"R$ {ebitda - enc:,.2f}")

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Fluxo e Grau de Liquidez (Acumulado)")
        
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

        # --- LOGICA DE GRUPOS (ATIVO E PASSIVO) ---
        def saldo_grupo_acumulado(natureza, keywords, limite):
            if df.empty: return 0.0
            sub = df[(df['data_lancamento'] <= limite) & (df['natureza'] == natureza)]
            mask = sub['descricao'].str.contains('|'.join(keywords), case=False, na=False)
            final = sub[mask]
            if natureza == 'Ativo':
                return final[final['tipo'] == 'Débito']['valor'].sum() - final[final['tipo'] == 'Crédito']['valor'].sum()
            else:
                return final[final['tipo'] == 'Crédito']['valor'].sum() - final[final['tipo'] == 'Débito']['valor'].sum()

        # ATIVO
        disponivel = saldo_grupo_acumulado('Ativo', ['CAIXA', 'BANCO', 'NUBANK', 'POUPANCA'], data_fim)
        estoques = saldo_grupo_acumulado('Ativo', ['ESTOQUE', 'MERCADORIA'], data_fim)
        recebeis = saldo_grupo_acumulado('Ativo', ['CLIENTES', 'RECEBER'], data_fim)
        
        # PASSIVO (DÍVIDAS)
        fornecedores = saldo_grupo_acumulado('Passivo', ['FORNECEDOR', 'BOLETO', 'COMPRA'], data_fim)
        emprestimos = saldo_grupo_acumulado('Passivo', ['EMPRESTIMO', 'FINANCIAMENTO', 'JUROS'], data_fim)
        tributos = saldo_grupo_acumulado('Passivo', ['IMPOSTO', 'TRIBUTO', 'DAS', 'ICMS', 'FGTS'], data_fim)
        
        at_circulante = disponivel + estoques + recebeis
        pa_circulante = calc_acumulado(data_fim, "Passivo")
        
        l_corrente = at_circulante / pa_circulante if pa_circulante > 0 else at_circulante

        # --- MÉTRICAS ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Saldo Inicial (Transportado)", f"R$ {si:,.2f}")
        m2.metric("Saldo Final de Caixa", f"R$ {sf:,.2f}")
        m3.metric("Variação do Período", f"R$ {sf-si:,.2f}", delta=f"{sf-si:,.2f}")

        st.write("---")
        st.markdown("#### 📏 Índices de Liquidez Acumulada")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='metric-card'><p class='liquidez-label'>Liquidez Corrente</p><h3>{l_corrente:.2f}</h3><small>Ativo Circ. / Passivo Circ.</small></div>", unsafe_allow_html=True)
        with c2:
            l_seca = (at_circulante - estoques) / pa_circulante if pa_circulante > 0 else (at_circulante - estoques)
            st.markdown(f"<div class='metric-card' style='border-left-color: #f59e0b'><p class='liquidez-label'>Liquidez Seca</p><h3>{l_seca:.2f}</h3><small>Excluindo Estoques</small></div>", unsafe_allow_html=True)
        with c3:
            l_imediata = disponivel / pa_circulante if pa_circulante > 0 else disponivel
            st.markdown(f"<div class='metric-card' style='border-left-color: #10b981'><p class='liquidez-label'>Liquidez Imediata</p><h3>{l_imediata:.2f}</h3><small>Disponível / Dívida Total</small></div>", unsafe_allow_html=True)

        st.write("---")
        col_at, col_pa = st.columns(2)
        with col_at:
            st.markdown("#### 💰 Detalhe do Ativo (Conversíveis)")
            dados_at = [
                {"Item": "💵 Disponibilidade Imediata", "Valor": disponivel},
                {"Item": "📦 Estoques (Mercadorias)", "Valor": estoques},
                {"Item": "⏳ Recebíveis (Futuros)", "Valor": recebeis},
                {"Item": "🏛️ Total Ativo Circulante", "Valor": at_circulante}
            ]
            st.table(pd.DataFrame(dados_at).style.format({"Valor": "R$ {:,.2f}"}))
        
        with col_pa:
            st.markdown("#### 💸 Detalhe do Passivo (Dívidas)")
            dados_pa = [
                {"Item": "🤝 Fornecedores / Boletos", "Valor": fornecedores},
                {"Item": "🏦 Empréstimos / Bancos", "Valor": emprestimos},
                {"Item": "⚖️ Tributos / Impostos", "Valor": tributos},
                {"Item": "📉 Total Passivo Acumulado", "Valor": pa_circulante}
            ]
            st.table(pd.DataFrame(dados_pa).style.format({"Valor": "R$ {:,.2f}"}))

        st.write("---")
        st.markdown("#### 📋 Histórico de Movimentações do Período")
        st.dataframe(df_periodo[df_periodo['status'].isin(["Entrada", "Pago"])][['data_lancamento', 'descricao', 'valor', 'status', 'justificativa']], use_container_width=True)

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        col_res, _ = st.columns([1, 4])
        if col_res.button("🚨 Resetar Todos Lançamentos", type="primary", use_container_width=True):
            try:
                supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
                st.cache_data.clear()
                st.success("Todos os lançamentos foram excluídos.")
                st.rerun()
            except Exception as e: st.error(f"Erro: {e}")
        
        st.divider()
        if not df.empty:
            for _, row in df.sort_values('data_lancamento', ascending=False).iterrows():
                with st.expander(f"{row['data_lancamento']} - {row['descricao']} - R$ {row['valor']} ({row['status']})"):
                    st.write(f"Justificativa: {row['justificativa']}")
                    c_edit, c_del = st.columns(2)
                    if c_edit.button("✏️ Editar", key=f"ed_{row['id']}"):
                        st.session_state.edit_id = row['id']
                        st.rerun()
                    if c_del.button("🗑️ Excluir", key=f"del_{row['id']}"):
                        supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.rerun()
