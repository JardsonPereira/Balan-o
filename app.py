import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="ContabilApp - Sistema Integrado", layout="wide")

# Limpeza de cache para atualização em tempo real
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

# --- FUNÇÃO CARREGAR DADOS ---
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

# --- LOGICA DE SALDO DE CAIXA (PARA FLUXO) ---
def calc_saldo_caixa_ate(df_completo, data_limite):
    if df_completo.empty: return 0.0
    sub = df_completo[df_completo['data_lancamento'] <= data_limite]
    entradas = sub[sub['status'] == "Entrada"]['valor'].sum()
    saidas = sub[sub['status'] == "Pago"]['valor'].sum()
    return entradas - saidas

# --- AUTENTICAÇÃO ---
def gerenciar_acesso():
    st.sidebar.title("🔐 Acesso")
    menu = st.sidebar.radio("Escolha", ["Login", "Criar Conta"])
    email = st.sidebar.text_input("E-mail").lower().strip()
    senha = st.sidebar.text_input("Senha", type="password")
    if menu == "Login" and st.sidebar.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
            st.session_state.user = res.user
            st.rerun()
        except: st.sidebar.error("Erro no login.")
    elif menu == "Criar Conta" and st.sidebar.button("Cadastrar"):
        try:
            supabase.auth.sign_up({"email": email, "password": senha})
            st.sidebar.success("Conta criada!")
        except Exception as e: st.sidebar.error(f"Erro: {e}")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

# Carregamento imediato
df = carregar_dados(st.session_state.user.id)

# --- FORMULÁRIO LATERAL ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.user.email}**")
    if st.button("Sair"):
        st.session_state.user = None
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
        conta_sel = st.selectbox("Conta", opcoes_conta, index=0)
        desc_input = st.text_input("Nome da Conta", value=reg['descricao']).upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel
        data_f = st.date_input("Data", value=reg['data_lancamento'])
        nat = st.selectbox("Grupo", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=0)
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(reg['valor']))
        status_pag = st.selectbox("Status Financeiro", ["Pago", "Entrada", "Pendente", "Investimento", "Transferência Interna"])
        just = st.text_area("Justificativa", value=reg['justificativa'])
        
        if st.form_submit_button("Confirmar"):
            payload = {"user_id": st.session_state.user.id, "descricao": desc_input, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just, "status": status_pag, "data_lancamento": str(data_f)}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.session_state.form_count += 1
            st.rerun()

# --- FILTROS DE DATA ---
st.title("📑 Sistema Contábil Digital")
col_nav = st.columns(5)
opcoes_menu = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes_menu):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()
f1, f2 = st.columns(2)
with f1: data_ini = st.date_input("Início do Período", value=datetime.now().date().replace(day=1))
with f2: data_fim = st.date_input("Fim do Período", value=datetime.now().date())

# Processamento de Dados do Período
df_periodo = df[(df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)].copy()

# --- LOGICA DAS ABAS ---
if st.session_state.menu_opcao == "📊 Razonetes":
    if df_periodo.empty: st.info("Sem dados no período.")
    else:
        for grupo in sorted(df_periodo['natureza'].unique()):
            st.subheader(grupo)
            df_g = df_periodo[df_periodo['natureza'] == grupo]
            cols = st.columns(3)
            for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                df_c = df_g[df_g['descricao'] == conta]
                v_d, v_c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                saldo = (v_d - v_c) if grupo in ["Ativo", "Despesa", "Encargos Financeiros"] else (v_c - v_d)
                with cols[i % 3]:
                    st.markdown(f"**{conta}** (Saldo: R$ {saldo:,.2f})")
                    st.write(f"D: {v_d:,.2f} | C: {v_c:,.2f}")
                    st.divider()

elif st.session_state.menu_opcao == "🧾 Balancete":
    st.subheader("🧾 Balancete de Verificação")
    if df_periodo.empty: st.info("Sem dados no período.")
    else:
        bal_data = []
        for conta in sorted(df_periodo['descricao'].unique()):
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c, "SD": d-c if d>c else 0, "SC": c-d if c>d else 0})
        df_bal = pd.DataFrame(bal_data)
        st.table(df_bal.style.format(precision=2))
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Soma Débitos", f"R$ {df_bal['Débito'].sum():,.2f}")
        c2.metric("Soma Créditos", f"R$ {df_bal['Crédito'].sum():,.2f}")
        c3.metric("Total Devedor", f"R$ {df_bal['SD'].sum():,.2f}")
        c4.metric("Total Credor", f"R$ {df_bal['SC'].sum():,.2f}")

elif st.session_state.menu_opcao == "📈 DRE":
    st.subheader("📈 DRE")
    rec = df_periodo[(df_periodo['natureza'] == 'Receita') & (df_periodo['tipo'] == 'Crédito')]['valor'].sum()
    desp = df_periodo[(df_periodo['natureza'] == 'Despesa') & (df_periodo['tipo'] == 'Débito')]['valor'].sum()
    st.metric("Receita Bruta", f"R$ {rec:,.2f}")
    st.metric("Despesas Operacionais", f"R$ {desp:,.2f}")
    st.info(f"⚡ Resultado Líquido: R$ {rec - desp:,.2f}")

elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
    st.subheader("💸 Fluxo de Caixa (Saldos Transportados)")
    s_ini = calc_saldo_caixa_ate(df, data_ini - timedelta(days=1))
    s_fin = calc_saldo_caixa_ate(df, data_fim)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo Inicial (Anterior)", f"R$ {s_ini:,.2f}")
    c2.metric("Saldo Final (Atual)", f"R$ {s_fin:,.2f}")
    c3.metric("Variação", f"R$ {s_fin - s_ini:,.2f}", delta=f"{s_fin - s_ini:,.2f}")

elif st.session_state.menu_opcao == "⚙️ Gestão":
    if st.button("🚨 Resetar Tudo"):
        supabase.table("lancamentos").delete().eq("user_id", st.session_state.user.id).execute()
        st.rerun()
    st.divider()
    for _, row in df.sort_values(by='data_lancamento', ascending=False).iterrows():
        with st.expander(f"{row['data_lancamento']} | {row['descricao']} | R$ {row['valor']}"):
            if st.button("✏️ Editar", key=f"e_{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if st.button("🗑️ Excluir", key=f"x_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
