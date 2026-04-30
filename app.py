import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta

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

@st.cache_data(ttl=600)
def carregar_dados(u_id):
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        temp_df = pd.DataFrame(res.data)
        if not temp_df.empty:
            temp_df['data_lancamento'] = pd.to_datetime(temp_df['data_lancamento']).dt.date
            if 'status' not in temp_df.columns: temp_df['status'] = 'Pago'
            if 'justificativa' not in temp_df.columns: temp_df['justificativa'] = ''
        return temp_df
    except Exception: return pd.DataFrame()

df = carregar_dados(user_id)

# --- FORMULÁRIO LATERAL ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.user.email}**")
    if st.button("Sair"):
        st.session_state.user = None
        st.cache_data.clear()
        st.rerun()
    st.divider()
    
    # Botão para forçar a criação de um novo lançamento (limpa o edit_id)
    if st.session_state.edit_id:
        if st.button("⬅️ Cancelar Edição / Novo"):
            st.session_state.edit_id = None
            st.rerun()

    if st.session_state.edit_id and not df.empty:
        st.header("📝 Editar Lançamento")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago", "data_lancamento": datetime.now().date()}

    with st.form(key=f"form_contabil_{st.session_state.form_count}"):
        # 1. Seleção de Conta
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes = ["+ Adicionar Nova Conta"] + contas_existentes
        
        idx_default = 0
        if st.session_state.edit_id and item_edit['descricao'] in contas_existentes:
            idx_default = opcoes.index(item_edit['descricao'])
        
        conta_selecionada = st.selectbox("Selecione a Conta", opcoes, index=idx_default)
        
        # 2. Nome da Conta (se for nova)
        if conta_selecionada == "+ Adicionar Nova Conta":
            nome_final = st.text_input("Nome da Nova Conta", value="").upper().strip()
        else:
            nome_final = conta_selecionada

        # 3. Campos restantes
        dt_lanc = st.date_input("Data", value=item_edit['data_lancamento'])
        nat_opcoes = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        natureza = st.selectbox("Grupo", nat_opcoes, index=nat_opcoes.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        
        status_opcoes = ["Pago", "Entrada", "Pendente", "Investimento", "Transferência Interna"]
        status_sel = st.selectbox("Status", status_opcoes, index=status_opcoes.index(item_edit['status']) if item_edit['status'] in status_opcoes else 0)
        justificativa = st.text_area("Justificativa", value=item_edit['justificativa'])

        submit = st.form_submit_button("Salvar Lançamento")
        
        if submit:
            if not nome_final or nome_final == "+ ADICIONAR NOVA CONTA":
                st.error("Informe um nome válido para a conta.")
            else:
                payload = {
                    "user_id": user_id, 
                    "descricao": nome_final, 
                    "natureza": natureza, 
                    "tipo": tipo, 
                    "valor": valor, 
                    "justificativa": justificativa, 
                    "status": status_sel, 
                    "data_lancamento": str(dt_lanc)
                }
                
                if st.session_state.edit_id:
                    supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                    st.session_state.edit_id = None
                else:
                    supabase.table("lancamentos").insert(payload).execute()
                
                st.cache_data.clear()
                st.session_state.form_count += 1 # Muda a chave do formulário para resetar campos
                st.rerun()

# --- CSS ---
st.markdown("""<style>
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; text-transform: uppercase; border-radius: 12px 12px 0 0; }
    .conta-corpo { display: flex; min-height: 80px; position: relative; }
    .conta-corpo::after { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1.5px; background-color: #cbd5e1; }
    .lado-debito, .lado-credito { flex: 1; padding: 10px; font-size: 0.8rem; }
    .valor-deb { color: #059669; font-weight: 600; }
    .valor-cre { color: #dc2626; font-weight: 600; text-align: right; }
    .just-hint { font-size: 0.7rem; color: #64748b; font-style: italic; display: block; }
    .conta-rodape { padding: 8px; background: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; font-weight: 700; border-radius: 0 0 12px 12px; }
</style>""", unsafe_allow_html=True)

st.title("📑 Sistema Contábil Digital")

# --- NAVEGAÇÃO ---
col_nav = st.columns(5)
opcoes_menu = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes_menu):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()
f1, f2 = st.columns(2)
with f1: data_ini = st.date_input("Início", value=datetime.now().date().replace(day=1))
with f2: data_fim = st.date_input("Fim", value=datetime.now().date())

