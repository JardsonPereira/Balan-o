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
st.set_page_config(page_title="Terminal Contábil v2.0", layout="wide")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets.")
    st.stop()

# --- ESTADOS ---
if 'user' not in st.session_state: st.session_state.user = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'menu_opcao' not in st.session_state: st.session_state.menu_opcao = "📊 Razonetes"

# --- LOGIN ---
if st.session_state.user is None:
    st.markdown("<h2 style='text-align: center;'>SISTEMA CONTÁBIL - LOGIN</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Acessar Terminal", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Falha na autenticação.")
    st.stop()

user_id = st.session_state.user.id

# --- CARREGAR DADOS ---
def carregar_dados():
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

df = carregar_dados()

# --- SIDEBAR (INPUT) ---
with st.sidebar:
    st.title("📟 Terminal")
    st.write(f"Operador: {st.session_state.user.email}")
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()
    st.divider()
    
    if st.session_state.edit_id:
        st.subheader("📝 Editar Registro")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.subheader("➕ Novo Registro")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"f_{st.session_state.form_count}"):
        contas = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        conta_sel = st.selectbox("Conta", ["NOVA CONTA"] + contas)
        desc = st.text_input("Nome da Conta", value=item_edit['descricao']).upper() if conta_sel == "NOVA CONTA" else conta_sel
        nat = st.selectbox("Grupo", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_input("Histórico", value=item_edit['justificativa'])
        
        if st.form_submit_button("PROCESSAR"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.session_state.form_count += 1
            st.rerun()

# --- CSS (VISUAL DE CONSULTA) ---
st.markdown("""
<style>
    .system-header { background: #1a365d; color: white; padding: 10px; border-radius: 4px; font-family: monospace; margin-bottom: 20px; }
    .ficha-conta { background: white; border: 2px solid #1a365d; margin-bottom: 20px; font-family: 'Courier New', monospace; }
    .ficha-header { background: #1a365d; color: white; text-align: center; font-weight: bold; padding: 5px; text-transform: uppercase; }
    .grid-contas { display: flex; border-bottom: 2px solid #1a365d; min-height: 100px; }
    .col-deb { flex: 1; border-right: 2px solid #1a365d; padding: 8px; background: #fafafa; }
    .col-cre { flex: 1; padding: 8px; background: #fffafa; text-align: right; }
    .label-col { font-size: 10px; color: #666; font-weight: bold; border-bottom: 1px solid #ddd; margin-bottom: 5px; }
    .entry { font-size: 13px; margin-bottom: 3px; border-bottom: 1px dashed #eee; }
    .ficha-total { background: #e2e8f0; padding: 5px 15px; text-align: right; font-weight: bold; font-size: 14px; }
    .grupo-title { background: #cbd5e0; padding: 5px 15px; border-radius: 4px; font-weight: bold; margin: 20px 0 10px 0; }
</style>
""", unsafe_allow_html=True)

# --- UI PRINCIPAL ---
st.markdown("<div class='system-header'>TERMINAL DE CONSULTA CONTÁBIL - MÓDULO DE RAZONETES</div>", unsafe_allow_html=True)

n1, n2, n3, n4 = st.columns(4)
if n1.button("📊 Razonetes", use_container_width=True): st.session_state.menu_opcao = "📊 Razonetes"
if n2.button("🧾 Balancete", use_container_width=True): st.session_state.menu_opcao = "🧾 Balancete"
if n3.button("📈 DRE", use_container_width=True): st.session_state.menu_opcao = "📈 DRE"
if n4.button("⚙️ Gestão", use_container_width=True): st.session_state.menu_opcao = "⚙️ Gestão"

st.divider()

if not df.empty:
    opcao = st.session_state.menu_opcao
    
    if opcao == "📊 Razonetes":
        for nat in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_n = df[df['natureza'] == nat]
            if not df_n.empty:
                st.markdown(f"<div class='grupo-title'>📁 GRUPO: {nat.upper()}</div>", unsafe_allow_html=True)
                contas = sorted(df_n['descricao'].unique())
                cols = st.columns(2)
                for i, conta in enumerate(contas):
                    with cols[i % 2]:
                        df_c = df_n[df_n['descricao'] == conta]
                        v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        saldo = v_d - v_c
                        
                        # Gerar as linhas de débito e crédito separadamente para não quebrar o HTML
                        deb_rows = "".join([f"<div class='entry' style='color:green'>{r['valor']:,.2f}</div>" for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows()])
                        cre_rows = "".join([f"<div class='entry' style='color:red'>{r['valor']:,.2f}</div>" for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows()])
                        
                        txt_saldo = f"SALDO ATUAL: R$ {abs(saldo):,.2f} ({'DEVEDOR' if saldo >=0 else 'CREDOR'})"
                        
                        st.markdown(f"""
                        <div class="ficha-conta">
                            <div class="ficha-header">{conta}</div>
                            <div class="grid-contas">
                                <div class="col-deb">
                                    <div class="label-col">DÉBITOS (D)</div>
                                    {deb_rows}
                                </div>
                                <div class="col-cre">
                                    <div class="label-col">CRÉDITOS (C)</div>
                                    {cre_rows}
                                </div>
                            </div>
                            <div class="ficha-total">{txt_saldo}</div>
                        </div>
                        """, unsafe_allow_html=True)

    elif opcao == "🧾 Balancete":
        st.subheader("BALANCETE DE VERIFICAÇÃO")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"CONTA": conta, "DÉBITO": d, "CRÉDITO": c, "SALDO": d-c})
        st.dataframe(pd.DataFrame(bal_data), use_container_width=True)

    elif opcao == "📈 DRE":
        st.subheader("DEMONSTRAÇÃO DE RESULTADO")
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        des = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        st.metric("LUCRO/PREJUÍZO LÍQUIDO", f"R$ {rec - des - enc:,.2f}")

    elif opcao == "⚙️ Gestão":
        st.subheader("ADMINISTRAÇÃO")
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([4,1,1])
            c1.write(f"ID {row['id']} | {row['descricao']} | R$ {row['valor']:,.2f}")
            if c2.button("EDIT", key=f"e{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("DEL", key=f"d{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Nenhum dado processado no terminal.")
