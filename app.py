import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

# 1. Configuração de Página
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. Conexão com Supabase (Configurar Secrets no Streamlit Cloud)
conn = st.connection("supabase", type=SupabaseConnection)

# --- CSS INTEGRADO ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main { overflow: auto !important; height: auto !important; }
    .main .block-container { padding-bottom: 250px !important; }
    .gestao-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 8px; }
    .badge-natureza { background-color: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: bold; }
    .dre-header { font-size: 16px !important; font-weight: bold !important; color: #1E3A8A; margin: 0; }
    .dre-value { font-size: 24px !important; font-weight: 900 !important; margin-bottom: 15px; }
    .resumo-dre-linha { font-size: 1.1em; font-weight: bold; padding: 12px; border-radius: 8px; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Lógica de Autenticação na Barra Lateral
st.sidebar.title("🔐 Acesso ao Sistema")
aba_auth = st.sidebar.radio("Escolha uma opção", ["Login", "Criar Conta"])
email = st.sidebar.text_input("E-mail")
senha = st.sidebar.text_input("Senha", type="password")

user_session = None

if aba_auth == "Criar Conta":
    if st.sidebar.button("Registrar"):
        try:
            conn.auth.sign_up(email=email, password=senha)
            st.sidebar.success("Conta criada! Verifique seu e-mail ou faça login.")
        except Exception as e:
            st.sidebar.error(f"Erro ao criar conta: {e}")
else:
    try:
        user_session = conn.auth.sign_in_with_password(email=email, password=senha)
    except:
        st.sidebar.info("Aguardando login...")

# --- SÓ MOSTRA O SISTEMA SE ESTIVER LOGADO ---
if user_session:
    u_id = user_session.user.id
    st.sidebar.success(f"Logado como: {email}")
    if st.sidebar.button("Sair"):
        conn.auth.sign_out()
        st.rerun()

    st.title("📑 Sistema Contábil Integrado")

    # 4. Funções de Banco de Dados
    def buscar_dados():
        res = conn.table("lancamentos").select("*").eq("user_id", u_id).execute()
        return pd.DataFrame(res.data)

    df_db = buscar_dados()

    # 5. Formulário de Lançamento
    with st.sidebar:
        st.divider()
        st.header("➕ Novo Lançamento")
        with st.form("form_contabil", clear_on_submit=True):
            contas_existentes = sorted(df_db['descricao'].unique().tolist()) if not df_db.empty else []
            escolha_conta = st.selectbox("Conta Existente", ["-- Selecione --"] + contas_existentes)
            nova_conta = st.text_input("OU Nova Conta").upper().strip()
            
            natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"])
            tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            justificativa = st.text_area("Justificativa")
            
            if st.form_submit_button("Confirmar Dados", use_container_width=True):
                nome_final = nova_conta if nova_conta else (escolha_conta if escolha_conta != "-- Selecione --" else None)
                if nome_final and valor > 0:
                    dados_insert = {
                        "user_id": u_id,
                        "descricao": nome_final,
                        "natureza": natureza,
                        "tipo": tipo,
                        "valor": valor,
                        "justificativa": justificativa
                    }
                    conn.table("lancamentos").insert(dados_insert).execute()
                    st.rerun()

    # 6. Interface Principal
    if not df_db.empty:
        tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Auditoria & Balancete", "📈 DRE Detalhada", "⚙️ Gestão"])
        
        # Cálculos para DRE
        rec_tot = df_db[df_db['natureza'] == 'Receita']['valor'].sum()
        desp_op = df_db[df_db['natureza'] == 'Despesa']['valor'].sum()
        enc_fin = df_db[df_db['natureza'] == 'Encargos Financeiros']['valor'].sum()
        ebitda = rec_tot - desp_op
        lucro_real = ebitda - enc_fin
        def calcular_av(v): return f"{(v/rec_tot*100):.2f}%" if rec_tot > 0 else "0.00%"

        # --- ABA RAZONETES ---
        with tab_raz:
            for conta in sorted(df_db['descricao'].unique()):
                df_c = df_db[df_db['descricao'] == conta]
                with st.expander(f"📖 Razonete: {conta}"):
                    c_d, c_c = st.columns(2)
                    v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                    v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                    c_d.write("**DÉBITO**")
                    for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows(): c_d.caption(f"R$ {r['valor']:,.2f}")
                    c_c.write("**CRÉDITO**")
                    for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows(): c_c.caption(f"R$ {r['valor']:,.2f}")
                    st.divider()
                    st.write(f"Saldo: R$ {abs(v_d - v_c):,.2f} ({'Devedor' if v_d >= v_c else 'Credor'})")

        # --- ABA GESTÃO (COM DELETE) ---
        with tab_ges:
            for _, row in df_db.iterrows():
                st.markdown(f'<div class="gestao-card"><b>{row["descricao"]}</b> - {row["tipo"]}: R$ {row["valor"]:,.2f}</div>', unsafe_allow_html=True)
                if st.button("Remover", key=f"del_{row['id']}"):
                    conn.table("lancamentos").delete().eq("id", row['id']).execute()
                    st.rerun()
    else:
        st.info("Nenhum dado encontrado. Comece lançando na barra lateral.")

else:
    st.warning("Acesse com seu e-mail e senha para visualizar seus dados contábeis.")
