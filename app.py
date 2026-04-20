import streamlit as st
import pandas as pd
import subprocess
import sys
import os

# --- GARANTIA DE INSTALAÇÃO ---
def install_and_import(package):
    try:
        return __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return __import__(package)

plotly_go = install_and_import("plotly").graph_objects
from supabase import create_client, Client

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema Contábil Integrado", layout="wide")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets.")
    st.stop()

# --- ESTADOS DO SISTEMA ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

# --- AUTENTICAÇÃO ---
def gerenciar_acesso():
    st.sidebar.title("🔐 Acesso")
    menu = st.sidebar.radio("Escolha", ["Login", "Criar Conta", "Recuperar Senha"])
    email = st.sidebar.text_input("E-mail").lower().strip()
    if menu == "Criar Conta":
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada! Tente logar.")
            except Exception as e: st.sidebar.error(f"Erro: {e}")
    elif menu == "Login":
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception: st.sidebar.error("Credenciais inválidas.")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

# --- PÓS-LOGIN ---
user_id = st.session_state.user.id
st.sidebar.write(f"👤 Logado: **{st.session_state.user.email}**")
if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

def carregar_dados():
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
        return pd.DataFrame(res.data)
    except Exception: return pd.DataFrame()

df = carregar_dados()

# --- FORMULÁRIO COM ENCARGOS FINANCEIROS ---
with st.sidebar:
    st.divider()
    if st.session_state.edit_id:
        st.header("📝 Editar")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.01, "justificativa": "", "natureza_operacao": "Outros"}

    with st.form("contabil", clear_on_submit=True):
        # LISTA DE NATUREZAS ATUALIZADA
        nat_op_list = [
            "Integralização de Capital Social",
            "Venda de Mercadorias/Serviços",
            "Compra de Mercadorias/Bens",
            "Pagamento de Fornecedores",
            "Recebimento de Clientes",
            "Pagamento de Salários/Encargos Sociais",
            "Pagamento de Impostos/Contribuições",
            "Pagamento de Aluguel/Utilitários",
            "Pagamento de Juros/Multas (Encargos Financeiros)", # Adicionado
            "Tarifas e Taxas Bancárias (Encargos Financeiros)",   # Adicionado
            "Variações Monetárias Passivas (Encargos Financeiros)", # Adicionado
            "Recebimento de Receitas Financeiras",
            "Amortização de Empréstimos",
            "Distribuição de Lucros",
            "Depreciação/Amortização",
            "Outros"
        ]
        
        idx_op = nat_op_list.index(item_edit['natureza_operacao']) if item_edit.get('natureza_operacao') in nat_op_list else 15
        
        natureza_op = st.selectbox("Natureza da Operação", nat_op_list, index=idx_op)
        desc = st.text_input("Nome da Conta", value=item_edit['descricao']).upper().strip()
        
        # Grupos Contábeis
        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo (Natureza)", nat_list, index=nat_list.index(item_edit['natureza']))
        
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.01, value=float(item_edit['valor']))
        just = st.text_area("Justificativa/Histórico", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just, "natureza_operacao": natureza_op}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.rerun()

# --- INTERFACE ---
st.title("📑 Painel Contábil Digital")

if not df.empty:
    t = st.tabs(["📊 Razonetes", "🧾 Balancete", "📈 DRE", "⚙️ Gestão"])
    
    with t[0]: # Razonetes
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            with st.expander(f"📖 {conta} ({df_c['natureza'].iloc[0]})"):
                st.table(df_c[['natureza_operacao', 'tipo', 'valor', 'justificativa']])

    with t[1]: # Balancete
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c})
        st.table(pd.DataFrame(bal_data))
        if round(sum(i['Débito'] for i in bal_data),2) == round(sum(i['Crédito'] for i in bal_data),2):
            st.success("✅ Balancete Equilibrado")

    with t[2]: # DRE
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        desp = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        lucro = rec - desp - enc
        
        st.metric("Lucro/Prejuízo Líquido", f"R$ {lucro:,.2f}")
        fig = plotly_go.Figure(plotly_go.Waterfall(
            x=["Receita", "Despesas", "Encargos", "LUCRO"], 
            y=[rec, -desp, -enc, 0], 
            measure=["relative", "relative", "relative", "total"]
        ))
        st.plotly_chart(fig, use_container_width=True)

    with t[3]: # Gestão
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            tag = "🔴" if row['tipo'] == "Crédito" else "🔵"
            c1.write(f"**{row['descricao']}** | {row['natureza']} ({tag} {row['tipo'][0]})")
            c1.caption(f"Op: {row.get('natureza_operacao', 'Outros')} | R$ {row['valor']:,.2f}")
            if c2.button("Editar", key=f"e_{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("Excluir", key=f"d_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
            st.divider()
else:
    st.info("Aguardando lançamentos...")
