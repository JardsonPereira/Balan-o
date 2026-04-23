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

from supabase import create_client, Client

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema Contábil Integrado", layout="wide")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets no Streamlit Cloud.")
    st.stop()

# --- ESTADOS DO SISTEMA ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None
if 'form_count' not in st.session_state:
    st.session_state.form_count = 0
if 'menu_opcao' not in st.session_state:
    st.session_state.menu_opcao = "📊 Razonetes"

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
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        
        idx_conta = 0
        if st.session_state.edit_id and item_edit['descricao'] in contas_existentes:
            idx_conta = opcoes_conta.index(item_edit['descricao'])
            
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        desc = st.text_input("Nome da Conta", value=item_edit['descricao']).upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel

        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar Lançamento"):
            if not desc or desc == "+ Adicionar Nova Conta":
                st.error("Informe o nome da conta!")
            else:
                payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
                try:
                    if st.session_state.edit_id:
                        supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                        st.session_state.edit_id = None
                    else:
                        supabase.table("lancamentos").insert(payload).execute()
                    st.session_state.form_count += 1
                    st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

# --- CSS INTEGRADO ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }
    div.stButton > button {
        border-radius: 8px; border: 1px solid #e2e8f0; background-color: white;
        transition: all 0.3s ease; font-weight: 600; color: #475569;
    }
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 24px; overflow: hidden; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 12px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; }
    .conta-corpo { display: flex; min-height: 100px; position: relative; }
    .conta-corpo::after { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background-color: #cbd5e1; }
    .lado-debito, .lado-credito { flex: 1; padding: 10px; }
    .valor-item { font-size: 0.8rem; margin-bottom: 4px; padding: 2px 6px; border-radius: 4px; }
    .valor-deb { color: #059669; background: #ecfdf5; border-left: 3px solid #10b981; }
    .valor-cre { color: #dc2626; background: #fef2f2; border-right: 3px solid #ef4444; text-align: right; }
    .conta-rodape { padding: 8px; background: #f1f5f9; border-top: 1px solid #1e293b; text-align: center; font-weight: 700; font-size: 0.85rem; }
    .grupo-header { background: #334155; color: white; padding: 8px 16px; border-radius: 6px; margin: 20px 0 10px 0; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- CONTEÚDO PRINCIPAL ---
st.title("📑 Sistema Contábil Digital")

col_nav = st.columns(4)
if col_nav[0].button("📊 Razonetes", use_container_width=True): st.session_state.menu_opcao = "📊 Razonetes"
if col_nav[1].button("🧾 Balancete", use_container_width=True): st.session_state.menu_opcao = "🧾 Balancete"
if col_nav[2].button("📈 DRE", use_container_width=True): st.session_state.menu_opcao = "📈 DRE"
if col_nav[3].button("⚙️ Gestão", use_container_width=True): st.session_state.menu_opcao = "⚙️ Gestão"

st.divider()

if not df.empty:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for grupo in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df[df['natureza'] == grupo]
            if not df_g.empty:
                st.markdown(f"<div class='grupo-header'>{grupo.upper()}</div>", unsafe_allow_html=True)
                cols = st.columns(3)
                for idx, conta in enumerate(sorted(df_g['descricao'].unique())):
                    with cols[idx % 3]:
                        df_c = df_g[df_g['descricao'] == conta]
                        v_deb = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        v_cre = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        saldo = v_deb - v_cre
                        
                        deb_h = "".join([f"<div class='valor-item valor-deb'>{r['valor']:,.2f}</div>" for _,r in df_c[df_c['tipo']=='Débito'].iterrows()])
                        cre_h = "".join([f"<div class='valor-item valor-cre'>{r['valor']:,.2f}</div>" for _,r in df_c[df_c['tipo']=='Crédito'].iterrows()])
                        
                        st.markdown(f"""
                            <div class="conta-card">
                                <div class="conta-titulo">{conta}</div>
                                <div class="conta-corpo"><div class="lado-debito">{deb_h}</div><div class="lado-credito">{cre_h}</div></div>
                                <div class="conta-rodape">SALDO: R$ {abs(saldo):,.2f} {'(D)' if saldo >=0 else '(C)'}</div>
                            </div>
                        """, unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("Balancete de Verificação")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c, "Saldo": d-c})
        st.dataframe(pd.DataFrame(bal_data), use_container_width=True)

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("Resultado")
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        des = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        st.metric("Lucro Líquido", f"R$ {rec - des - enc:,.2f}")

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("Histórico de Lançamentos")
        st.dataframe(df[['descricao', 'natureza', 'tipo', 'valor', 'justificativa']], use_container_width=True)
        if st.button("Limpar Dados"):
            supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
            st.rerun()
else:
    st.info("Nenhum dado encontrado.")
