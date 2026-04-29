import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

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
if 'confirm_reset' not in st.session_state: st.session_state.confirm_reset = False

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
        if not temp_df.empty:
            # Proteção contra ausência da coluna de data ou status
            if 'data_lancamento' not in temp_df.columns:
                temp_df['data_lancamento'] = datetime.now().date()
            else:
                temp_df['data_lancamento'] = pd.to_datetime(temp_df['data_lancamento']).dt.date
            
            if 'status' not in temp_df.columns:
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
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago", "data_lancamento": datetime.now().date()}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        idx_conta = opcoes_conta.index(item_edit['descricao']) if st.session_state.edit_id and item_edit['descricao'] in contas_existentes else 0
        
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        desc = st.text_input("Nome da Nova Conta", value="").upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel

        # DATA DO LANÇAMENTO
        data_lanc = st.date_input("Data do Lançamento", value=item_edit.get('data_lancamento', datetime.now().date()))

        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        
        # STATUS ATUALIZADOS
        opcoes_status = ["Entrada", "Pendente", "Pago", "Investimento"]
        status_atual = item_edit.get('status', 'Pago')
        idx_status = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0
        status_pag = st.selectbox("Status Financeiro", opcoes_status, index=idx_status)
        
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar Lançamento"):
            if not desc: st.error("Informe o nome da conta!")
            else:
                payload = {
                    "user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, 
                    "valor": valor, "justificativa": just, "status": status_pag,
                    "data_lancamento": str(data_lanc)
                }
                try:
                    if st.session_state.edit_id:
                        supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                        st.session_state.edit_id = None
                    else:
                        supabase.table("lancamentos").insert(payload).execute()
                    st.session_state.form_count += 1
                    st.rerun()
                except Exception as e: st.error(f"Erro ao salvar: {e}")

