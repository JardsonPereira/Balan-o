import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
from fpdf import FPDF
import io

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="ContabilApp - Sistema Integrado", layout="wide")
st.cache_data.clear()

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

# --- FUNÇÕES AUXILIARES ---
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

def gerar_pdf(user_email, df_per, data_i, data_f, s_ini, s_fin, v_at, v_pas, v_pl, v_rec, v_desp, v_ebitda, v_finan, v_lucro):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "RELATÓRIO CONTÁBIL CONSOLIDADO", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 7, f"Usuário: {user_email}", ln=True, align="C")
    pdf.cell(190, 7, f"Período: {data_i} até {data_f} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    # 1. FLUXO DE CAIXA
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "1. FLUXO DE CAIXA", ln=True, fill=False)
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 8, f"Saldo Inicial: R$ {s_ini:,.2f}", border=1)
    pdf.cell(95, 8, f"Saldo Final: R$ {s_fin:,.2f}", border=1, ln=True)
    pdf.ln(5)

    # 2. DEMONSTRAÇÃO DO RESULTADO (DRE)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "2. DEMONSTRAÇÃO DO RESULTADO (DRE)", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(140, 8, "(+) Receitas Brutas", border=1)
    pdf.cell(50, 8, f"R$ {v_rec:,.2f}", border=1, ln=True, align="R")
    pdf.cell(140, 8, "(-) Despesas Operacionais", border=1)
    pdf.cell(50, 8, f"R$ ({v_desp:,.2f})", border=1, ln=True, align="R")
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(140, 8, "(=) EBITDA", border=1)
    pdf.cell(50, 8, f"R$ {v_ebitda:,.2f}", border=1, ln=True, align="R")
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(140, 8, "(-) Encargos Financeiros / Impostos", border=1)
    pdf.cell(50, 8, f"R$ ({v_finan:,.2f})", border=1, ln=True, align="R")
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(140, 8, "(=) LUCRO LÍQUIDO DO PERÍODO", border=1)
    pdf.cell(50, 8, f"R$ {v_lucro:,.2f}", border=1, ln=True, align="R")
    pdf.ln(5)

    # 3. BALANÇO PATRIMONIAL RESUMIDO
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "3. BALANÇO PATRIMONIAL", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 8, f"ATIVOS TOTAIS: R$ {v_at:,.2f}", border=1)
    pdf.cell(95, 8, f"PASSIVOS TOTAIS: R$ {v_pas:,.2f}", border=1, ln=True)
    pdf.cell(95, 8, f"PATRIMÔNIO LÍQUIDO: R$ {v_pl:,.2f}", border=1)
    pdf.cell(95, 8, f"LUCRO ACUMULADO: R$ {v_lucro:,.2f}", border=1, ln=True)
    pdf.ln(10)

    # 4. LANÇAMENTOS DETALHADOS
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "4. LANÇAMENTOS DO PERÍODO", ln=True)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(20, 8, "Data", border=1)
    pdf.cell(50, 8, "Conta", border=1)
    pdf.cell(20, 8, "Tipo", border=1)
    pdf.cell(30, 8, "Valor", border=1)
    pdf.cell(35, 8, "Natureza", border=1)
    pdf.cell(35, 8, "Status", border=1, ln=True)
    
    pdf.set_font("Arial", "", 7)
    for _, row in df_per.sort_values('data_lancamento').iterrows():
        pdf.cell(20, 7, str(row['data_lancamento']), border=1)
        pdf.cell(50, 7, str(row['descricao'])[:28], border=1)
        pdf.cell(20, 7, str(row['tipo']), border=1)
        pdf.cell(30, 7, f"{row['valor']:,.2f}", border=1)
        pdf.cell(35, 7, str(row['natureza']), border=1)
        pdf.cell(35, 7, str(row['status']), border=1, ln=True)

    return pdf.output()

# --- AUTENTICAÇÃO ---
if st.session_state.user is None:
    st.sidebar.title("🔐 Acesso")
    menu = st.sidebar.radio("Escolha", ["Login", "Criar Conta"])
    email = st.sidebar.text_input("E-mail").lower().strip()
    senha = st.sidebar.text_input("Senha", type="password")
    if menu == "Login" and st.sidebar.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
            st.session_state.user = res.user
            st.rerun()
        except: st.sidebar.error("E-mail ou senha incorretos.")
    elif menu == "Criar Conta" and st.sidebar.button("Cadastrar"):
        supabase.auth.sign_up({"email": email, "password": senha})
        st.sidebar.success("Conta criada!")
    st.stop()

df_base = carregar_dados(st.session_state.user.id)

