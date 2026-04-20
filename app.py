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
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")
    elif menu == "Login":
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception:
                st.sidebar.error("Credenciais inválidas.")
    elif menu == "Recuperar Senha":
        if st.sidebar.button("Enviar link"):
            try:
                supabase.auth.reset_password_for_email(email)
                st.sidebar.success("Link enviado!")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")

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
    res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
    return pd.DataFrame(res.data)

df = carregar_dados()

# --- FORMULÁRIO COM NATUREZA DA OPERAÇÃO ---
with st.sidebar:
    st.divider()
    if st.session_state.edit_id:
        st.header("📝 Editar Lançamento")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
        btn_label = "Atualizar"
    else:
        st.header("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.01, "justificativa": "", "natureza_operacao": "Operação Geral"}
        btn_label = "Confirmar"

    with st.form("contabil", clear_on_submit=True):
        # NOVO CAMPO: Natureza da Operação
        natureza_op_list = [
            "Compra de Mercadorias", "Venda de Mercadorias/Serviços", 
            "Pagamento de Despesas", "Recebimento de Clientes", 
            "Integralização de Capital", "Empréstimos/Financiamentos", 
            "Ajustes Contábeis", "Outros"
        ]
        natureza_op = st.selectbox("Natureza da Operação", natureza_op_list, 
                                   index=natureza_op_list.index(item_edit.get('natureza_operacao', "Outros")))
        
        desc = st.text_input("Nome da Conta (Razão)", value=item_edit['descricao']).upper().strip()
        
        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo Contábil", nat_list, index=nat_list.index(item_edit['natureza']))
        
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.01, value=float(item_edit['valor']), format="%.2f")
        just = st.text_area("Histórico / Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button(btn_label, use_container_width=True):
            if desc:
                payload = {
                    "user_id": user_id, 
                    "descricao": desc, 
                    "natureza": nat, 
                    "tipo": tipo, 
                    "valor": valor, 
                    "justificativa": just,
                    "natureza_operacao": natureza_op # Enviando o novo campo
                }
                if st.session_state.edit_id:
                    supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                    st.session_state.edit_id = None
                else:
                    supabase.table("lancamentos").insert(payload).execute()
                st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title("📑 Painel Contábil Digital")

if not df.empty:
    tabs = st.tabs(["📊 Razonetes", "🧾 Balancete", "📈 DRE Interativa", "⚙️ Gestão"])
    
    with tabs[0]: # Razonetes
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            with st.expander(f"📖 {conta} ({df_c['natureza'].iloc[0]})"):
                # Exibindo a natureza da operação na tabela
                st.table(df_c[['natureza_operacao', 'tipo', 'valor', 'justificativa']])

    with tabs[1]: # Balancete
        balancete_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            balancete_data.append({"Conta": conta, "Débito": d, "Crédito": c})
        bal_df = pd.DataFrame(balancete_data)
        st.table(bal_df.style.format({"Débito": "R$ {:.2f}", "Crédito": "R$ {:.2f}"}))
        if round(bal_df["Débito"].sum(), 2) == round(bal_df["Crédito"].sum(), 2):
            st.success("✅ Balancete em Equilíbrio!")
        else:
            st.error("⚠️ Balancete Desequilibrado!")

    with tabs[2]: # DRE
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        desp = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        lucro = rec - desp - enc
        fig = plotly_go.Figure(plotly_go.Waterfall(
            x = ["Receita", "Despesas", "Encargos", "LUCRO"],
            measure = ["relative", "relative", "relative", "total"],
            y = [rec, -desp, -enc, 0]
        ))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[3]: # Gestão
        st.subheader("Gerenciar Lançamentos")
        for idx, row in df.iterrows():
            col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
            # Mostrando a natureza da operação na linha de gestão
            col1.write(f"🏷️ **{row.get('natureza_operacao', 'Op.')}** | {row['descricao']} | R$ {row['valor']:.2f}")
            
            if col2.button("Editar", key=f"edit_{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if col3.button("Excluir", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Aguardando lançamentos.")
