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
def gerar_pdf(df_periodo, data_ini, data_fim, user_email, s_ini, s_fin):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(190, 10, "Relatorio Contabil Consolidado", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(190, 10, f"Periodo: {data_ini} ate {data_fim} | Usuario: {user_email}", ln=True, align="C")
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, f"Saldo Inicial Transportado: R$ {s_ini:,.2f}", ln=True)
    pdf.cell(190, 10, f"Saldo Final em Caixa: R$ {s_fin:,.2f}", ln=True)
    
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

# --- LÓGICA DE SALDO TRANSPORTADO ---
def calc_saldo_caixa_ate(data_limite):
    if df.empty: return 0.0
    sub = df[df['data_lancamento'] <= data_limite]
    entradas = sub[sub['status'] == "Entrada"]['valor'].sum()
    saidas = sub[sub['status'] == "Pago"]['valor'].sum()
    return entradas - saidas

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

# Cálculo de Saldo Transportado
saldo_inicial_transporte = calc_saldo_caixa_ate(data_ini - timedelta(days=1))
saldo_final_periodo = calc_saldo_caixa_ate(data_fim)

df_periodo = df[(df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)] if not df.empty else pd.DataFrame()

with f3:
    if not df_periodo.empty:
        try:
            pdf_bytes = gerar_pdf(df_periodo, data_ini, data_fim, st.session_state.user.email, saldo_inicial_transporte, saldo_final_periodo)
            st.download_button(label="📥 Baixar PDF", data=pdf_bytes, file_name="relatorio.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e: st.error(f"Erro PDF: {e}")

# --- CONTEÚDO ---
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
                                st.markdown(f'<div class="valor-deb">D: {r["valor"]:,.2f}</div>', unsafe_allow_html=True)
                        with c_cre:
                            for _, r in df_c[df_c['tipo']=='Crédito'].iterrows():
                                st.markdown(f'<div class="valor-cre">C: {r["valor"]:,.2f}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>', unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("🧾 Balancete de Verificação")
        bal_data = []
        for conta in sorted(df_periodo['descricao'].unique()):
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c, "SD": d-c if d>c else 0, "SC": c-d if c>d else 0})
        st.table(pd.DataFrame(bal_data))

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 Demonstração do Resultado (DRE)")
        rec = df_periodo[(df_periodo['natureza'] == 'Receita') & (df_periodo['tipo'] == 'Crédito')]['valor'].sum()
        desp = df_periodo[(df_periodo['natureza'] == 'Despesa') & (df_periodo['tipo'] == 'Débito')]['valor'].sum()
        st.metric("Receita Bruta", f"R$ {rec:,.2f}")
        st.metric("Despesas Operacionais", f"R$ {desp:,.2f}")
        st.info(f"⚡ EBITDA/Lucro: R$ {rec - desp:,.2f}")

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("💸 Fluxo de Caixa (Transporte Automático)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo Inicial (do mês anterior)", f"R$ {saldo_inicial_transporte:,.2f}")
        c2.metric("Saldo Final (este mês)", f"R$ {saldo_final_periodo:,.2f}")
        c3.metric("Variação", f"R$ {saldo_final_periodo - saldo_inicial_transporte:,.2f}", delta=f"{saldo_final_periodo - saldo_inicial_transporte:,.2f}")

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("⚙️ Gestão de Lançamentos")
        
        if st.button("🚨 Resetar Todos os Lançamentos", type="primary"):
            supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
            st.cache_data.clear()
            st.rerun()
            
        st.divider()
        
        if not df.empty:
            # Ordenar por data mais recente para facilitar a gestão
            df_sorted = df.sort_values(by='data_lancamento', ascending=False)
            for _, row in df_sorted.iterrows():
                with st.expander(f"📅 {row['data_lancamento']} | {row['descricao']} | R$ {row['valor']:,.2f}"):
                    st.write(f"**Grupo:** {row['natureza']} | **Tipo:** {row['tipo']} | **Status:** {row['status']}")
                    st.write(f"**Justificativa:** {row['justificativa']}")
                    
                    col_ed, col_ex = st.columns(2)
                    if col_ed.button("✏️ Editar", key=f"edit_{row['id']}"):
                        st.session_state.edit_id = row['id']
                        st.rerun()
                    
                    if col_ex.button("🗑️ Excluir", key=f"del_{row['id']}"):
                        supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.rerun()
