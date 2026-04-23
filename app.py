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

# --- ESTADOS ---
if 'user' not in st.session_state: st.session_state.user = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'menu_opcao' not in st.session_state: st.session_state.menu_opcao = "📊 Razonetes"
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = "login"

# --- LOGIN ---
def tela_autenticacao():
    st.markdown("<div style='text-align: center; padding: 2rem 0;'><h1 style='color: #1e3a8a;'>ERP CONTÁBIL PRO</h1></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.container(border=True):
            if st.session_state.auth_mode == "login":
                st.subheader("Acesso ao Sistema")
                email = st.text_input("E-mail").lower().strip()
                senha = st.text_input("Senha", type="password")
                if st.button("Entrar", use_container_width=True, type="primary"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state.user = res.user
                        st.rerun()
                    except: st.error("E-mail ou senha incorretos.")
                if st.button("Criar Conta", use_container_width=True): st.session_state.auth_mode = "cadastro"; st.rerun()
            elif st.session_state.auth_mode == "cadastro":
                st.subheader("Novo Cadastro")
                n_email = st.text_input("E-mail").lower().strip()
                n_pass = st.text_input("Senha", type="password")
                if st.button("Cadastrar", use_container_width=True, type="primary"):
                    try:
                        supabase.auth.sign_up({"email": n_email, "password": n_pass})
                        st.success("Sucesso! Verifique seu e-mail.")
                    except Exception as e: st.error(f"Erro: {e}")
                if st.button("Voltar"): st.session_state.auth_mode = "login"; st.rerun()

if st.session_state.user is None:
    tela_autenticacao()
    st.stop()

# --- CARREGAMENTO DE DADOS (FORÇADO) ---
user_id = st.session_state.user.id
try:
    # Tenta buscar os dados. Se o user_id falhar por erro de RLS, ele pega o que estiver disponível
    res = supabase.table("lancamentos").select("*").execute()
    full_df = pd.DataFrame(res.data)
    
    if not full_df.empty and 'user_id' in full_df.columns:
        df = full_df[full_df['user_id'] == user_id].copy()
    else:
        df = full_df.copy()
except:
    df = pd.DataFrame()

# Padronização de Colunas Cruciais
if not df.empty:
    for col in ['descricao', 'natureza', 'tipo', 'justificativa', 'categoria_dfc']:
        if col not in df.columns: df[col] = "Não informado"
    if 'valor' not in df.columns: df['valor'] = 0.0
    if 'data_lancamento' not in df.columns:
        df['data_lancamento'] = df['created_at'] if 'created_at' in df.columns else date.today()
    
    # Converte para data real do Python
    df['data_lancamento'] = pd.to_datetime(df['data_lancamento']).dt.date
else:
    df = pd.DataFrame(columns=['id', 'user_id', 'descricao', 'natureza', 'tipo', 'valor', 'justificativa', 'categoria_dfc', 'data_lancamento'])

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"Sessão: {st.session_state.user.email}")
    if st.button("Sair"): st.session_state.user = None; st.rerun()
    st.divider()

    if st.session_state.edit_id:
        st.subheader("📝 Editando")
        it = df[df['id'] == st.session_state.edit_id].iloc[0].to_dict()
    else:
        st.subheader("➕ Novo")
        it = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "categoria_dfc": "Atividade Operacional", "data_lancamento": date.today()}

    with st.form(key=f"f_{st.session_state.form_count}", clear_on_submit=True):
        f_dt = st.date_input("Data", value=pd.to_datetime(it.get('data_lancamento', date.today())))
        f_desc = st.text_input("Conta", value=it.get('descricao', "")).upper()
        f_nat = st.selectbox("Grupo", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(it.get('natureza', 'Ativo')))
        f_dfc = st.selectbox("DFC", ["Atividade Operacional", "Atividade de Investimento", "Atividade de Financiamento", "N/A (Não Financeiro)"], index=["Atividade Operacional", "Atividade de Investimento", "Atividade de Financiamento", "N/A (Não Financeiro)"].index(it.get('categoria_dfc', 'Atividade Operacional')))
        f_tp = st.radio("Tipo", ["Débito", "Crédito"], index=0 if it.get('tipo') == 'Débito' else 1, horizontal=True)
        f_val = st.number_input("Valor", min_value=0.0, value=float(it.get('valor', 0.0)))
        f_hist = st.text_input("Histórico", value=it.get('justificativa', ""))
        
        if st.form_submit_button("Efetivar", type="primary", use_container_width=True):
            payload = {"user_id": user_id, "descricao": f_desc, "natureza": f_nat, "tipo": f_tp, "valor": f_val, "justificativa": f_hist, "categoria_dfc": f_dfc, "data_lancamento": f_dt.strftime('%Y-%m-%d')}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.session_state.form_count += 1
            st.rerun()

