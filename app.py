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
        
        desc = st.text_input("Nome da Nova Conta").upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel

        nat_op_list = ["Integralização de Capital", "Venda de Mercadorias/Serviços", "Compra de Mercadorias/Bens", "Pagamento de Salários", "Encargos Financeiros", "Outros"]
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
    
    with t[0]: # RAZONETES COM RESULTADO FINAL
        st.subheader("Livro Razão (Razonetes)")
        cols = st.columns(3)
        for i, conta in enumerate(sorted(df['descricao'].unique())):
            with cols[i % 3]:
                df_c = df[df['descricao'] == conta]
                
                # Título da Conta
                st.markdown(f"<div style='text-align:center; font-weight:bold; border-bottom:2px solid black; background-color:#f8f9fa;'>{conta}</div>", unsafe_allow_html=True)
                
                # Movimentação
                c_d, c_c = st.columns(2)
                v_deb = df_c[df_c['tipo'] == 'Débito']['valor'].tolist()
                v_cre = df_c[df_c['tipo'] == 'Crédito']['valor'].tolist()
                
                with c_d:
                    st.markdown("<p style='text-align:center; color:blue; font-size:11px;'>Débito</p>", unsafe_allow_html=True)
                    for v in v_deb: st.write(f"R$ {v:,.2f}")
                with c_c:
                    st.markdown("<p style='text-align:center; color:red; font-size:11px;'>Crédito</p>", unsafe_allow_html=True)
                    for v in v_cre: st.write(f"R$ {v:,.2f}")
                
                # Totais e Resultado Final do Razonete
                total_d = sum(v_deb)
                total_c = sum(v_cre)
                saldo = total_d - total_c
                
                st.markdown("<div style='border-top:1px solid gray;'></div>", unsafe_allow_html=True)
                res_d, res_c = st.columns(2)
                
                if saldo > 0:
                    res_d.markdown(f"**Saldo: R$ {saldo:,.2f}**")
                elif saldo < 0:
                    res_c.markdown(f"**Saldo: R$ {abs(saldo):,.2f}**")
                else:
                    st.write("<p style='text-align:center;'>Conta Zerada</p>", unsafe_allow_html=True)
                st.write("") # Espaçador

    with t[1]: # Balancete
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Devedor": d-c if d>c else 0, "Credor": c-d if c>d else 0})
        st.table(pd.DataFrame(bal_data).style.format({"Devedor": "R$ {:.2f}", "Credor": "R$ {:.2f}"}))

    with t[2]: # DRE
        st.subheader("DRE (Análise Vertical)")
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        des = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        luc = rec - des - enc
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receita", f"R$ {rec:,.2f}")
        c2.metric("Despesas", f"R$ {des:,.2f}")
        c3.metric("Encargos", f"R$ {enc:,.2f}")
        c4.metric("Lucro", f"R$ {luc:,.2f}")

        if rec > 0:
            dre_final = pd.DataFrame([
                {"Descrição": "RECEITA BRUTA", "Valor": rec, "%": "100%"},
                {"Descrição": "(-) DESPESAS ADM", "Valor": des, "%": f"{(des/rec)*100:.2f}%"},
                {"Descrição": "(-) ENCARGOS FIN", "Valor": enc, "%": f"{(enc/rec)*100:.2f}%"},
                {"Descrição": "(=) RESULTADO LÍQUIDO", "Valor": luc, "%": f"{(luc/rec)*100:.2f}%"}
            ])
            st.table(dre_final.style.format({"Valor": "R$ {:.2f}"}))

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
