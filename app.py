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
    menu = st.sidebar.radio("Escolha", ["Login", "Criar Conta"])
    email = st.sidebar.text_input("E-mail").lower().strip()
    if menu == "Login":
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception: st.sidebar.error("Erro no login.")
    else:
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada!")
            except Exception as e: st.sidebar.error(f"Erro: {e}")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

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

# --- FORMULÁRIO ---
with st.sidebar:
    st.divider()
    if st.session_state.edit_id:
        st.header("📝 Editar")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.01, "justificativa": "", "natureza_operacao": "Outros"}

    with st.form("contabil", clear_on_submit=True):
        nat_op_list = ["Integralização de Capital", "Venda de Mercadorias/Serviços", "Compra de Mercadorias/Bens", "Pagamento de Fornecedores", "Recebimento de Clientes", "Pagamento de Salários/Encargos", "Pagamento de Juros/Multas", "Outros"]
        natureza_op = st.selectbox("Natureza da Operação", nat_op_list)
        desc = st.text_input("Nome da Conta", value=item_edit['descricao']).upper().strip()
        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.01, value=float(item_edit['valor']))
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
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
    t = st.tabs(["📊 Razonetes", "🧾 Balancete de Saldos", "📈 DRE", "⚙️ Gestão"])
    
    with t[0]: # Razonetes
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            with st.expander(f"📖 {conta}"):
                st.table(df_c[['tipo', 'valor', 'justificativa']])

    with t[1]: # BALANCETE ATUALIZADO COM SALDOS DEVEDOR E CREDOR
        st.subheader("Balancete de Verificação (Saldos Finais)")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            total_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            total_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            
            # Cálculo do Saldo Final
            saldo_devedor = 0.0
            saldo_credor = 0.0
            
            if total_d > total_c:
                saldo_devedor = total_d - total_c
            elif total_c > total_d:
                saldo_credor = total_c - total_d
            
            bal_data.append({
                "Conta": conta,
                "Grupo": df_c['natureza'].iloc[0],
                "Saldo Devedor": saldo_devedor,
                "Saldo Credor": saldo_credor
            })
        
        bal_df = pd.DataFrame(bal_data)
        
        # Exibição da Tabela
        st.table(bal_df.style.format({"Saldo Devedor": "R$ {:.2f}", "Saldo Credor": "R$ {:.2f}"}))
        
        # Totais para conferência
        sum_d = bal_df["Saldo Devedor"].sum()
        sum_c = bal_df["Saldo Credor"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Total Saldo Devedor", f"R$ {sum_d:,.2f}")
        c2.metric("Total Saldo Credor", f"R$ {sum_c:,.2f}")
        
        if round(sum_d, 2) == round(sum_c, 2):
            st.success("✅ Balancete em Equilíbrio!")
        else:
            st.error("⚠️ Balancete Desequilibrado! Revise os lançamentos.")

    with t[2]: # DRE
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        desp = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        lucro = rec - desp - enc
        fig = plotly_go.Figure(plotly_go.Waterfall(x=["Receita", "Despesas", "Encargos", "LUCRO"], y=[rec, -desp, -enc, 0], measure=["relative", "relative", "relative", "total"]))
        st.plotly_chart(fig, use_container_width=True)

    with t[3]: # Gestão
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            tag = "🔵 D" if row['tipo'] == "Débito" else "🔴 C"
            c1.write(f"**{row['descricao']}** | {row['natureza']} ({tag})")
            if c2.button("Editar", key=f"ed_{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("Excluir", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Sem dados.")
