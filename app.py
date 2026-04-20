import streamlit as st
import pandas as pd
import subprocess
import sys

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
    st.error("Erro de conexão. Verifique as Secrets do Supabase.")
    st.stop()

# --- ESTADOS DO SISTEMA ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

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
            except Exception: st.sidebar.error("Credenciais inválidas.")
    else:
        if st.sidebar.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada!")
            except Exception as e: st.sidebar.error(f"Erro: {e}")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

# --- CARREGAMENTO DE DADOS ---
user_id = st.session_state.user.id
st.sidebar.write(f"👤 **{st.session_state.user.email}**")
if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

def carregar_dados():
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
        return pd.DataFrame(res.data)
    except Exception: return pd.DataFrame()

df = carregar_dados()

# --- FORMULÁRIO COM CONTAS EXISTENTES ---
with st.sidebar:
    st.divider()
    if st.session_state.edit_id:
        st.header("📝 Editar")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.01, "justificativa": "", "natureza_operacao": "Outros"}

    with st.form("form_contabil", clear_on_submit=True):
        # NATUREZA DA OPERAÇÃO
        nat_op_list = ["Integralização de Capital", "Venda de Mercadorias/Serviços", "Compra de Mercadorias/Bens", "Pagamento de Fornecedores", "Recebimento de Clientes", "Pagamento de Salários/Encargos", "Pagamento de Juros/Multas (Encargos Financeiros)", "Outros"]
        natureza_op = st.selectbox("Natureza da Operação", nat_op_list)

        # LÓGICA DE SELEÇÃO DE CONTAS EXISTENTES
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        
        # Se estiver editando, tenta pré-selecionar a conta correta
        idx_conta = 0
        if item_edit['descricao'] in contas_existentes:
            idx_conta = opcoes_conta.index(item_edit['descricao'])
            
        conta_selecionada = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        
        # Campo de texto que aparece apenas se "Adicionar Nova" for selecionado ou se estiver editando
        desc_nova = ""
        if conta_selecionada == "+ Adicionar Nova Conta":
            desc_nova = st.text_input("Nome da Nova Conta (Ex: CAIXA)").upper().strip()
        else:
            desc_nova = conta_selecionada

        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo Contábil", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.01, value=float(item_edit['valor']))
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("💾 Salvar"):
            if desc_nova:
                payload = {"user_id": user_id, "descricao": desc_nova, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just, "natureza_operacao": natureza_op}
                if st.session_state.edit_id:
                    supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                    st.session_state.edit_id = None
                else:
                    supabase.table("lancamentos").insert(payload).execute()
                st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title("📑 Sistema Contábil Pedagógico")

if not df.empty:
    tab_raz, tab_bal, tab_ges = st.tabs(["📊 Razonetes", "🧾 Balancete", "⚙️ Gestão"])
    
    with tab_raz:
        cols = st.columns(3)
        for i, conta in enumerate(sorted(df['descricao'].unique())):
            with cols[i % 3]:
                df_c = df[df['descricao'] == conta]
                st.markdown(f"<div style='border-bottom: 2px solid black; text-align: center; font-weight: bold; background-color: #f0f2f6;'>{conta}</div>", unsafe_allow_html=True)
                c_d, c_c = st.columns(2)
                c_d.markdown("<p style='text-align: center; color: blue; font-size: 10px;'>D</p>", unsafe_allow_html=True)
                for v in df_c[df_c['tipo'] == 'Débito']['valor']: c_d.write(f"{v:,.2f}")
                c_c.markdown("<p style='text-align: center; color: red; font-size: 10px;'>C</p>", unsafe_allow_html=True)
                for v in df_c[df_c['tipo'] == 'Crédito']['valor']: c_c.write(f"{v:,.2f}")
                
                s = df_c[df_c['tipo'] == 'Débito']['valor'].sum() - df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                st.divider()
                st.write(f"**Saldo: R$ {abs(s):,.2f} ({'D' if s >= 0 else 'C'})**")

    with tab_bal:
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            t_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            t_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Devedor": t_d - t_c if t_d > t_c else 0, "Credor": t_c - t_d if t_c > t_d else 0})
        st.table(pd.DataFrame(bal_data))

    with tab_ges:
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            c1.write(f"**{row['descricao']}** | {row['tipo']} | R$ {row['valor']:.2f}")
            if c2.button("Editar", key=f"e_{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("Excluir", key=f"d_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Aguardando lançamentos.")