# --- NAVEGAÇÃO ---
nav = st.columns(5)
btns = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 DFC", "⚙️ Gestão"]
for i, b in enumerate(btns):
    if nav[i].button(b, use_container_width=True): st.session_state.menu_opcao = b
st.divider()

# --- ABA GESTÃO: MOSTRA TUDO SEM FILTROS ---
if st.session_state.menu_opcao == "⚙️ Gestão":
    st.subheader("⚙️ Manutenção de Registros")
    if df.empty:
        st.info("Nenhum lançamento encontrado para este usuário.")
    else:
        for _, r in df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{r['data_lancamento']} - {r['descricao']}** | R$ {r['valor']:,.2f} ({r['tipo']})")
                if c2.button("✏️", key=f"e_{r['id']}"): st.session_state.edit_id = r['id']; st.rerun()
                if c2.button("🗑️", key=f"d_{r['id']}"): supabase.table("lancamentos").delete().eq("id", r['id']).execute(); st.rerun()
        
        st.divider()
        if st.button("LIMPAR TUDO (RESETAR)"):
            supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
            st.rerun()

# --- OUTRAS ABAS ---
elif not df.empty:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for n in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df[df['natureza'] == n]
            if not df_g.empty:
                st.write(f"### {n}")
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    with cols[i%3]:
                        df_c = df_g[df_g['descricao'] == conta]
                        sd = df_c[df_c['tipo']=='Débito']['valor'].sum() - df_c[df_c['tipo']=='Crédito']['valor'].sum()
                        st.info(f"**{conta}**\nSaldo: R$ {abs(sd):,.2f}")

    elif st.session_state.menu_opcao == "🧾 Balancete":
        # Balancete conforme modelo solicitado anteriormente
        resumo = []
        for c in sorted(df['descricao'].unique()):
            tmp = df[df['descricao'] == c]
            d, cr = tmp[tmp['tipo']=='Débito']['valor'].sum(), tmp[tmp['tipo']=='Crédito']['valor'].sum()
            s = d - cr
            resumo.append({"CONTA": c, "DEBITO": d, "CREDITO": cr, "SALDO DEVEDOR": s if s>0 else 0, "SALDO CREDOR": abs(s) if s<0 else 0})
        st.table(pd.DataFrame(resumo).style.format("{:,.2f}", subset=["DEBITO", "CREDITO", "SALDO DEVEDOR", "SALDO CREDOR"]))

    elif st.session_state.menu_opcao == "📈 DRE":
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        des = df[df['natureza'] == 'Despesa']['valor'].sum()
        st.success(f"**LUCRO LÍQUIDO: R$ {rec - des:,.2f}**")

    elif st.session_state.menu_opcao == "💸 DFC":
        st.subheader("Fluxo de Caixa por Período")
        c1, c2 = st.columns(2)
        d1, d2 = c1.date_input("Início", date(date.today().year, date.today().month, 1)), c2.date_input("Fim", date.today())
        
        df_f = df[(df['categoria_dfc'] != "N/A (Não Financeiro)") & (df['data_lancamento'] >= d1) & (df['data_lancamento'] <= d2)]
        
        if not df_f.empty:
            st.metric("Saldo do Período", f"R$ {df_f[df_f['tipo']=='Débito']['valor'].sum() - df_f[df_f['tipo']=='Crédito']['valor'].sum():,.2f}")
            st.dataframe(df_f[['data_lancamento', 'descricao', 'valor', 'tipo']], use_container_width=True)
        else:
            st.warning("Sem movimentações financeiras neste período.")
else:
    st.info("Nenhum registro encontrado. Use a barra lateral para lançar dados.")