# --- FORMULÁRIO LATERAL ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.user.email}**")
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df_base.empty:
        st.header("📝 Editar Lançamento")
        reg = df_base[df_base['id'] == st.session_state.edit_id].iloc[0]
        if st.button("Cancelar Edição"):
            st.session_state.edit_id = None
            st.rerun()
    else:
        st.header("➕ Novo Lançamento")
        reg = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago", "data_lancamento": datetime.now().date()}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df_base['descricao'].unique().tolist()) if not df_base.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        idx_conta = opcoes_conta.index(reg['descricao']) if reg['descricao'] in contas_existentes else 0
        
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        desc_input = st.text_input("Nome da Conta", value=reg['descricao']).upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel
        data_f = st.date_input("Data", value=reg['data_lancamento'])
        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(reg['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if reg['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(reg['valor']))
        status_pag = st.selectbox("Status", ["Pago", "Entrada", "Pendente", "Investimento", "Transferência Interna"], index=0)
        just_input = st.text_area("Justificativa", value=reg['justificativa'])
        
        if st.form_submit_button("Confirmar"):
            payload = {"user_id": st.session_state.user.id, "descricao": desc_input, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just_input, "status": status_pag, "data_lancamento": str(data_f)}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.session_state.form_count += 1
            st.rerun()

# --- CSS ---
st.markdown("""<style>
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; border-radius: 12px 12px 0 0; }
    .conta-rodape { padding: 8px; background: #f8fafc; text-align: center; font-weight: 700; border-top: 1px solid #e2e8f0; border-radius: 0 0 12px 12px; }
    .valor-deb { color: #059669; font-size: 0.8rem; padding: 2px 10px; font-weight: 600; }
    .valor-cre { color: #dc2626; font-size: 0.8rem; text-align: right; padding: 2px 10px; font-weight: 600; }
    .just-box { font-size: 0.65rem; color: #64748b; font-style: italic; padding: 0 10px 5px 10px; line-height: 1.1; }
    .dre-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #f1f5f9; }
    .dre-total { font-weight: bold; border-top: 2px solid #1e293b; margin-top: 10px; padding-top: 5px; font-size: 1.1rem; }
</style>""", unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
st.title("📑 Sistema Contábil Digital")
col_nav = st.columns(5)
opcoes_menu = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes_menu):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()

# --- FILTROS ---
f1, f2 = st.columns(2)
with f1: data_ini = st.date_input("Início", value=datetime.now().date().replace(day=1))
with f2: data_fim = st.date_input("Fim", value=datetime.now().date())
df_periodo = df_base[(df_base['data_lancamento'] >= data_ini) & (df_base['data_lancamento'] <= data_fim)].copy()

# --- CÁLCULOS TÉCNICOS ---
def get_caixa(data_limite):
    sub = df_base[df_base['data_lancamento'] <= data_limite]
    return sub[sub['status'] == "Entrada"]['valor'].sum() - sub[sub['status'] == "Pago"]['valor'].sum()

s_ini = get_caixa(data_ini - timedelta(days=1))
t_ent = df_periodo[df_periodo['status'] == "Entrada"]['valor'].sum()
t_sai = df_periodo[df_periodo['status'] == "Pago"]['valor'].sum()
s_fin = s_ini + t_ent - t_sai

# DRE
v_rec = df_periodo[(df_periodo['natureza'] == 'Receita') & (df_periodo['tipo'] == 'Crédito')]['valor'].sum()
v_desp_op = df_periodo[(df_periodo['natureza'] == 'Despesa') & (df_periodo['tipo'] == 'Débito')]['valor'].sum()
ebitda = v_rec - v_desp_op
v_finan = df_periodo[(df_periodo['natureza'] == 'Encargos Financeiros') & (df_periodo['tipo'] == 'Débito')]['valor'].sum()
v_lucro = ebitda - v_finan

# Balanço
v_at = df_periodo[df_periodo['natureza'] == 'Ativo']['valor'].sum() + s_fin
v_pas = df_periodo[df_periodo['natureza'] == 'Passivo']['valor'].sum() + df_periodo[df_periodo['status'] == 'Pendente']['valor'].sum()
v_pl = df_periodo[df_periodo['natureza'] == 'Patrimônio Líquido']['valor'].sum()

# Botão Impressão
col_imp, _ = st.columns([1, 4])
with col_imp:
    pdf_bytes = gerar_pdf(st.session_state.user.email, df_periodo, data_ini, data_fim, s_ini, s_fin, v_at, v_pas, v_pl, v_rec, v_desp_op, ebitda, v_finan, v_lucro)
    st.download_button("🖨️ Baixar PDF do Período", data=bytes(pdf_bytes), file_name=f"Relatorio_{data_ini}.pdf", mime="application/pdf")

# --- CONTEÚDO ---
if df_periodo.empty and st.session_state.menu_opcao != "⚙️ Gestão":
    st.info("Nenhum lançamento no período.")
else:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for grupo in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df_periodo[df_periodo['natureza'] == grupo]
            if not df_g.empty:
                st.subheader(grupo)
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    df_c = df_g[df_g['descricao'] == conta]
                    v_d, v_c = df_c[df_c['tipo']=='Débito']['valor'].sum(), df_c[df_c['tipo']=='Crédito']['valor'].sum()
                    saldo = (v_d - v_c) if grupo in ["Ativo", "Despesa", "Encargos Financeiros"] else (v_c - v_d)
                    with cols[i % 3]:
                        st.markdown(f'<div class="conta-card"><div class="conta-titulo">{conta}</div>', unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        with c1: 
                            for _, r in df_c[df_c['tipo']=='Débito'].iterrows(): st.markdown(f'<div class="valor-deb">D: {r["valor"]:,.2f}</div><div class="just-box">{r["justificativa"]}</div>', unsafe_allow_html=True)
                        with c2: 
                            for _, r in df_c[df_c['tipo']=='Crédito'].iterrows(): st.markdown(f'<div class="valor-cre">C: {r["valor"]:,.2f}</div><div class="just-box">{r["justificativa"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>', unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("🧾 Balancete de Verificação")
        bal_data = []
        for conta in sorted(df_periodo['descricao'].unique()):
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d, c = df_c[df_c['tipo']=='Débito']['valor'].sum(), df_c[df_c['tipo']=='Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c, "SD": d-c if d>c else 0, "SC": c-d if c>d else 0})
        df_bal = pd.DataFrame(bal_data)
        st.table(df_bal.style.format(precision=2))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Soma Débitos", f"R$ {df_bal['Débito'].sum():,.2f}")
        c2.metric("Soma Créditos", f"R$ {df_bal['Crédito'].sum():,.2f}")
        c3.metric("Total Devedor (SD)", f"R$ {df_bal['SD'].sum():,.2f}")
        c4.metric("Total Credor (SC)", f"R$ {df_bal['SC'].sum():,.2f}")

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 DRE Detalhada")
        col_d, col_m = st.columns([2, 1])
        with col_d:
            st.markdown("**(+) RECEITAS**")
            for _, r in df_periodo[(df_periodo['natureza']=='Receita') & (df_periodo['tipo']=='Crédito')].groupby('descricao')['valor'].sum().reset_index().iterrows():
                st.markdown(f'<div class="dre-row"><span>{r["descricao"]}</span><span>R$ {r["valor"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown("**(-) DESPESAS OPERACIONAIS**")
            for _, r in df_periodo[(df_periodo['natureza']=='Despesa') & (df_periodo['tipo']=='Débito')].groupby('descricao')['valor'].sum().reset_index().iterrows():
                st.markdown(f'<div class="dre-row"><span>{r["descricao"]}</span><span>(R$ {r["valor"]:,.2f})</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dre-total" style="color:#059669">(=) EBITDA: R$ {ebitda:,.2f}</div>', unsafe_allow_html=True)
            st.markdown("**(-) FINANCEIRO / IMPOSTOS**")
            for _, r in df_periodo[(df_periodo['natureza']=='Encargos Financeiros') & (df_periodo['tipo']=='Débito')].groupby('descricao')['valor'].sum().reset_index().iterrows():
                st.markdown(f'<div class="dre-row"><span>{r["descricao"]}</span><span>(R$ {r["valor"]:,.2f})</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dre-total" style="color:{"#059669" if v_lucro >=0 else "#dc2626"}">(=) LUCRO LÍQUIDO: R$ {v_lucro:,.2f}</div>', unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("💸 Fluxo e Liquidez")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Saldo Inicial", f"R$ {s_ini:,.2f}")
        m2.metric("Saldo Final", f"R$ {s_fin:,.2f}")
        m3.metric("Fluxo Líquido", f"R$ {t_ent - t_sai:,.2f}")
        liq = (s_ini + t_ent) / (t_sai + df_periodo[df_periodo['status']=='Pendente']['valor'].sum() + 1)
        m4.metric("Índice Liquidez", f"{liq:.2f}")
        
        st.markdown("### Análise Patrimonial")
        c1, c2 = st.columns(2)
        c1.markdown(f'<div class="conta-card"><div class="conta-titulo" style="background:#0369a1">ATIVOS TOTAIS</div><div style="padding:20px; text-align:center; font-size:1.5rem; color:#0369a1; font-weight:bold;">R$ {v_at:,.2f}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="conta-card"><div class="conta-titulo" style="background:#be123c">PASSIVOS TOTAIS</div><div style="padding:20px; text-align:center; font-size:1.5rem; color:#be123c; font-weight:bold;">R$ {v_pas:,.2f}</div></div>', unsafe_allow_html=True)
        st.dataframe(df_periodo[df_periodo['status'].isin(["Entrada", "Pago"])], use_container_width=True)

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        if st.button("🚨 Resetar Tudo"):
            supabase.table("lancamentos").delete().eq("user_id", st.session_state.user.id).execute()
            st.rerun()
        for _, row in df_base.sort_values('data_lancamento', ascending=False).iterrows():
            with st.expander(f"{row['data_lancamento']} | {row['descricao']} | R$ {row['valor']}"):
                c_ed, c_ex = st.columns(2)
                if c_ed.button("✏️ Editar", key=f"ed_{row['id']}"):
                    st.session_state.edit_id = row['id']
                    st.rerun()
                if c_ex.button("🗑️ Excluir", key=f"ex_{row['id']}"):
                    supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                    st.rerun()
