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

# --- FORMULÁRIO ATUALIZADO ---
with st.sidebar:
    st.divider()
    if st.session_state.edit_id:
        st.header("📝 Editar")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago"}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        idx_conta = opcoes_conta.index(item_edit['descricao']) if st.session_state.edit_id and item_edit['descricao'] in contas_existentes else 0
        
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        desc = st.text_input("Nome da Conta", value="").upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel

        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        
        # NOVO: Status de Pagamento para Fluxo de Caixa
        status_pag = st.selectbox("Status Financeiro", ["Pago", "Pendente"], index=0 if item_edit.get('status') == "Pago" else 1)
        
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar Lançamento"):
            if not desc: st.error("Informe a conta!")
            else:
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

# --- CSS PREMIUM ---
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; border-radius: 12px 12px 0 0; }
    .conta-corpo { display: flex; min-height: 60px; position: relative; }
    .conta-corpo::after { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background-color: #cbd5e1; }
    .lado-debito, .lado-credito { flex: 1; padding: 10px; font-size: 0.85rem; }
    .valor-deb { color: #059669; font-weight: 600; }
    .valor-cre { color: #dc2626; font-weight: 600; text-align: right; }
    .conta-rodape { padding: 8px; background: #f1f5f9; text-align: center; font-weight: 700; border-radius: 0 0 12px 12px; }
</style>
""", unsafe_allow_html=True)

# --- INTERFACE PRINCIPAL ---
st.title("📑 Sistema Contábil Digital")

# Cálculo de Indicadores (Dashboard de Topo)
if not df.empty:
    # Liquidez
    ac = df[(df['natureza'] == 'Ativo') & (df['tipo'] == 'Débito')]['valor'].sum() - df[(df['natureza'] == 'Ativo') & (df['tipo'] == 'Crédito')]['valor'].sum()
    pc = df[(df['natureza'] == 'Passivo') & (df['tipo'] == 'Crédito')]['valor'].sum() - df[(df['natureza'] == 'Passivo') & (df['tipo'] == 'Débito')]['valor'].sum()
    liq_corrente = ac / pc if pc != 0 else 0
    
    # Caixa (Somente o que está 'Pago')
    entradas = df[(df['status'] == 'Pago') & (df['tipo'] == 'Débito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    saidas = df[(df['status'] == 'Pago') & (df['tipo'] == 'Crédito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    saldo_caixa = entradas - saidas

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Saldo em Caixa", f"R$ {saldo_caixa:,.2f}")
    m2.metric("Liquidez Corrente", f"{liq_corrente:.2f}")
    m3.metric("Ativo Circulante", f"R$ {ac:,.2f}")
    m4.metric("Passivo Circulante", f"R$ {pc:,.2f}")

# Menu de navegação
col_nav = st.columns(5)
opcoes = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()

if not df.empty:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for grupo in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"]:
            df_g = df[df['natureza'] == grupo]
            if not df_g.empty:
                st.subheader(grupo)
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    with cols[i % 3]:
                        df_c = df_g[df_g['descricao'] == conta]
                        v_deb = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        v_cre = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        saldo = v_deb - v_cre if grupo in ["Ativo", "Despesa"] else v_cre - v_deb
                        
                        st.markdown(f"""<div class="conta-card"><div class="conta-titulo">{conta}</div>
                            <div class="conta-corpo">
                                <div class="lado-debito">{"".join([f"<div class='valor-deb'>D: {r['valor']:,.2f}</div>" for _,r in df_c[df_c['tipo']=='Débito'].iterrows()])}</div>
                                <div class="lado-credito">{"".join([f"<div class='valor-cre'>C: {r['valor']:,.2f}</div>" for _,r in df_c[df_c['tipo']=='Crédito'].iterrows()])}</div>
                            </div><div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>""", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("Movimentação de Caixa (Efetivada)")
        df_caixa = df[df['status'] == 'Pago'].copy()
        if not df_caixa.empty:
            st.dataframe(df_caixa[['descricao', 'tipo', 'valor', 'justificativa']], use_container_width=True)
            st.info(f"O saldo atual disponível (Regime de Caixa) é de **R$ {saldo_caixa:,.2f}**")
        else:
            st.warning("Nenhum lançamento marcado como 'Pago'.")

    elif st.session_state.menu_opcao == "📈 DRE":
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        des = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        st.write(f"**Receita Bruta:** R$ {rec:,.2f}")
        st.write(f"**(-) Despesas:** R$ {des:,.2f}")
        st.success(f"**Lucro/Prejuízo Líquido:** R$ {rec - des - enc:,.2f}")

    elif st.session_state.menu_opcao == "🧾 Balancete":
        # Lógica de Balancete existente...
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c, "Saldo": d-c})
        st.table(pd.DataFrame(bal_data))

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("Editar ou Excluir")
        for _, row in df.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['descricao']}** - R$ {row['valor']:,.2f} ({row['status']})")
            if c2.button("✏️", key=f"e_{row['id']}"): 
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("🗑️", key=f"d_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()

else:
    st.info("Adicione o primeiro lançamento na barra lateral para começar.")
