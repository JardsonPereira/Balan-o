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

# --- FUNÇÃO PARA GERAR PDF (ATUALIZADA COM JUSTIFICATIVAS) ---
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

    # --- 1. DRE ---
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
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 7, f"EBITDA: R$ {ebitda:,.2f}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(100, 7, f"Encargos Financeiros: R$ {encargos:,.2f}", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 7, f"LUCRO/PREJUIZO LIQUIDO: R$ {lucro_periodo:,.2f}", ln=True)
    pdf.ln(5)

    # --- 2. BALANCETE PATRIMONIAL ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "2. Balancete Patrimonial", ln=True)
    
    def render_secao_balancete(titulo, nat, tipo_dev):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(190, 8, titulo, ln=True)
        pdf.set_font("Helvetica", "", 9)
        contas = sorted(df_periodo[df_periodo['natureza'] == nat]['descricao'].unique())
        total_secao = 0
        for conta in contas:
            df_c = df_periodo[(df_periodo['natureza'] == nat) & (df_periodo['descricao'] == conta)]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            saldo = (d - c) if tipo_dev else (c - d)
            pdf.cell(140, 6, f"  {conta.capitalize()}", border="B")
            pdf.cell(50, 6, f"R$ {saldo:,.2f}", border="B", ln=True, align="R")
            total_secao += saldo
        return total_secao

    total_ativo = render_secao_balancete("ATIVO", "Ativo", True)
    total_passivo = render_secao_balancete("PASSIVO", "Passivo", False)
    total_pl = render_secao_balancete("PATRIMONIO LIQUIDO", "Patrimônio Líquido", False)

    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(140, 6, "  (+) Resultado do Periodo (Lucro/Prejuizo)", border="B")
    pdf.cell(50, 6, f"R$ {lucro_periodo:,.2f}", border="B", ln=True, align="R")
    
    total_pl_final = total_pl + lucro_periodo
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(140, 8, "TOTAL DO ATIVO")
    pdf.cell(50, 8, f"R$ {total_ativo:,.2f}", ln=True, align="R")
    pdf.cell(140, 8, "TOTAL DO PASSIVO + PL")
    pdf.cell(50, 8, f"R$ {total_passivo + total_pl_final:,.2f}", ln=True, align="R")
    pdf.ln(5)

    # --- 3. FLUXO DE CAIXA ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "3. Fluxo de Caixa", ln=True)
    pdf.set_font("Helvetica", "", 10)
    entradas = df_periodo[df_periodo['status'] == 'Entrada']['valor'].sum()
    saidas = df_periodo[df_periodo['status'] == 'Pago']['valor'].sum()
    pdf.cell(100, 7, f"Total de Entradas: R$ {entradas:,.2f}", ln=True)
    pdf.cell(100, 7, f"Total de Saidas: R$ {saidas:,.2f}", ln=True)
    pdf.cell(100, 7, f"Variacao Liquida: R$ {entradas - saidas:,.2f}", ln=True)
    pdf.ln(5)

    # --- 4. LISTAGEM DETALHADA COM JUSTIFICATIVAS ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "4. Detalhamento de Lancamentos", ln=True)
    pdf.set_font("Helvetica", "B", 7)
    
    # Cabeçalho da Tabela
    pdf.cell(20, 7, "Data", 1)
    pdf.cell(40, 7, "Conta", 1)
    pdf.cell(25, 7, "Grupo", 1)
    pdf.cell(20, 7, "Valor", 1)
    pdf.cell(25, 7, "Status", 1)
    pdf.cell(60, 7, "Justificativa", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 6)
    for _, row in df_periodo.sort_values('data_lancamento').iterrows():
        # Limpeza de strings para evitar erro latin-1
        desc = str(row['descricao'])[:30].encode('latin-1', 'replace').decode('latin-1')
        nat = str(row['natureza']).encode('latin-1', 'replace').decode('latin-1')
        stat = str(row['status']).encode('latin-1', 'replace').decode('latin-1')
        just = str(row['justificativa'])[:45].encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(20, 6, str(row['data_lancamento']), 1)
        pdf.cell(40, 6, desc, 1)
        pdf.cell(25, 6, nat, 1)
        pdf.cell(20, 6, f"{row['valor']:,.2f}", 1)
        pdf.cell(25, 6, stat, 1)
        pdf.cell(60, 6, just, 1)
        pdf.ln()

    return bytes(pdf.output())

