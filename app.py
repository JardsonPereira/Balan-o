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
    st.markdown("<h2 style='text-align: center; font-family: monospace;'>SISTEMA CONTÁBIL - LOGIN</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Acessar Terminal", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Acesso Negado.")
    st.stop()

user_id = st.session_state.user.id

def carregar_dados():
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

df = carregar_dados()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 📟 MÓDULO OPERACIONAL")
    st.caption(f"Operador: {st.session_state.user.email}")
    if st.button("Sair do Sistema"):
        st.session_state.user = None
        st.rerun()
    st.divider()
    
    if st.session_state.edit_id:
        st.subheader("📝 EDITAR REGISTRO")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.subheader("➕ NOVO LANÇAMENTO")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"f_{st.session_state.form_count}"):
        contas = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        conta_sel = st.selectbox("CONTA", ["(NOVA CONTA)"] + contas)
        desc = st.text_input("NOME DA CONTA", value=item_edit['descricao']).upper() if conta_sel == "(NOVA CONTA)" else conta_sel
        nat = st.selectbox("GRUPO", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit['natureza']))
        tipo = st.radio("OPERAÇÃO", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("VALOR", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_input("HISTÓRICO", value=item_edit['justificativa'])
        
        if st.form_submit_button("PROCESSAR"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.session_state.form_count += 1
            st.rerun()

# --- CSS PARA ESTILO TERMINAL ---
st.markdown("""
<style>
    .terminal-header { background: #0f172a; color: #38bdf8; padding: 10px; font-family: monospace; font-size: 14px; border-radius: 4px; border-left: 5px solid #38bdf8; margin-bottom: 20px; }
    .razonete-container { border: 2px solid #1e293b; border-radius: 4px; background: #ffffff; margin-bottom: 20px; font-family: monospace; }
    .razonete-header { background: #1e293b; color: #f8fafc; text-align: center; padding: 5px; font-weight: bold; border-bottom: 2px solid #1e293b; }
    .label-box { font-size: 10px; color: #64748b; font-weight: bold; border-bottom: 1px solid #e2e8f0; margin-bottom: 5px; }
    .total-box { background: #f1f5f9; border-top: 2px solid #1e293b; padding: 5px 10px; text-align: right; font-weight: bold; font-size: 14px; color: #0f172a; }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
st.markdown("<div class='terminal-header'>CONSOLE DE CONSULTA CONTÁBIL > MÓDULO CENTRAL</div>", unsafe_allow_html=True)

menu_cols = st.columns(4)
botoes = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "⚙️ Gestão"]
for i, b in enumerate(botoes):
    if menu_cols[i].button(b, use_container_width=True): st.session_state.menu_opcao = b

st.divider()

if not df.empty:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for nat in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df[df['natureza'] == nat]
            if not df_g.empty:
                st.subheader(f"📂 GRUPO: {nat.upper()}")
                contas = sorted(df_g['descricao'].unique())
                cols = st.columns(2)
                for i, conta in enumerate(contas):
                    with cols[i % 2]:
                        # AQUI ESTÁ A CORREÇÃO: Usamos st.container para criar a ficha
                        with st.container():
                            st.markdown(f"<div class='razonete-container'><div class='razonete-header'>{conta}</div>", unsafe_allow_html=True)
                            
                            sub_c1, sub_c2 = st.columns(2)
                            df_c = df_g[df_g['descricao'] == conta]
                            
                            with sub_c1:
                                st.markdown("<div class='label-box'>DÉBITOS (D)</div>", unsafe_allow_html=True)
                                for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows():
                                    st.markdown(f"<span style='color:green; font-size:12px;'>{r['valor']:,.2f}</span>", unsafe_allow_html=True)
                                    if r['justificativa']: st.caption(r['justificativa'])
                            
                            with sub_c2:
                                st.markdown("<div class='label-box' style='text-align:right'>CRÉDITOS (C)</div>", unsafe_allow_html=True)
                                for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows():
                                    st.markdown(f"<div style='color:red; font-size:12px; text-align:right;'>{r['valor']:,.2f}</div>", unsafe_allow_html=True)
                                    if r['justificativa']: st.caption(f"<div style='text-align:right'>{r['justificativa']}</div>", unsafe_allow_html=True)
                            
                            v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                            v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                            saldo = v_d - v_c
                            txt_saldo = f"SALDO: R$ {abs(saldo):,.2f} ({'D' if saldo >=0 else 'C'})"
                            st.markdown(f"<div class='total-box'>{txt_saldo}</div></div>", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("RELATÓRIO DE BALANCETE")
        bal_data = []
        for c in sorted(df['descricao'].unique()):
            temp = df[df['descricao'] == c]
            d = temp[temp['tipo'] == 'Débito']['valor'].sum()
            cr = temp[temp['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"CONTA": c, "DÉBITO": d, "CRÉDITO": cr, "SALDO": d-cr})
        st.table(pd.DataFrame(bal_data))

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("DEMONSTRATIVO DE RESULTADO")
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        des = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        st.code(f"(+) RECEITA BRUTA: {rec:,.2f}\n(-) DESPESAS:     {des:,.2f}\n(-) FINANC:       {enc:,.2f}\n---------------------------\n(=) RESULTADO:    {rec-des-enc:,.2f}")

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("ADMINISTRAÇÃO DE LANÇAMENTOS")
        for idx, row in df.iterrows():
            with st.expander(f"ID {row['id']} | {row['descricao']} | R$ {row['valor']:,.2f}"):
                st.write(f"Grupo: {row['natureza']} | Tipo: {row['tipo']}")
                st.write(f"Histórico: {row['justificativa']}")
                c1, c2 = st.columns(2)
                if c1.button("EDITAR", key=f"e_{row['id']}"):
                    st.session_state.edit_id = row['id']
                    st.rerun()
                if c2.button("EXCLUIR", key=f"d_{row['id']}"):
                    supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                    st.rerun()
else:
    st.info("NENHUM DADO ENCONTRADO NO BANCO DE DADOS.")
