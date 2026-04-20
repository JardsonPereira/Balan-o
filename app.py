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
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta)
        
        if conta_sel == "+ Adicionar Nova Conta":
            desc = st.text_input("Nome da Nova Conta").upper().strip()
        else:
            desc = conta_sel

        nat_op_list = [
            "Integralização de Capital", "Venda de Mercadorias/Serviços", 
            "Compra de Mercadorias/Bens", "Pagamento de Salários", 
            "Pagamento de Juros/Multas (Encargos Financeiros)", 
            "Tarifas Bancárias (Encargos Financeiros)", "Outros"
        ]
        natureza_op = st.selectbox("Natureza da Operação", nat_op_list)
        
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
st.title("📑 Sistema Contábil Digital")

if not df.empty:
    t = st.tabs(["📊 Razonetes", "🧾 Balancete", "📈 DRE", "⚙️ Gestão"])
    
    with t[0]: # Razonetes
        cols = st.columns(3)
        for i, conta in enumerate(sorted(df['descricao'].unique())):
            with cols[i % 3]:
                df_c = df[df['descricao'] == conta]
                st.markdown(f"<div style='text-align:center; font-weight:bold; border-bottom:2px solid black;'>{conta}</div>", unsafe_allow_html=True)
                c_d, c_c = st.columns(2)
                for v in df_c[df_c['tipo'] == 'Débito']['valor']: c_d.write(f"D: {v:,.2f}")
                for v in df_c[df_c['tipo'] == 'Crédito']['valor']: c_c.write(f"C: {v:,.2f}")

    with t[1]: # Balancete
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Devedor": d-c if d>c else 0, "Credor": c-d if c>d else 0})
        st.table(pd.DataFrame(bal_data))

    with t[2]: # DRE SEM GRÁFICOS
        st.subheader("Demonstração do Resultado (DRE)")
        
        receita = df[df['natureza'] == 'Receita']['valor'].sum()
        despesa = df[df['natureza'] == 'Despesa']['valor'].sum()
        encargos = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        lucro = receita - despesa - encargos
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receita Bruta", f"R$ {receita:,.2f}")
        c2.metric("Despesas Adm.", f"R$ {despesa:,.2f}")
        c3.metric("Encargos Fin.", f"R$ {encargos:,.2f}")
        c4.metric("Resultado Líquido", f"R$ {lucro:,.2f}")

        st.divider()
        st.write("**Análise Vertical (Percentual em relação à Receita)**")
        
        if receita > 0:
            dre_final = pd.DataFrame([
                {"Descrição": "RECEITA OPERACIONAL BRUTA", "Valor": receita, "%": "100.00%"},
                {"Descrição": "(-) DESPESAS ADMINISTRATIVAS", "Valor": despesa, "%": f"{(despesa/receita)*100:.2f}%"},
                {"Descrição": "(-) ENCARGOS FINANCEIROS", "Valor": encargos, "%": f"{(encargos/receita)*100:.2f}%"},
                {"Descrição": "(=) LUCRO/PREJUÍZO LÍQUIDO", "Valor": lucro, "%": f"{(lucro/receita)*100:.2f}%"}
            ])
            st.table(dre_final.style.format({"Valor": "R$ {:.2f}"}))
        else:
            st.warning("Lance uma 'Receita' para visualizar a análise percentual.")

    with t[3]: # Gestão
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            c1.write(f"**{row['descricao']}** | {row['natureza']} | R$ {row['valor']:.2f}")
            if c2.button("Editar", key=f"ed_{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("Excluir", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Aguardando lançamentos.")
