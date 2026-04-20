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
    st.sidebar.title("🔐 Acesso ao Sistema")
    menu = st.sidebar.radio("Escolha", ["Login", "Criar Conta"])
    email = st.sidebar.text_input("E-mail").lower().strip()
    senha = st.sidebar.text_input("Senha", type="password")

    if menu == "Login":
        if st.sidebar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception: st.sidebar.error("E-mail ou senha incorretos.")
    else:
        if st.sidebar.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada! Agora faça o login.")
            except Exception as e: st.sidebar.error(f"Erro: {e}")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

# --- CARREGAMENTO DE DADOS ---
user_id = st.session_state.user.id
st.sidebar.write(f"👤 Usuário: **{st.session_state.user.email}**")
if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

def carregar_dados():
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
        return pd.DataFrame(res.data)
    except Exception: return pd.DataFrame()

df = carregar_dados()

# --- FORMULÁRIO DE LANÇAMENTO (SALVAR) ---
with st.sidebar:
    st.divider()
    if st.session_state.edit_id:
        st.header("📝 Editar Lançamento")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.01, "justificativa": "", "natureza_operacao": "Outros"}

    with st.form("form_contabil", clear_on_submit=True):
        nat_op_list = ["Integralização de Capital", "Venda de Mercadorias/Serviços", "Compra de Mercadorias/Bens", "Pagamento de Fornecedores", "Recebimento de Clientes", "Pagamento de Salários/Encargos", "Encargos Financeiros", "Outros"]
        natureza_op = st.selectbox("Natureza da Operação", nat_op_list)
        
        desc = st.text_input("Nome da Conta (Ex: BANCO)", value=item_edit['descricao']).upper().strip()
        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo Contábil", nat_list, index=nat_list.index(item_edit['natureza']))
        
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.01, value=float(item_edit['valor']), format="%.2f")
        just = st.text_area("Histórico/Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("💾 Salvar Lançamento"):
            if desc:
                payload = {
                    "user_id": user_id, "descricao": desc, "natureza": nat, 
                    "tipo": tipo, "valor": valor, "justificativa": just, 
                    "natureza_operacao": natureza_op
                }
                if st.session_state.edit_id:
                    supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                    st.session_state.edit_id = None
                else:
                    supabase.table("lancamentos").insert(payload).execute()
                st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title("📚 Sistema Contábil Pedagógico")

if not df.empty:
    tab_razonete, tab_balancete, tab_gestao = st.tabs(["📊 Razonetes", "🧾 Balancete", "⚙️ Gestão"])
    
    with tab_razonete:
        st.subheader("Livro Razão (Razonetes)")
        # Criar colunas para organizar os razonetes em grid
        col_count = 0
        cols = st.columns(3)
        
        for conta in sorted(df['descricao'].unique()):
            with cols[col_count % 3]:
                df_c = df[df['descricao'] == conta]
                
                # Cabeçalho do Razonete
                st.markdown(f"""
                    <div style="border-bottom: 2px solid black; text-align: center; font-weight: bold; background-color: #f0f2f6; padding: 5px;">
                        {conta}
                    </div>
                """, unsafe_allow_html=True)
                
                # Corpo do Razonete (Débito e Crédito)
                deb_df = df_c[df_c['tipo'] == 'Débito']
                cre_df = df_c[df_c['tipo'] == 'Crédito']
                
                c_deb, c_cre = st.columns(2)
                with c_deb:
                    st.markdown("<p style='text-align: center; color: blue; font-size: 12px;'>Débito</p>", unsafe_allow_html=True)
                    for v in deb_df['valor']: st.write(f"R$ {v:,.2f}")
                with c_cre:
                    st.markdown("<p style='text-align: center; color: red; font-size: 12px;'>Crédito</p>", unsafe_allow_html=True)
                    for v in cre_df['valor']: st.write(f"R$ {v:,.2f}")
                
                # Saldo Final do Razonete
                total_d = deb_df['valor'].sum()
                total_c = cre_df['valor'].sum()
                saldo = total_d - total_c
                
                st.markdown("---")
                if saldo >= 0:
                    st.write(f"**Saldo Devedor: R$ {saldo:,.2f}**")
                else:
                    st.write(f"**Saldo Credor: R$ {abs(saldo):,.2f}**")
                st.write("") # Espaçamento
            col_count += 1

    with tab_balancete:
        # Lógica do Balancete (conforme sua solicitação anterior)
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            t_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            t_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            s_d = t_d - t_c if t_d > t_c else 0
            s_c = t_c - t_d if t_c > t_d else 0
            bal_data.append({"Conta": conta, "Devedor": s_d, "Credor": s_c})
        st.table(pd.DataFrame(bal_data).style.format({"Devedor": "R$ {:.2f}", "Credor": "R$ {:.2f}"}))

    with tab_gestao:
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
    st.info("💡 Faça seu primeiro lançamento no menu lateral para gerar os razonetes!")
