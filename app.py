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

# --- FORMULÁRIO (CORRIGIDO PARA NÃO SUMIR) ---
with st.sidebar:
    st.divider()
    if st.session_state.edit_id:
        st.header("📝 Editar")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.01, "justificativa": ""}

    # IMPORTANTE: Não usamos clear_on_submit=True para evitar bugs de reset visual
    with st.form("contabil"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        
        idx_conta = 0
        if st.session_state.edit_id and item_edit['descricao'] in contas_existentes:
            idx_conta = opcoes_conta.index(item_edit['descricao'])
            
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        
        # Lógica persistente para o nome da conta
        if conta_sel == "+ Adicionar Nova Conta":
            desc = st.text_input("Nome da Nova Conta").upper().strip()
        else:
            desc = conta_sel

        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.01, value=float(item_edit['valor']))
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar Lançamento"):
            if not desc:
                st.error("O nome da conta é obrigatório!")
            else:
                payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
                try:
                    if st.session_state.edit_id:
                        supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                        st.session_state.edit_id = None
                    else:
                        supabase.table("lancamentos").insert(payload).execute()
                    st.success("Salvo com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

# --- INTERFACE PRINCIPAL ---
st.title("📑 Sistema Contábil Digital")

opcao_menu = st.selectbox("Menu de Navegação", ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "⚙️ Gestão"])

if not df.empty:
    if opcao_menu == "📊 Razonetes":
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

    elif opcao_menu == "🧾 Balancete":
        st.subheader("Balancete de Verificação")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Saldo Devedor": d-c if d>c else 0, "Saldo Credor": c-d if c>d else 0})
        bal_df = pd.DataFrame(bal_data)
        st.table(bal_df.style.format({"Saldo Devedor": "R$ {:.2f}", "Saldo Credor": "R$ {:.2f}"}))
        t_dev, t_cre = bal_df["Saldo Devedor"].sum(), bal_df["Saldo Credor"].sum()
        col_b1, col_b2 = st.columns(2)
        col_b1.metric("Total Devedores", f"R$ {t_dev:,.2f}")
        col_b2.metric("Total Credores", f"R$ {t_cre:,.2f}")

    elif opcao_menu == "📈 DRE":
        st.subheader("Demonstração do Resultado do Exercício")
        df_rec = df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum()
        df_des = df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum()
        df_enc = df[df['natureza'] == 'Encargos Financeiros'].groupby('descricao')['valor'].sum()
        
        rec_total = df_rec.sum()
        des_total = df_des.sum()
        enc_total = df_enc.sum()
        ebitda = rec_total - des_total
        lucro_real = ebitda - enc_total

        with st.expander(f"(=) RECEITA BRUTA OPERACIONAL: R$ {rec_total:,.2f}", expanded=True):
            for nome, valor in df_rec.items():
                st.write(f"   (+) {nome}: R$ {valor:,.2f}")

        with st.expander(f"(-) DESPESAS OPERACIONAIS: R$ {-des_total:,.2f}", expanded=False):
            for nome, valor in df_des.items():
                st.write(f"   (-) {nome}: R$ {valor:,.2f}")

        st.info(f"**(=) EBITDA (LAJIDA): R$ {ebitda:,.2f}**")

        with st.expander(f"(-) RESULTADO FINANCEIRO: R$ {-enc_total:,.2f}", expanded=False):
            for nome, valor in df_enc.items():
                st.write(f"   (-) {nome}: R$ {valor:,.2f}")

        st.success(f"### **(=) LUCRO REAL LÍQUIDO: R$ {lucro_real:,.2f}**")

    elif opcao_menu == "⚙️ Gestão":
        st.subheader("Gerenciar Lançamentos")
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            c1.write(f"**{row['descricao']}** | Grupo: {row['natureza']}")
            c1.caption(f"Operação: {row['tipo']} | Valor: R$ {row['valor']:,.2f}")
            if c2.button("Editar", key=f"ed_{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("Excluir", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
            st.divider()
else:
    st.info("Aguardando lançamentos.")
