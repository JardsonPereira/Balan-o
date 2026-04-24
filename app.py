import streamlit as st
import pandas as pd
import subprocess
import sys
from supabase import create_client, Client

# --- GARANTIA DE INSTALAÇÃO ---
def install_and_import(package):
    try:
        return __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return __import__(package)

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

def carregar_dados():
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
        temp_df = pd.DataFrame(res.data)
        # SEGURANÇA: Se a coluna 'status' não existir no banco, cria ela no DataFrame
        if not temp_df.empty and 'status' not in temp_df.columns:
            temp_df['status'] = 'Pago'
        return temp_df
    except Exception: return pd.DataFrame()

df = carregar_dados()

# --- FORMULÁRIO COM STATUS FINANCEIRO ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.user.email}**")
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df.empty:
        st.header("📝 Editar")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago"}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Nova Conta"] + contas_existentes
        idx_conta = opcoes_conta.index(item_edit['descricao']) if st.session_state.edit_id and item_edit['descricao'] in contas_existentes else 0
        
        conta_sel = st.selectbox("Conta", opcoes_conta, index=idx_conta)
        desc = st.text_input("Nome", value="").upper().strip() if conta_sel == "+ Nova Conta" else conta_sel

        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        status_pag = st.selectbox("Financeiro", ["Pago", "Pendente"], index=0 if item_edit.get('status') == "Pago" else 1)
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just, "status": status_pag}
            try:
                if st.session_state.edit_id:
                    supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                    st.session_state.edit_id = None
                else:
                    supabase.table("lancamentos").insert(payload).execute()
                st.session_state.form_count += 1
                st.rerun()
            except Exception as e: st.error(f"Erro: {e}")

# --- CSS ---
st.markdown("""<style>
    .stApp { background-color: #f8fafc; }
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; border-radius: 12px 12px 0 0; }
    .conta-corpo { display: flex; min-height: 50px; position: relative; }
    .conta-corpo::after { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background-color: #cbd5e1; }
    .lado-debito, .lado-credito { flex: 1; padding: 10px; font-size: 0.8rem; }
    .conta-rodape { padding: 8px; background: #f1f5f9; text-align: center; font-weight: 700; border-radius: 0 0 12px 12px; }
</style>""", unsafe_allow_html=True)

st.title("📑 Sistema Contábil Digital")

# --- DASHBOARD DE MÉTRICAS ---
if not df.empty:
    # Liquidez e Caixa
    ac = df[(df['natureza'] == 'Ativo') & (df['tipo'] == 'Débito')]['valor'].sum() - df[(df['natureza'] == 'Ativo') & (df['tipo'] == 'Crédito')]['valor'].sum()
    pc = df[(df['natureza'] == 'Passivo') & (df['tipo'] == 'Crédito')]['valor'].sum() - df[(df['natureza'] == 'Passivo') & (df['tipo'] == 'Débito')]['valor'].sum()
    entradas = df[(df['status'] == 'Pago') & (df['tipo'] == 'Débito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    saidas = df[(df['status'] == 'Pago') & (df['tipo'] == 'Crédito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Saldo Caixa", f"R$ {entradas - saidas:,.2f}")
    m2.metric("Liquidez Corrente", f"{ac/pc:.2f}" if pc != 0 else "0.00")
    m3.metric("Ativo (AC)", f"R$ {ac:,.2f}")
    m4.metric("Passivo (PC)", f"R$ {pc:,.2f}")

# --- NAVEGAÇÃO ---
col_nav = st.columns(5)
opcoes = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()

# --- TELAS ---
if df.empty:
    st.info("Nenhum lançamento encontrado.")
else:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for grupo in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"]:
            df_g = df[df['natureza'] == grupo]
            if not df_g.empty:
                st.subheader(grupo)
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    with cols[i % 3]:
                        df_c = df_g[df_g['descricao'] == conta]
                        v_deb, v_cre = df_c[df_c['tipo']=='Débito']['valor'].sum(), df_c[df_c['tipo']=='Crédito']['valor'].sum()
                        saldo = v_deb - v_cre if grupo in ["Ativo", "Despesa"] else v_cre - v_deb
                        st.markdown(f"""<div class="conta-card"><div class="conta-titulo">{conta}</div>
                            <div class="conta-corpo"><div class="lado-debito">D: {v_deb:,.2f}</div><div class="lado-credito">C: {v_cre:,.2f}</div></div>
                            <div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>""", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("Regime de Caixa (Apenas Pagos)")
        df_pago = df[df['status'] == 'Pago']
        st.dataframe(df_pago[['descricao', 'tipo', 'valor', 'justificativa']], use_container_width=True)

    elif st.session_state.menu_opcao == "📈 DRE":
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        des = df[df['natureza'] == 'Despesa']['valor'].sum()
        st.success(f"**Resultado Líquido: R$ {rec - des:,.2f}**")

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        for _, row in df.iterrows():
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.write(f"{row['descricao']} | R$ {row['valor']:,.2f} ({row['status']})")
            if c2.button("✏️", key=f"ed{row['id']}"): st.session_state.edit_id = row['id']; st.rerun()
            if c3.button("🗑️", key=f"del{row['id']}"): supabase.table("lancamentos").delete().eq("id", row['id']).execute(); st.rerun()