# --- RESTANTE DO CÓDIGO (LÓGICA STREAMLIT) ---

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
</style>""", unsafe_allow_html=True)

st.title("📑 Sistema Contábil Digital")

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
            st.download_button(label="📥 Baixar PDF", data=pdf_bytes, file_name=f"relatorio_{data_ini}_{data_fim}.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

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
                    deb_html = "".join([f"<div class='valor-deb'>D: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _,r in df_c[df_c['tipo']=='Débito'].iterrows()])
                    cre_html = "".join([f"<div class='valor-cre'>C: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _,r in df_c[df_c['tipo']=='Crédito'].iterrows()])
                    with cols[i % 3]:
                        st.markdown(f"""<div class="conta-card"><div class="conta-titulo">{conta}</div><div class="conta-corpo"><div class="lado-debito">{deb_html}</div><div class="lado-credito">{cre_html}</div></div><div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>""", unsafe_allow_html=True)

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
            t_sd, t_sc = bal_df["Saldo Devedor"].sum(), bal_df["Saldo Credor"].sum()
            c1, c2 = st.columns(2)
            c1.metric("Total Devedor", f"R$ {t_sd:,.2f}")
            c2.metric("Total Credor", f"R$ {t_sc:,.2f}")
            if abs(t_sd - t_sc) < 0.01: st.success("✅ O Balancete está equilibrado.")
            else: st.error(f"⚠️ Desequilíbrio: R$ {abs(t_sd - t_sc):,.2f}")

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 Demonstração do Resultado do Exercício (DRE)")
        def calcular_total_por_conta(df_sub, nat):
            if df_sub.empty: return pd.DataFrame(columns=['descricao', 'Total']), 0.0
            if nat == 'Receita':
                res = df_sub.groupby('descricao').apply(lambda x: x[x['tipo'] == 'Crédito']['valor'].sum() - x[x['tipo'] == 'Débito']['valor'].sum(), include_groups=False)
            else:
                res = df_sub.groupby('descricao').apply(lambda x: x[x['tipo'] == 'Débito']['valor'].sum() - x[x['tipo'] == 'Crédito']['valor'].sum(), include_groups=False)
            return res.reset_index(name='Total'), res.sum()

        df_r, tot_r = calcular_total_por_conta(df_periodo[df_periodo['natureza'] == 'Receita'], 'Receita')
        df_d, tot_d = calcular_total_por_conta(df_periodo[df_periodo['natureza'] == 'Despesa'], 'Despesa')
        df_e, tot_e = calcular_total_por_conta(df_periodo[df_periodo['natureza'] == 'Encargos Financeiros'], 'Encargos Financeiros')
        ebitda = tot_r - tot_d
        lucro = ebitda - tot_e

        st.write(f"**RECEITA BRUTA: R$ {tot_r:,.2f}**")
        st.write(f"**TOTAL DESPESAS: R$ {tot_d:,.2f}**")
        st.markdown(f"""<div style="background:#f8fafc;padding:15px;border-radius:10px;border:1px solid #1e293b;margin:15px 0;"><h4>⚡ EBITDA: R$ {ebitda:,.2f}</h4></div>""", unsafe_allow_html=True)
        st.write(f"**TOTAL ENCARGOS: R$ {tot_e:,.2f}**")
        cor = "green" if lucro >= 0 else "red"
        st.markdown(f"## Lucro/Prejuízo Líquido: :{cor}[R$ {lucro:,.2f}]")

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Fluxo de Caixa (Status)")
        def calc_saldo(data_lim):
            sub = df[df['data_lancamento'] <= data_lim]
            return sub[sub['status'] == "Entrada"]['valor'].sum() - sub[sub['status'] == "Pago"]['valor'].sum()
        si, sf = calc_saldo(data_ini - timedelta(days=1)), calc_saldo(data_fim)
        m1, m2, m3 = st.columns(3)
        m1.metric("Saldo Inicial", f"R$ {si:,.2f}")
        m2.metric("Variação", f"R$ {sf-si:,.2f}", delta=f"{sf-si:,.2f}")
        m3.metric("Saldo Final", f"R$ {sf:,.2f}")
        df_f = df_periodo[df_periodo['status'].isin(["Entrada", "Pago"])]
        st.dataframe(df_f[['data_lancamento', 'descricao', 'natureza', 'valor', 'status', 'justificativa']], use_container_width=True, hide_index=True)

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        if st.button("🚨 Resetar Banco"):
            supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
            st.cache_data.clear()
            st.rerun()
        for _, row in df.sort_values(by='data_lancamento', ascending=False).iterrows():
            with st.container():
                c1, c2, c3 = st.columns([5, 0.5, 0.5])
                c1.write(f"**[{row['data_lancamento']}] {row['descricao']}** | R$ {row['valor']:,.2f} ({row['status']})")
                if c2.button("✏️", key=f"ed_{row['id']}"): 
                    st.session_state.edit_id = row['id']
                    st.rerun()
                if c3.button("🗑️", key=f"del_{row['id']}"): 
                    supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                    st.cache_data.clear()
                    st.rerun()
                st.markdown("---")
