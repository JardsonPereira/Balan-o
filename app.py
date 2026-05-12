import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="ContabilApp - Sistema Integrado", layout="wide")

# Limpeza de cache para garantir que os dados apareçam imediatamente
st.cache_data.clear()

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

# --- FUNÇÃO CARREGAR DADOS ---
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

# --- AUTENTICAÇÃO ---
if st.session_state.user is None:
    st.sidebar.title("🔐 Acesso")
    menu = st.sidebar.radio("Escolha", ["Login", "Criar Conta"])
    email = st.sidebar.text_input("E-mail").lower().strip()
    senha = st.sidebar.text_input("Senha", type="password")
    if menu == "Login" and st.sidebar.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
            st.session_state.user = res.user
            st.rerun()
        except: st.sidebar.error("E-mail ou senha incorretos.")
    elif menu == "Criar Conta" and st.sidebar.button("Cadastrar"):
        supabase.auth.sign_up({"email": email, "password": senha})
        st.sidebar.success("Conta criada!")
    st.stop()

# Carregamento Base
df_base = carregar_dados(st.session_state.user.id)

# --- FORMULÁRIO LATERAL ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.user.email}**")
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()
    st.divider()
    
    if st.session_state.edit_id and not df_base.empty:
        st.header("📝 Editar Lançamento")
        reg = df_base[df_base['id'] == st.session_state.edit_id].iloc[0]
        if st.button("Cancelar Edição"):
            st.session_state.edit_id = None
            st.rerun()
    else:
        st.header("➕ Novo Lançamento")
        reg = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": "", "status": "Pago", "data_lancamento": datetime.now().date()}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df_base['descricao'].unique().tolist()) if not df_base.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        idx_conta = opcoes_conta.index(reg['descricao']) if reg['descricao'] in contas_existentes else 0
        
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        desc_input = st.text_input("Nome da Conta", value=reg['descricao']).upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel
        data_f = st.date_input("Data", value=reg['data_lancamento'])
        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(reg['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if reg['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(reg['valor']))
        op_status = ["Pago", "Entrada", "Pendente", "Investimento", "Transferência Interna"]
        status_pag = st.selectbox("Status", op_status, index=op_status.index(reg['status']) if reg['status'] in op_status else 0)
        just_input = st.text_area("Justificativa", value=reg['justificativa'])
        
        if st.form_submit_button("Confirmar"):
            payload = {"user_id": st.session_state.user.id, "descricao": desc_input, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just_input, "status": status_pag, "data_lancamento": str(data_f)}
            if st.session_state.edit_id:
                supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                st.session_state.edit_id = None
            else:
                supabase.table("lancamentos").insert(payload).execute()
            st.session_state.form_count += 1
            st.rerun()

# --- CSS ---
st.markdown("""<style>
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; border-radius: 12px 12px 0 0; }
    .conta-rodape { padding: 8px; background: #f8fafc; text-align: center; font-weight: 700; border-top: 1px solid #e2e8f0; border-radius: 0 0 12px 12px; }
    .valor-deb { color: #059669; font-size: 0.8rem; padding: 2px 10px; font-weight: 600; }
    .valor-cre { color: #dc2626; font-size: 0.8rem; text-align: right; padding: 2px 10px; font-weight: 600; }
    .just-box { font-size: 0.65rem; color: #64748b; font-style: italic; padding: 0 10px 5px 10px; line-height: 1.1; }
</style>""", unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
st.title("📑 Sistema Contábil Digital")
col_nav = st.columns(5)
opcoes_menu = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes_menu):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()

# --- FILTROS DE DATA ---
f1, f2 = st.columns(2)
with f1: data_ini = st.date_input("Início do Período", value=datetime.now().date().replace(day=1))
with f2: data_fim = st.date_input("Fim do Período", value=datetime.now().date())

# Filtragem Sincronizada
df_periodo = df_base[(df_base['data_lancamento'] >= data_ini) & (df_base['data_lancamento'] <= data_fim)].copy()

# --- CONTEÚDO ---
if df_periodo.empty and st.session_state.menu_opcao != "⚙️ Gestão":
    st.info("Nenhum lançamento no período selecionado.")
else:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for grupo in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df_periodo[df_periodo['natureza'] == grupo]
            if not df_g.empty:
                st.markdown(f"### {grupo}")
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    df_c = df_g[df_g['descricao'] == conta]
                    v_d, v_c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                    saldo = (v_d - v_c) if grupo in ["Ativo", "Despesa", "Encargos Financeiros"] else (v_c - v_d)
                    with cols[i % 3]:
                        st.markdown(f'<div class="conta-card"><div class="conta-titulo">{conta}</div>', unsafe_allow_html=True)
                        c_deb, c_cre = st.columns(2)
                        with c_deb:
                            for _, r in df_c[df_c['tipo']=='Débito'].iterrows():
                                st.markdown(f'<div class="valor-deb">D: {r["valor"]:,.2f}</div><div class="just-box">{r["justificativa"]}</div>', unsafe_allow_html=True)
                        with c_cre:
                            for _, r in df_c[df_c['tipo']=='Crédito'].iterrows():
                                st.markdown(f'<div class="valor-cre">C: {r["valor"]:,.2f}</div><div class="just-box">{r["justificativa"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>', unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("🧾 Balancete de Verificação")
        bal_data = []
        for conta in sorted(df_periodo['descricao'].unique()):
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c, "SD": d-c if d>c else 0, "SC": c-d if c>d else 0})
        df_bal = pd.DataFrame(bal_data)
        st.table(df_bal.style.format(precision=2))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Soma Débitos", f"R$ {df_bal['Débito'].sum():,.2f}")
        c2.metric("Soma Créditos", f"R$ {df_bal['Crédito'].sum():,.2f}")
        c3.metric("Total Devedor (SD)", f"R$ {df_bal['SD'].sum():,.2f}")
        c4.metric("Total Credor (SC)", f"R$ {df_bal['SC'].sum():,.2f}")

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 DRE")
        rec = df_periodo[(df_periodo['natureza'] == 'Receita') & (df_periodo['tipo'] == 'Crédito')]['valor'].sum()
        desp = df_periodo[(df_periodo['natureza'] == 'Despesa') & (df_periodo['tipo'] == 'Débito')]['valor'].sum()
        st.metric("Receita Bruta", f"R$ {rec:,.2f}")
        st.metric("Despesas Operacionais", f"R$ {desp:,.2f}")
        st.info(f"⚡ Resultado Líquido: R$ {rec - desp:,.2f}")

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("💸 Fluxo de Caixa Detalhado")
        
        # Função para calcular saldo histórico (acumulado até o início do período)
        def calc_caixa(limite):
            if df_base.empty: return 0.0
            sub = df_base[df_base['data_lancamento'] <= limite]
            return sub[sub['status'] == "Entrada"]['valor'].sum() - sub[sub['status'] == "Pago"]['valor'].sum()
        
        s_ini = calc_caixa(data_ini - timedelta(days=1))
        
        # Filtrar movimentações específicas do período que afetam o caixa diretamente
        df_fluxo = df_periodo[df_periodo['status'].isin(["Entrada", "Pago"])].copy()
        df_fluxo = df_fluxo.sort_values(by='data_lancamento')
        
        # Métricas Principais
        m1, m2, m3 = st.columns(3)
        total_ent = df_fluxo[df_fluxo['status'] == "Entrada"]['valor'].sum()
        total_sai = df_fluxo[df_fluxo['status'] == "Pago"]['valor'].sum()
        s_fin = s_ini + total_ent - total_sai
        
        m1.metric("Saldo Inicial", f"R$ {s_ini:,.2f}")
        m2.metric("Saldo Final", f"R$ {s_fin:,.2f}")
        m3.metric("Fluxo Líquido", f"R$ {total_ent - total_sai:,.2f}", delta=f"{total_ent - total_sai:,.2f}")
        
        st.divider()
        
        # Detalhamento das Entradas e Saídas
        if not df_fluxo.empty:
            st.markdown("### 📋 Histórico de Movimentações (Caixa)")
            
            # Criar colunas para exibição limpa
            df_display = df_fluxo[['data_lancamento', 'descricao', 'status', 'valor', 'justificativa']].copy()
            df_display.columns = ['Data', 'Conta', 'Tipo', 'Valor (R$)', 'Justificativa']
            
            # Formatação visual da tabela
            def color_status(val):
                color = '#059669' if val == 'Entrada' else '#dc2626'
                return f'color: {color}; font-weight: bold'
            
            st.table(df_display.style.format({'Valor (R$)': "{:,.2f}"}).applymap(color_status, subset=['Tipo']))
            st.caption(f"Exibindo {len(df_fluxo)} lançamentos que afetaram o caixa no período.")
        else:
            st.info("Não houve movimentações de Entrada ou Pagamento neste intervalo de datas.")

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        if st.button("🚨 Resetar Tudo"):
            supabase.table("lancamentos").delete().eq("user_id", st.session_state.user.id).execute()
            st.rerun()
        st.divider()
        if not df_base.empty:
            for _, row in df_base.sort_values(by='data_lancamento', ascending=False).iterrows():
                with st.expander(f"{row['data_lancamento']} | {row['descricao']} | R$ {row['valor']}"):
                    ce, cx = st.columns(2)
                    if ce.button("✏️ Editar", key=f"e_{row['id']}"):
                        st.session_state.edit_id = row['id']
                        st.rerun()
                    if cx.button("🗑️ Excluir", key=f"x_{row['id']}"):
                        supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                        st.rerun()
