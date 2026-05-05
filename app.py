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

# --- FUNÇÃO PARA GERAR PDF (CORRIGIDA) ---
def gerar_pdf(df_periodo, data_ini, data_fim, user_email):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    
    # Cabeçalho
    pdf.cell(190, 10, "Relatorio Contabil Consolidado", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(190, 10, f"Periodo: {data_ini} ate {data_fim} | Usuario: {user_email}", ln=True, align="C")
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)

    # 1. Resumo DRE
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "1. Demonstracao do Resultado (DRE)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    
    def calc_dre_pdf(nat, tipo_base):
        sub = df_periodo[df_periodo['natureza'] == nat]
        if tipo_base == 'Crédito':
            return sub[sub['tipo'] == 'Crédito']['valor'].sum() - sub[sub['tipo'] == 'Débito']['valor'].sum()
        return sub[sub['tipo'] == 'Débito']['valor'].sum() - sub[sub['tipo'] == 'Crédito']['valor'].sum()

    receitas = calc_dre_pdf('Receita', 'Crédito')
    despesas = calc_dre_pdf('Despesa', 'Débito')
    encargos = calc_dre_pdf('Encargos Financeiros', 'Débito')
    ebitda = receitas - despesas
    lucro = ebitda - encargos

    pdf.cell(100, 8, f"Receita Bruta: R$ {receitas:,.2f}", ln=True)
    pdf.cell(100, 8, f"Despesas Operacionais: R$ {despesas:,.2f}", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 8, f"EBITDA: R$ {ebitda:,.2f}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(100, 8, f"Encargos Financeiros: R$ {encargos:,.2f}", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 8, f"LUCRO/PREJUIZO LIQUIDO: R$ {lucro:,.2f}", ln=True)
    pdf.ln(5)

    # 2. Fluxo de Caixa
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "2. Fluxo de Caixa (Baseado no Status)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    entradas = df_periodo[df_periodo['status'] == 'Entrada']['valor'].sum()
    saidas = df_periodo[df_periodo['status'] == 'Pago']['valor'].sum()
    pdf.cell(100, 8, f"Total de Entradas: R$ {entradas:,.2f}", ln=True)
    pdf.cell(100, 8, f"Total de Saidas: R$ {saidas:,.2f}", ln=True)
    pdf.cell(100, 8, f"Variacao Liquida: R$ {entradas - saidas:,.2f}", ln=True)
    pdf.ln(5)

    # 3. Listagem de Lancamentos
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "3. Detalhamento de Lancamentos", ln=True)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(25, 7, "Data", 1)
    pdf.cell(60, 7, "Conta", 1)
    pdf.cell(40, 7, "Grupo", 1)
    pdf.cell(25, 7, "Valor", 1)
    pdf.cell(40, 7, "Status", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 7)
    for _, row in df_periodo.sort_values('data_lancamento').iterrows():
        # .encode('latin-1', 'replace').decode('latin-1') evita erros de caracteres especiais
        pdf.cell(25, 6, str(row['data_lancamento']), 1)
        pdf.cell(60, 6, str(row['descricao'])[:35].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(40, 6, str(row['natureza']).encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(25, 6, f"{row['valor']:,.2f}", 1)
        pdf.cell(40, 6, str(row['status']), 1)
        pdf.ln()

    # Retorno corrigido para compatibilidade com fpdf2
    return pdf.output()

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
            if desc == "" or desc == "+ ADICIONAR NOVA CONTA":
                st.error("Informe o nome da conta.")
            else:
                payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just, "status": status_pag, "data_lancamento": str(data_f)}
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
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; overflow: hidden; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; border-bottom: 2px solid #334155; }
    .conta-corpo { display: flex; min-height: 80px; position: relative; }
    .conta-corpo::after { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1.5px; background-color: #cbd5e1; }
    .lado-debito, .lado-credito { flex: 1; padding: 10px; }
    .valor-deb { color: #059669; font-weight: 600; font-size: 0.8rem; }
    .valor-cre { color: #dc2626; font-weight: 600; text-align: right; font-size: 0.8rem; }
    .just-hint { font-size: 0.7rem; color: #64748b; font-style: italic; display: block; }
    .conta-rodape { padding: 8px; background: #f8fafc; border-top: 1.5px solid #1e293b; text-align: center; font-weight: 700; font-size: 0.85rem; }
    .destaque-balancete { background-color: #f1f5f9; border: 2px solid #1e293b; border-radius: 10px; padding: 15px; margin-top: 20px; }
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

df_periodo = df[(df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)] if not df.empty else df

# BOTÃO PDF CORRIGIDO
with f3:
    if not df_periodo.empty:
        try:
            pdf_bytes = gerar_pdf(df_periodo, data_ini, data_fim, st.session_state.user.email)
            st.download_button(label="📥 Baixar PDF", data=pdf_bytes, file_name=f"relatorio_{data_ini}_{data_fim}.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

if df.empty and st.session_state.menu_opcao != "⚙️ Gestão":
    st.info("Nenhum lançamento encontrado.")
else:
    # --- 1. RAZONETES ---
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
                    deb_html = "".join([f"<div class='valor-deb'>D: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _,r in df_c[df_c['tipo']=='Débito'].iterrows()])
                    cre_html = "".join([f"<div class='valor-cre'>C: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _,r in df_c[df_c['tipo']=='Crédito'].iterrows()])
                    with cols[i % 3]:
                        st.markdown(f"""<div class="conta-card"><div class="conta-titulo">{conta}</div><div class="conta-corpo"><div class="lado-debito">{deb_html}</div><div class="lado-credito">{cre_html}</div></div><div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>""", unsafe_allow_html=True)

    # --- 2. BALANCETE ---
    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("🧾 Balancete de Verificação")
        if df_periodo.empty:
            st.info("Sem dados para o período.")
        else:
            bal_data = []
            for conta in sorted(df_periodo['descricao'].unique()):
                df_c = df_periodo[df_periodo['descricao'] == conta]
                d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                sd, sc = (d - c if d > c else 0), (c - d if c > d else 0)
                bal_data.append({"Conta": conta, "Débito (Mov)": d, "Crédito (Mov)": c, "Saldo Devedor": sd, "Saldo Credor": sc})
            
            bal_df = pd.DataFrame(bal_data)
            st.table(bal_df.style.format(precision=2, decimal=',', thousands='.'))

            st.markdown('<div class="destaque-balancete">', unsafe_allow_html=True)
            st.markdown("#### ⚖️ Resultados Consolidados")
            t_d = bal_df["Débito (Mov)"].sum()
            t_c = bal_df["Crédito (Mov)"].sum()
            t_sd = bal_df["Saldo Devedor"].sum()
            t_sc = bal_df["Saldo Credor"].sum()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Soma Débitos", f"R$ {t_d:,.2f}")
            c2.metric("Soma Créditos", f"R$ {t_c:,.2f}")
            c3.metric("Total Devedor", f"R$ {t_sd:,.2f}")
            c4.metric("Total Credor", f"R$ {t_sc:,.2f}")
            if abs(t_sd - t_sc) < 0.01: st.success("✅ O Balancete está equilibrado.")
            else: st.error(f"⚠️ Desequilíbrio: R$ {abs(t_sd - t_sc):,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. DRE ---
    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 Demonstração do Resultado do Exercício (DRE)")
        
        def calcular_total_por_conta(df_sub, nat):
            if df_sub.empty: return pd.DataFrame(columns=['descricao', 'Total']), 0.0
            if nat == 'Receita':
                res = df_sub.groupby('descricao').apply(lambda x: x[x['tipo'] == 'Crédito']['valor'].sum() - x[x['tipo'] == 'Débito']['valor'].sum(), include_groups=False)
            else:
                res = df_sub.groupby('descricao').apply(lambda x: x[x['tipo'] == 'Débito']['valor'].sum() - x[x['tipo'] == 'Crédito']['valor'].sum(), include_groups=False)
            df_res = res.reset_index(name='Total')
            return df_res, df_res['Total'].sum()

        df_r, tot_r = calcular_total_por_conta(df_periodo[df_periodo['natureza'] == 'Receita'], 'Receita')
        df_d, tot_d = calcular_total_por_conta(df_periodo[df_periodo['natureza'] == 'Despesa'], 'Despesa')
        df_e, tot_e = calcular_total_por_conta(df_periodo[df_periodo['natureza'] == 'Encargos Financeiros'], 'Encargos Financeiros')
        
        ebitda = tot_r - tot_d
        lucro = ebitda - tot_e

        st.write("### 1. Receitas")
        if not df_r.empty:
            for _, r in df_r.iterrows(): st.write(f"    (+) {r['descricao']}: R$ {r['Total']:,.2f}")
        st.write(f"**(=) RECEITA BRUTA: R$ {tot_r:,.2f}**")
        st.divider()

        st.write("### 2. Despesas Operacionais")
        if not df_d.empty:
            for _, r in df_d.iterrows(): st.write(f"    (-) {r['descricao']}: R$ {r['Total']:,.2f}")
        st.write(f"**(=) TOTAL DESPESAS: R$ {tot_d:,.2f}**")
        
        st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #1e293b; margin: 15px 0;">
                <h4 style="margin:0; color: #1e293b;">⚡ EBITDA: R$ {ebitda:,.2f}</h4>
                <small style="color: #64748b;">(Resultado Operacional antes de Encargos e Juros)</small>
            </div>
        """, unsafe_allow_html=True)
        st.divider()

        st.write("### 3. Resultados Financeiros (Encargos)")
        if not df_e.empty:
            for _, r in df_e.iterrows(): st.write(f"    (-) {r['descricao']}: R$ {r['Total']:,.2f}")
        st.write(f"**(=) TOTAL ENCARGOS: R$ {tot_e:,.2f}**")
        st.divider()
        
        cor = "green" if lucro >= 0 else "red"
        st.markdown(f"## Lucro/Prejuízo Líquido: :{cor}[R$ {lucro:,.2f}]")

    # --- 4. FLUXO DE CAIXA ---
    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Fluxo de Caixa (Baseado no Status)")
        
        def calc_saldo_acumulado(data_lim):
            mask = (df['data_lancamento'] <= data_lim)
            sub = df[mask]
            saldo = 0.0
            for _, row in sub.iterrows():
                if row['status'] == "Entrada":
                    saldo += row['valor']
                elif row['status'] == "Pago":
                    saldo -= row['valor']
            return saldo

        si = calc_saldo_acumulado(data_ini - timedelta(days=1))
        sf = calc_saldo_acumulado(data_fim)
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown('<div style="background:#f0f9ff; padding:15px; border-radius:10px; border-left:5px solid #0ea5e9">', unsafe_allow_html=True)
            st.metric("Saldo Inicial", f"R$ {si:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        with m2:
            st.markdown('<div style="background:#f0fdf4; padding:15px; border-radius:10px; border-left:5px solid #22c55e">', unsafe_allow_html=True)
            st.metric("Variação Líquida", f"R$ {sf-si:,.2f}", delta=f"{sf-si:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        with m3:
            st.markdown('<div style="background:#fef2f2; padding:15px; border-radius:10px; border-left:5px solid #ef4444">', unsafe_allow_html=True)
            st.metric("Saldo Final", f"R$ {sf:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        st.write("### 📄 Detalhamento de Movimentações (Entradas e Saídas)")
        df_f = df_periodo[df_periodo['status'].isin(["Entrada", "Pago"])]
        if not df_f.empty:
            st.dataframe(df_f[['data_lancamento', 'descricao', 'natureza', 'valor', 'status', 'justificativa']], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma entrada ou saída registrada no período selecionado.")

    # --- 5. GESTÃO ---
    elif st.session_state.menu_opcao == "⚙️ Gestão":
        col_tit, col_reset = st.columns([4, 1])
        with col_tit:
            st.subheader("⚙️ Gestão de Lançamentos")
        with col_reset:
            if st.button("🚨 Resetar Banco", use_container_width=True):
                st.session_state.confirm_reset = True
            
            if st.session_state.confirm_reset:
                st.warning("Confirmar exclusão de TODOS os seus dados?")
                cr1, cr2 = st.columns(2)
                if cr1.button("Sim, apagar", type="primary"):
                    supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
                    st.session_state.confirm_reset = False
                    st.cache_data.clear()
                    st.rerun()
                if cr2.button("Cancelar"):
                    st.session_state.confirm_reset = False
                    st.rerun()

        st.divider()
        if df.empty:
            st.info("Nenhum dado cadastrado para gerenciar.")
        else:
            for _, row in df.sort_values(by='data_lancamento', ascending=False).iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([5, 0.5, 0.5])
                    c1.write(f"**[{row['data_lancamento']}] {row['descricao']}**")
                    c1.caption(f"Natureza: {row['natureza']} | Status: {row['status']} | Valor: R$ {row['valor']:,.2f}")
                    if c2.button("✏️", key=f"ed_{row['id']}"): 
                        st.session_state.edit_id = row['id']
                        st.rerun()
                    if c3.button("🗑️", key=f"del_{row['id']}"): 
                        supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.rerun()
                    st.markdown("---")
