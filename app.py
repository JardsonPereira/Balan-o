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
st.set_page_config(page_title="Terminal de Consulta Contábil", layout="wide")

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

# --- LOGIN (SISTEMA FECHADO) ---
if st.session_state.user is None:
    st.markdown("<h2 style='text-align: center;'>ERP CONTÁBIL - ACESSO RESTRITO</h2>", unsafe_allow_html=True)
    with st.container():
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            email = st.text_input("Usuário (E-mail)")
            senha = st.text_input("Senha", type="password")
            if st.button("Autenticar", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res.user
                    st.rerun()
                except: st.error("Acesso negado.")
    st.stop()

user_id = st.session_state.user.id

# --- CARREGAR DADOS ---
def carregar_dados():
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

df = carregar_dados()

# --- SIDEBAR: ÁREA DE INPUT ---
with st.sidebar:
    st.title("📟 Terminal")
    st.write(f"Operador: {st.session_state.user.email}")
    if st.button("Encerrar Terminal"):
        st.session_state.user = None
        st.rerun()
    st.divider()
    
    st.header("Entrada de Dados")
    if st.session_state.edit_id:
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
        st.warning(f"Editando Registro ID: {st.session_state.edit_id}")
    else:
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"f_{st.session_state.form_count}"):
        contas = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        conta_sel = st.selectbox("Conta", ["NOVA CONTA"] + contas)
        desc = st.text_input("Nome da Conta").upper() if conta_sel == "NOVA CONTA" else conta_sel
        nat = st.selectbox("Grupo Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"], index=0 if not st.session_state.edit_id else ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"].index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor Nominal", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_area("Histórico Contábil", value=item_edit['justificativa'])
        
        if st.form_submit_button("PROCESSAR LANÇAMENTO"):
            payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.session_state.form_count += 1
            st.rerun()

# --- CSS: ESTILO SISTEMA LEGADO/MODERNO ---
st.markdown("""
<style>
    body { background-color: #f0f2f6; }
    .stApp { background-color: #f0f2f6; }
    
    /* Cabeçalho de Sistema */
    .system-header {
        background-color: #1a365d; color: white; padding: 10px 20px;
        border-radius: 5px; margin-bottom: 20px; font-family: monospace;
    }

    /* Tabela de Razonete (Ficha) */
    .ficha-conta {
        background-color: white; border: 2px solid #1a365d; margin-bottom: 30px;
    }
    .ficha-header {
        background-color: #1a365d; color: white; padding: 5px;
        text-align: center; font-weight: bold; font-size: 1.1rem;
    }
    .grid-contas { display: flex; border-bottom: 2px solid #1a365d; }
    .col-deb, .col-cre { flex: 1; padding: 10px; min-height: 80px; }
    .col-deb { border-right: 2px solid #1a365d; background-color: #fcfdfc; }
    .col-cre { background-color: #fdfcfc; }
    
    .label-col { font-size: 0.7rem; font-weight: bold; color: #555; text-transform: uppercase; margin-bottom: 5px; }
    .entry { font-family: 'Courier New', monospace; font-size: 0.9rem; margin-bottom: 2px; }
    .entry-val-d { color: green; }
    .entry-val-c { color: red; text-align: right; }
    
    .ficha-total {
        background-color: #e2e8f0; padding: 5px 15px;
        text-align: right; font-family: monospace; font-weight: bold; font-size: 1rem;
    }

    /* Estilo de Menu Abas */
    .stButton > button {
        border-radius: 0px; border: 1px solid #1a365d; background-color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- UI PRINCIPAL ---
st.markdown("<div class='system-header'>SISTEMA DE CONSULTA DE LANÇAMENTOS - MÓDULO CONTÁBIL v2.0</div>", unsafe_allow_html=True)

# Tabs de Navegação Estilo Sistema
nav_cols = st.columns(4)
menu_opcoes = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "⚙️ Gestão"]
for i, m in enumerate(menu_opcoes):
    if nav_cols[i].button(m, use_container_width=True): st.session_state.menu_opcao = m

st.divider()

if not df.empty:
    opcao = st.session_state.menu_opcao
    
    if opcao == "📊 Razonetes":
        for nat in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_n = df[df['natureza'] == nat]
            if not df_n.empty:
                st.markdown(f"### 📂 GRUPO: {nat.upper()}")
                contas = sorted(df_n['descricao'].unique())
                cols = st.columns(2) # 2 colunas para parecer fichas de papel
                for i, conta in enumerate(contas):
                    with cols[i % 2]:
                        df_c = df_n[df_n['descricao'] == conta]
                        v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        saldo = v_d - v_c
                        
                        # Construção da Ficha Contábil
                        st.markdown(f"""
                        <div class="ficha-conta">
                            <div class="ficha-header">{conta}</div>
                            <div class="grid-contas">
                                <div class="col-deb">
                                    <div class="label-col">Débitos (D)</div>
                                    {"".join([f"<div class='entry entry-val-d'>{r['valor']:,.2f} <small style='color:gray'>({r['justificativa']})</small></div>" for _,r in df_c[df_c['tipo']=='Débito'].iterrows()])}
                                </div>
                                <div class="col-cre">
                                    <div class="label-col" style="text-align:right">Créditos (C)</div>
                                    {"".join([f"<div class='entry entry-val-c'>{r['valor']:,.2f} <small style='color:gray'>({r['justificativa']})</small></div>" for _,r in df_c[df_c['tipo']=='Crédito'].iterrows()])}
                                </div>
                            </div>
                            <div class="ficha-total">
                                SALDO ATUAL: R$ {abs(saldo):,.2f} {'(DEVEDOR)' if saldo >=0 else '(CREDOR)'}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    elif opcao == "🧾 Balancete":
        st.subheader("RELATÓRIO DE BALANCETE DE VERIFICAÇÃO")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"CONTA": conta, "NATUREZA": df_c['natureza'].iloc[0], "DEVEDOR": d-c if d>c else 0, "CREDOR": c-d if c>d else 0})
        bal_df = pd.DataFrame(bal_data)
        st.table(bal_df.style.format({"DEVEDOR": "{:,.2f}", "CREDOR": "{:,.2f}"}))
        st.metric("TOTAL DEVEDOR", f"R$ {bal_df['DEVEDOR'].sum():,.2f}")
        st.metric("TOTAL CREDOR", f"R$ {bal_df['CREDOR'].sum():,.2f}")

    elif opcao == "📈 DRE":
        st.subheader("DEMONSTRAÇÃO DE RESULTADO DO EXERCÍCIO")
        rec = df[df['natureza'] == 'Receita']['valor'].sum()
        des = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        
        st.markdown(f"""
        **(+) RECEITA OPERACIONAL BRUTA:** R$ {rec:,.2f}  
        **(-) DESPESAS OPERACIONAIS:** R$ {des:,.2f}  
        ---
        **(=) EBITDA:** R$ {rec - des:,.2f}  
        **(-) RESULTADO FINANCEIRO:** R$ {enc:,.2f}  
        ---
        **(=) LUCRO/PREJUÍZO LÍQUIDO:** R$ {rec - des - enc:,.2f}
        """)

    elif opcao == "⚙️ Gestão":
        st.subheader("MANUTENÇÃO DE REGISTROS")
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([4,1,1])
            c1.write(f"[{row['id']}] {row['descricao']} | R$ {row['valor']:,.2f} | {row['tipo']}")
            if c2.button("EDIT", key=f"e{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("DEL", key=f"d{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("Aguardando entrada de dados para gerar consultas.")
