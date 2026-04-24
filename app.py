import streamlit as st
import pandas as pd
import subprocess
import sys
from supabase import create_client, Client

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
        if not temp_df.empty and 'status' not in temp_df.columns:
            temp_df['status'] = 'Pago'
        return temp_df
    except Exception: return pd.DataFrame()

df = carregar_dados()

# --- FORMULÁRIO LATERAL ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.user.email}**")
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df.empty:
        st.header("📝 Editar Lançamento")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago"}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Nova Conta"] + contas_existentes
        idx_conta = opcoes_conta.index(item_edit['descricao']) if st.session_state.edit_id and item_edit['descricao'] in contas_existentes else 0
        
        conta_sel = st.selectbox("Conta", opcoes_conta, index=idx_conta)
        desc = st.text_input("Nome da Conta", value="").upper().strip() if conta_sel == "+ Nova Conta" else conta_sel

        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        status_pag = st.selectbox("Status Financeiro", ["Pago", "Pendente"], index=0 if item_edit.get('status') == "Pago" else 1)
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar Lançamento"):
            if not desc: st.error("Informe o nome da conta!")
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

# --- DASHBOARD DE MÉTRICAS ---
if not df.empty:
    ac_deb = df[(df['natureza'] == 'Ativo') & (df['tipo'] == 'Débito')]['valor'].sum()
    ac_cre = df[(df['natureza'] == 'Ativo') & (df['tipo'] == 'Crédito')]['valor'].sum()
    ac = ac_deb - ac_cre
    
    pc_cre = df[(df['natureza'] == 'Passivo') & (df['tipo'] == 'Crédito')]['valor'].sum()
    pc_deb = df[(df['natureza'] == 'Passivo') & (df['tipo'] == 'Débito')]['valor'].sum()
    pc = pc_cre - pc_deb
    
    liq_corr = ac / pc if pc != 0 else 0
    
    entradas = df[(df['status'] == 'Pago') & (df['tipo'] == 'Débito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    saidas = df[(df['status'] == 'Pago') & (df['tipo'] == 'Crédito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    saldo_real = entradas - saidas

    st.title("📑 Sistema Contábil Digital")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Saldo em Caixa (Pago)", f"R$ {saldo_real:,.2f}")
    m2.metric("Liquidez Corrente", f"{liq_corr:.2f}")
    m3.metric("Ativo Circulante", f"R$ {ac:,.2f}")
    m4.metric("Passivo Circulante", f"R$ {pc:,.2f}")

# --- NAVEGAÇÃO ---
st.divider()
col_nav = st.columns(5)
opcoes = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

# --- TELAS DETALHADAS ---
if df.empty:
    st.info("Aguardando lançamentos para gerar relatórios.")
else:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for grupo in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df[df['natureza'] == grupo]
            if not df_g.empty:
                st.subheader(f"📂 {grupo}")
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    with cols[i % 3]:
                        df_c = df_g[df_g['descricao'] == conta]
                        d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        saldo = (d - c) if grupo in ["Ativo", "Despesa"] else (c - d)
                        st.info(f"**{conta}**\n\nSaldo: R$ {saldo:,.2f}")

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("Balancete de Verificação Detalhado")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({
                "Conta": conta, 
                "Débito (R$)": d, 
                "Crédito (R$)": c, 
                "Saldo Devedor": d-c if d > c else 0,
                "Saldo Credor": c-d if c > d else 0
            })
        st.table(pd.DataFrame(bal_data).style.format(precision=2, decimal=',', thousands='.'))

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("Demonstração do Resultado do Exercício (Competência)")
        df_rec = df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum()
        df_des = df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum()
        df_enc = df[df['natureza'] == 'Encargos Financeiros'].groupby('descricao')['valor'].sum()
        
        receita_total = df_rec.sum()
        despesa_total = df_des.sum()
        financeiro_total = df_enc.sum()
        
        with st.expander(f"(=) RECEITA BRUTA: R$ {receita_total:,.2f}", expanded=True):
            for n, v in df_rec.items(): st.write(f"• {n}: R$ {v:,.2f}")
        
        with st.expander(f"(-) DESPESAS OPERACIONAIS: R$ {-despesa_total:,.2f}", expanded=True):
            for n, v in df_des.items(): st.write(f"• {n}: R$ {v:,.2f}")
            
        st.info(f"**(=) EBITDA / LAJIDA: R$ {receita_total - despesa_total:,.2f}**")
        
        with st.expander(f"(-) RESULTADO FINANCEIRO: R$ {-financeiro_total:,.2f}"):
            for n, v in df_enc.items(): st.write(f"• {n}: R$ {v:,.2f}")
            
        lucro_final = receita_total - despesa_total - financeiro_total
        st.success(f"**(=) LUCRO/PREJUÍZO LÍQUIDO: R$ {lucro_final:,.2f}**")

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("Fluxo de Caixa (Regime de Caixa - Efetivado)")
        df_pago = df[df['status'] == 'Pago'].copy()
        if not df_pago.empty:
            st.dataframe(df_pago[['descricao', 'natureza', 'tipo', 'valor', 'justificativa']], use_container_width=True)
            st.metric("Disponibilidade Imediata", f"R$ {saldo_real:,.2f}")
        else:
            st.warning("Não há lançamentos marcados como 'Pago'.")

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("Gerenciar Lançamentos")
        for _, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([4, 1, 1])
                c1.write(f"**{row['descricao']}** | R$ {row['valor']:,.2f} ({row['status']})")
                if c2.button("✏️", key=f"ed_{row['id']}"):
                    st.session_state.edit_id = row['id']
                    st.rerun()
                if c3.button("🗑️", key=f"del_{row['id']}"):
                    supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                    st.rerun()
                st.divider()
