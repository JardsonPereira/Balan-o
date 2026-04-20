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

# --- FORMULÁRIO (PRESERVADO) ---
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
        
        desc = st.text_input("Nome da Nova Conta").upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel

        nat_op_list = [
            "Integralização de Capital Social", "Venda de Mercadorias/Serviços", 
            "Compra de Mercadorias/Bens", "Pagamento de Salários/Encargos", 
            "Pagamento de Juros/Multas (Encargos Financeiros)", 
            "Tarifas e Taxas Bancárias (Encargos Financeiros)", "Outros"
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
    
    with t[0]: # Razonetes com resultado (Preservado)
        cols = st.columns(3)
        for i, conta in enumerate(sorted(df['descricao'].unique())):
            with cols[i % 3]:
                df_c = df[df['descricao'] == conta]
                st.markdown(f"<div style='text-align:center; font-weight:bold; border-bottom:2px solid black; background-color:#f8f9fa;'>{conta}</div>", unsafe_allow_html=True)
                c_d, c_c = st.columns(2)
                v_deb = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                v_cre = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                for v in df_c[df_c['tipo'] == 'Débito']['valor']: c_d.write(f"D: {v:,.2f}")
                for v in df_c[df_c['tipo'] == 'Crédito']['valor']: c_c.write(f"C: {v:,.2f}")
                st.markdown("<div style='border-top:1px solid gray;'></div>", unsafe_allow_html=True)
                saldo = v_deb - v_cre
                if saldo > 0: st.markdown(f"**Saldo D: R$ {saldo:,.2f}**")
                elif saldo < 0: st.markdown(f"**Saldo C: R$ {abs(saldo):,.2f}**")
                else: st.write("Conta Zerada")

    with t[1]: # Balancete com Somas Devedoras e Credoras (Solicitado)
        st.subheader("Balancete de Verificação de Saldos")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Saldo Devedor": d-c if d>c else 0, "Saldo Credor": c-d if c>d else 0})
        
        bal_df = pd.DataFrame(bal_data)
        st.table(bal_df.style.format({"Saldo Devedor": "R$ {:.2f}", "Saldo Credor": "R$ {:.2f}"}))
        
        # Somas Finais do Balancete
        total_dev = bal_df["Saldo Devedor"].sum()
        total_cre = bal_df["Saldo Credor"].sum()
        
        col_b1, col_b2 = st.columns(2)
        col_b1.metric("Total Saldos Devedores", f"R$ {total_dev:,.2f}")
        col_b2.metric("Total Saldos Credores", f"R$ {total_cre:,.2f}")
        if round(total_dev, 2) == round(total_cre, 2): st.success("✅ Balancete Equilibrado")
        else: st.error("⚠️ Diferença detectada no Balancete")

    with t[2]: # DRE (Preservada)
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        des = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        luc = rec - des - enc
        if rec > 0:
            dre_df = pd.DataFrame([
                {"Descrição": "RECEITA BRUTA", "Valor": rec, "%": "100%"},
                {"Descrição": "(-) DESPESAS ADM", "Valor": des, "%": f"{(des/rec)*100:.2f}%"},
                {"Descrição": "(-) ENCARGOS FIN", "Valor": enc, "%": f"{(enc/rec)*100:.2f}%"},
                {"Descrição": "(=) RESULTADO LÍQUIDO", "Valor": luc, "%": f"{(luc/rec)*100:.2f}%"}
            ])
            st.table(dre_df.style.format({"Valor": "R$ {:.2f}"}))

    with t[3]: # Gestão com Grupo e Operação (Solicitado)
        st.subheader("Gerenciar Lançamentos")
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            # Exibição detalhada: Descrição, Grupo e Tipo de Operação
            c1.write(f"**{row['descricao']}** | Grupo: {row['natureza']}")
            c1.caption(f"Operação: {row['tipo']} | Valor: R$ {row['valor']:,.2f} | Natureza: {row.get('natureza_operacao', 'Outros')}")
            
            if c2.button("Editar", key=f"ed_{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("Excluir", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
            st.divider()
else:
    st.info("Aguardando lançamentos.")