# --- CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; overflow: hidden; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; border-bottom: 2px solid #334155; }
    .conta-corpo { display: flex; min-height: 80px; position: relative; }
    .conta-corpo::after { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1.5px; background-color: #cbd5e1; }
    .lado-debito, .lado-credito { flex: 1; padding: 10px; }
    .valor-item { font-size: 0.8rem; margin-bottom: 4px; line-height: 1.2; }
    .valor-deb { color: #059669; font-weight: 600; }
    .valor-cre { color: #dc2626; font-weight: 600; text-align: right; }
    .just-hint { font-size: 0.65rem; color: #64748b; font-style: italic; display: block; font-weight: 400; }
    .conta-rodape { padding: 8px; background: #f8fafc; border-top: 1.5px solid #1e293b; text-align: center; font-weight: 700; font-size: 0.85rem; }
    .grupo-header { background: linear-gradient(90deg, #1e293b, #334155); color: white; padding: 10px 15px; border-radius: 8px; margin: 25px 0 10px 0; font-size: 0.95rem; font-weight: 600; }
    .dre-linha { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #e2e8f0; }
    .dre-total { font-weight: 700; background-color: #e2e8f0; padding: 8px 5px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("📑 Sistema Contábil Digital")

# --- DASHBOARD DE MÉTRICAS ---
if not df.empty:
    ac_deb = df[(df['natureza'] == 'Ativo') & (df['tipo'] == 'Débito')]['valor'].sum()
    ac_cre = df[(df['natureza'] == 'Ativo') & (df['tipo'] == 'Crédito')]['valor'].sum()
    ac = ac_deb - ac_cre
    pc_cre = df[(df['natureza'] == 'Passivo') & (df['tipo'] == 'Crédito')]['valor'].sum()
    pc_deb = df[(df['natureza'] == 'Passivo') & (df['tipo'] == 'Débito')]['valor'].sum()
    pc = pc_cre - pc_deb
    
    entradas_caixa = df[(df['status'].isin(['Pago', 'Entrada'])) & (df['tipo'] == 'Débito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    saidas_caixa = df[(df['status'].isin(['Pago', 'Investimento'])) & (df['tipo'] == 'Crédito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    saldo_caixa = entradas_caixa - saidas_caixa

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Saldo em Caixa (Real)", f"R$ {saldo_caixa:,.2f}")
    m2.metric("Liquidez Corrente", f"{ac/pc:.2f}" if pc != 0 else "0.00")
    m3.metric("Ativo Total", f"R$ {ac:,.2f}")
    m4.metric("Passivo Total", f"R$ {pc:,.2f}")

# --- NAVEGAÇÃO ---
st.divider()
col_nav = st.columns(5)
opcoes = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

# --- TELAS ---
if df.empty:
    st.info("Nenhum lançamento encontrado.")
else:
    if st.session_state.menu_opcao == "📊 Razonetes":
        grupos = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        for grupo in grupos:
            df_grupo = df[df['natureza'] == grupo]
            if not df_grupo.empty:
                st.markdown(f"<div class='grupo-header'>{grupo.upper()}</div>", unsafe_allow_html=True)
                contas_grupo = sorted(df_grupo['descricao'].unique())
                cols = st.columns(3)
                for i, conta in enumerate(contas_grupo):
                    with cols[i % 3]:
                        df_c = df_grupo[df_grupo['descricao'] == conta]
                        v_deb_sum, v_cre_sum = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        saldo = (v_deb_sum - v_cre_sum) if grupo in ["Ativo", "Despesa"] else (v_cre_sum - v_deb_sum)
                        deb_html = "".join([f"<div class='valor-item valor-deb'>D: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows()])
                        cre_html = "".join([f"<div class='valor-item valor-cre'>C: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows()])
                        st.markdown(f"""<div class="conta-card"><div class="conta-titulo">{conta}</div>
                                <div class="conta-corpo"><div class="lado-debito">{deb_html}</div><div class="lado-credito">{cre_html}</div></div>
                                <div class="conta-rodape" style="color: {'#059669' if saldo >= 0 else '#dc2626'};">Saldo: R$ {saldo:,.2f}</div></div>""", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("Balancete de Verificação")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito (R$)": d, "Crédito (R$)": c, "Saldo Devedor": d-c if d > c else 0, "Saldo Credor": c-d if c > d else 0})
        st.table(pd.DataFrame(bal_data).style.format(precision=2, decimal=',', thousands='.'))

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 Demonstração do Resultado do Exercício")
        receitas_df = df[df['natureza'] == 'Receita']
        despesas_df = df[df['natureza'] == 'Despesa']
        encargos_df = df[df['natureza'] == 'Encargos Financeiros']
        
        total_receitas = receitas_df[receitas_df['tipo'] == 'Crédito']['valor'].sum() - receitas_df[receitas_df['tipo'] == 'Débito']['valor'].sum()
        total_despesas = despesas_df[despesas_df['tipo'] == 'Débito']['valor'].sum() - despesas_df[despesas_df['tipo'] == 'Crédito']['valor'].sum()
        total_encargos = encargos_df[encargos_df['tipo'] == 'Débito']['valor'].sum() - encargos_df[encargos_df['tipo'] == 'Crédito']['valor'].sum()
        ebitda = total_receitas - total_despesas
        lucro_liquido = ebitda - total_encargos

        with st.expander("Ver Detalhes da DRE", expanded=True):
            st.markdown("### Receitas Operacionais")
            for conta in receitas_df['descricao'].unique():
                val = receitas_df[receitas_df['descricao'] == conta][receitas_df['tipo'] == 'Crédito']['valor'].sum() - receitas_df[receitas_df['descricao'] == conta][receitas_df['tipo'] == 'Débito']['valor'].sum()
                st.markdown(f"<div class='dre-linha'><span>{conta}</span> <span>R$ {val:,.2f}</span></div>", unsafe_allow_html=True)
            st.markdown("### Despesas Operacionais")
            for conta in despesas_df['descricao'].unique():
                val = despesas_df[despesas_df['descricao'] == conta][despesas_df['tipo'] == 'Débito']['valor'].sum() - despesas_df[despesas_df['descricao'] == conta][despesas_df['tipo'] == 'Crédito']['valor'].sum()
                st.markdown(f"<div class='dre-linha'><span>{conta}</span> <span>(R$ {val:,.2f})</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='dre-total dre-linha'><span>EBITDA / Lucro Operacional</span> <span>R$ {ebitda:,.2f}</span></div>", unsafe_allow_html=True)
            cor_lucro = "#059669" if lucro_liquido >= 0 else "#dc2626"
            st.markdown(f"<div class='dre-total dre-linha' style='background-color: {cor_lucro}; color: white;'><span>LUCRO LÍQUIDO</span> <span>R$ {lucro_liquido:,.2f}</span></div>", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Demonstração do Fluxo de Caixa (Por Período)")
        
        # FILTRO DE PERÍODO
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            data_ini = st.date_input("De:", value=df['data_lancamento'].min())
        with col_f2:
            data_fim = st.date_input("Até:", value=datetime.now().date())

        mask = (df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)
        df_periodo = df.loc[mask]

        # Considera status que movimentam caixa efetivamente
        df_realizado = df_periodo[df_periodo['status'].isin(['Pago', 'Entrada', 'Investimento'])].copy()
        
        if df_realizado.empty:
            st.warning("Sem movimentações realizadas no período selecionado.")
        else:
            # Lógica DFC por atividades
            fin_in = df_realizado[(df_realizado['natureza'] == 'Patrimônio Líquido') & (df_realizado['tipo'] == 'Crédito')]['valor'].sum()
            fin_out = df_realizado[(df_realizado['natureza'] == 'Patrimônio Líquido') & (df_realizado['tipo'] == 'Débito')]['valor'].sum()
            op_in = df_realizado[(df_realizado['natureza'] == 'Receita') & (df_realizado['tipo'] == 'Crédito')]['valor'].sum()
            op_out = df_realizado[(df_realizado['natureza'] == 'Despesa') & (df_realizado['tipo'] == 'Débito')]['valor'].sum()
            inv_out = df_realizado[(df_realizado['natureza'] == 'Ativo') & (df_realizado['tipo'] == 'Débito') & (~df_realizado['descricao'].str.contains('CAIXA|BANCO', case=False))]['valor'].sum()
            inv_in = df_realizado[(df_realizado['natureza'] == 'Ativo') & (df_realizado['tipo'] == 'Crédito') & (~df_realizado['descricao'].str.contains('CAIXA|BANCO', case=False))]['valor'].sum()

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
                <div class="conta-card">
                    <div class="conta-titulo">1. Atividades Operacionais</div>
                    <div class="dre-linha"><span>(+) Recebimentos</span> <span>R$ {op_in:,.2f}</span></div>
                    <div class="dre-linha"><span>(-) Pagamentos</span> <span>(R$ {op_out:,.2f})</span></div>
                    <div class="dre-total">Líquido Operacional: R$ {op_in - op_out:,.2f}</div>
                </div>
                <div class="conta-card">
                    <div class="conta-titulo">2. Atividades de Investimento</div>
                    <div class="dre-linha"><span>(+) Venda de Ativos</span> <span>R$ {inv_in:,.2f}</span></div>
                    <div class="dre-linha"><span>(-) Compra de Ativos</span> <span>(R$ {inv_out:,.2f})</span></div>
                    <div class="dre-total">Líquido Investimento: R$ {inv_in - inv_out:,.2f}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="conta-card" style="border-left: 5px solid #059669;">
                    <div class="conta-titulo">3. Atividades de Financiamento</div>
                    <div class="dre-linha"><span>(+) Aportes/Capital</span> <span>R$ {fin_in:,.2f}</span></div>
                    <div class="dre-linha"><span>(-) Saídas de Capital</span> <span>(R$ {fin_out:,.2f})</span></div>
                    <div class="dre-total">Líquido Financiamento: R$ {fin_in - fin_out:,.2f}</div>
                </div>
                <div class="conta-card" style="background: #1e293b; color: white;">
                    <div class="conta-titulo" style="background: #0f172a;">Variação Total no Período</div>
                    <div class="dre-linha" style="padding:15px"><span>Saldo Realizado</span> <span>R$ {(op_in-op_out)+(inv_in-inv_out)+(fin_in-fin_out):,.2f}</span></div>
                </div>""", unsafe_allow_html=True)

        st.divider()
        st.subheader("📅 Pendências e Previsões (Período Selecionado)")
        df_pendente = df_periodo[df_periodo['status'] == 'Pendente']
        st.dataframe(df_pendente[['data_lancamento', 'descricao', 'natureza', 'valor', 'justificativa']], use_container_width=True)

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("⚙️ Gestão de Lançamentos")
        # Mantendo os botões de Reset e a listagem de edição/exclusão
        if st.button("⚠️ Resetar Todos os Lançamentos", use_container_width=True):
            if st.session_state.confirm_reset:
                supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("Clique novamente para confirmar.")
        
        st.divider()
        for _, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([5, 1, 1])
                with c1:
                    st.markdown(f"**[{row['data_lancamento']}] {row['descricao']}** - R$ {row['valor']:,.2f} ({row['status']})")
                if c2.button("✏️", key=f"ed_{row['id']}"):
                    st.session_state.edit_id = row['id']
                    st.rerun()
                if c3.button("🗑️", key=f"del_{row['id']}"):
                    supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                    st.rerun()
                st.divider()