df_periodo = df[(df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)] if not df.empty else df

if df.empty:
    st.info("Nenhum lançamento encontrado.")
else:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for grupo in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"]:
            df_g = df[df['natureza'] == grupo]
            if not df_g.empty:
                st.subheader(f"📂 {grupo}")
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    df_c = df_g[df_g['descricao'] == conta]
                    v_d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                    v_c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                    saldo = (v_d - v_c) if grupo in ["Ativo", "Despesa"] else (v_c - v_d)
                    
                    deb_html = "".join([f"<div class='valor-deb'>D: {r['valor']:,.2f} <span class='just-hint'>{r['justificativa']}</span></div>" for _,r in df_c[df_c['tipo']=='Débito'].iterrows()])
                    cre_html = "".join([f"<div class='valor-cre'>C: {r['valor']:,.2f} <span class='just-hint'>{r['justificativa']}</span></div>" for _,r in df_c[df_c['tipo']=='Crédito'].iterrows()])
                    
                    with cols[i % 3]:
                        st.markdown(f"""
                        <div class="conta-card">
                            <div class="conta-titulo">{conta}</div>
                            <div class="conta-corpo">
                                <div class="lado-debito">{deb_html}</div>
                                <div class="lado-credito">{cre_html}</div>
                            </div>
                            <div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Fluxo de Caixa")
        status_l = ["Pago", "Entrada", "Investimento"]
        
        def get_giro(target_df, data_lim):
            df_hist = target_df[(target_df['data_lancamento'] <= data_lim) & (target_df['status'].isin(status_l))]
            v_giro = df_hist[(df_hist['natureza'].isin(['Ativo', 'Patrimônio Líquido'])) & (df_hist['descricao'].str.contains('CAIXA|BANCO|CAPITAL', case=False))]
            saldo = 0.0
            for _, r in v_giro.iterrows():
                if r['natureza'] == 'Ativo': saldo += r['valor'] if r['tipo'] == 'Débito' else -r['valor']
                else: saldo += r['valor'] if r['tipo'] == 'Crédito' else -r['valor']
            return saldo

        sf = get_giro(df, data_fim)
        si = get_giro(df, data_ini - timedelta(days=1))
        
        df_per = df[(df['status'].isin(status_l)) & (df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)]
        ent_op = df_per[df_per['natureza'] == 'Receita'][df_per['tipo'] == 'Crédito']['valor'].sum()
        ent_pl = df_per[df_per['natureza'] == 'Patrimônio Líquido'][df_per['tipo'] == 'Crédito']['valor'].sum()
        sai_op = df_per[df_per['natureza'] == 'Despesa'][df_per['tipo'] == 'Débito']['valor'].sum()
        sai_div = df_per[df_per['natureza'] == 'Passivo'][df_per['tipo'] == 'Débito']['valor'].sum()
        sai_atv = df_per[(df_per['natureza'] == 'Ativo') & (df_per['tipo'] == 'Crédito') & (~df_per['descricao'].str.contains('CAIXA|BANCO', case=False))]['valor'].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo Inicial", f"R$ {si:,.2f}")
        c2.metric("Variação", f"R$ {sf-si:,.2f}", delta=f"{sf-si:,.2f}")
        c3.metric("Saldo Final", f"R$ {sf:,.2f}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📥 Entradas: R$ {ent_op + ent_pl:,.2f}\n(Rec: {ent_op:,.2f} | PL: {ent_pl:,.2f})")
        with col2:
            st.warning(f"out Saídas: R$ {sai_op + sai_div + sai_atv:,.2f}\n(Desp: {sai_op:,.2f} | Dív: {sai_div:,.2f} | Ativo: {sai_atv:,.2f})")

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("⚙️ Gestão")
        for _, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([5, 1, 1])
                c1.write(f"**[{row['data_lancamento']}] {row['descricao']}** - R$ {row['valor']:,.2f}")
                if c2.button("✏️", key=f"edit_btn_{row['id']}"): 
                    st.session_state.edit_id = row['id']
                    st.rerun()
                if c3.button("🗑️", key=f"del_btn_{row['id']}"): 
                    supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                    st.cache_data.clear()
                    st.rerun()
