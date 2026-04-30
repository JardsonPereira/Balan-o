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
        
        data_f = st.date_input("Data do Lançamento", value=item_edit.get('data_lancamento', datetime.now().date()))
        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        
        # AJUSTE NO STATUS: Unificado para garantir o salvamento
        opcoes_status = ["Pago", "Entrada", "Pendente", "Investimento", "Transferência Interna"]
        status_pag = st.selectbox("Status Financeiro", opcoes_status, index=opcoes_status.index(item_edit['status']) if item_edit['status'] in opcoes_status else 0)
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar Lançamento"):
            if desc == "" or desc == "+ ADICIONAR NOVA CONTA":
                st.error("Informe o nome da conta.")
            else:
                payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just, "status": status_pag, "data_lancamento": str(data_f)}
                if st.session_state.edit_id:
                    supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                    st.session_state.edit_id = None
                else:
                    supabase.table("lancamentos").insert(payload).execute()
                st.cache_data.clear()
                st.session_state.form_count += 1
                st.rerun()

# --- CSS ---
st.markdown("""<style>
    .conta-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; overflow: hidden; border: 1px solid #e2e8f0; }
    .conta-titulo { background: #1e293b; color: white; padding: 10px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; border-bottom: 2px solid #334155; }
    .conta-corpo { display: flex; min-height: 80px; position: relative; }
    .conta-corpo::after { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1.5px; background-color: #cbd5e1; }
    .lado-debito, .lado-credito { flex: 1; padding: 10px; }
    .valor-deb { color: #059669; font-weight: 600; font-size: 0.8rem; }
    .valor-cre { color: #dc2626; font-weight: 600; text-align: right; font-size: 0.8rem; }
    .just-hint { font-size: 0.7rem; color: #64748b; font-style: italic; display: block; }
    .conta-rodape { padding: 8px; background: #f8fafc; border-top: 1.5px solid #1e293b; text-align: center; font-weight: 700; font-size: 0.85rem; }
    .dre-linha { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #e2e8f0; }
    .dre-total { font-weight: 700; background-color: #e2e8f0; padding: 8px 5px; margin-top: 10px; }
</style>""", unsafe_allow_html=True)

st.title("📑 Sistema Contábil Digital")

# --- NAVEGAÇÃO ---
col_nav = st.columns(5)
opcoes_menu = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes_menu):
    if col_nav[i].button(op, use_container_width=True): st.session_state.menu_opcao = op

st.divider()
f1, f2 = st.columns(2)
with f1: data_ini = st.date_input("Início do Período", value=datetime.now().date().replace(day=1))
with f2: data_fim = st.date_input("Fim do Período", value=datetime.now().date())

df_periodo = df[(df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)] if not df.empty else df

if df.empty:
    st.info("Nenhum lançamento encontrado.")
else:
    if st.session_state.menu_opcao == "📊 Razonetes":
        for grupo in ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]:
            df_g = df[df['natureza'] == grupo]
            if not df_g.empty:
                st.markdown(f"### {grupo}")
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    df_c = df_g[df_g['descricao'] == conta]
                    v_d, v_c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                    saldo = (v_d - v_c) if grupo in ["Ativo", "Despesa", "Encargos Financeiros"] else (v_c - v_d)
                    deb_html = "".join([f"<div class='valor-deb'>D: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _,r in df_c[df_c['tipo']=='Débito'].iterrows()])
                    cre_html = "".join([f"<div class='valor-cre'>C: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _,r in df_c[df_c['tipo']=='Crédito'].iterrows()])
                    with cols[i % 3]:
                        st.markdown(f"""<div class="conta-card"><div class="conta-titulo">{conta}</div><div class="conta-corpo"><div class="lado-debito">{deb_html}</div><div class="lado-credito">{cre_html}</div></div><div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>""", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("🧾 Balancete de Verificação")
        bal_data = []
        for conta in sorted(df_periodo['descricao'].unique()):
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c, "Saldo Devedor": d-c if d > c else 0, "Saldo Credor": c-d if c > d else 0})
        bal_df = pd.DataFrame(bal_data)
        st.table(bal_df.style.format(precision=2, decimal=',', thousands='.'))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Débitos", f"R$ {bal_df['Débito'].sum():,.2f}")
        c2.metric("Total Créditos", f"R$ {bal_df['Crédito'].sum():,.2f}")
        c3.metric("Saldo Devedor", f"R$ {bal_df['Saldo Devedor'].sum():,.2f}")
        c4.metric("Saldo Credor", f"R$ {bal_df['Saldo Credor'].sum():,.2f}")

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Fluxo de Caixa")
        # Filtro de liquidez ignora Transferência Interna
        status_l = ["Pago", "Entrada", "Investimento"]
        
        def get_giro(target_df, data_lim):
            df_hist = target_df[(target_df['data_lancamento'] <= data_lim) & (target_df['status'].isin(status_l))]
            saldo = 0.0
            for _, r in df_hist.iterrows():
                if r['natureza'] in ['Receita', 'Patrimônio Líquido'] and r['tipo'] == 'Crédito': saldo += r['valor']
                elif r['tipo'] == 'Crédito' and r['natureza'] not in ['Receita', 'Patrimônio Líquido']: saldo -= r['valor']
                elif r['natureza'] in ['Despesa', 'Passivo', 'Encargos Financeiros'] and r['tipo'] == 'Débito': saldo -= r['valor']
            return saldo

        sf = get_giro(df, data_fim); si = get_giro(df, data_ini - timedelta(days=1))
        df_per = df[(df['status'].isin(status_l)) & (df['data_lancamento'] >= data_ini) & (df['data_lancamento'] <= data_fim)]
        ent_op = df_per[df_per['natureza'] == 'Receita'][df_per['tipo'] == 'Crédito']['valor'].sum()
        ent_pl = df_per[df_per['natureza'] == 'Patrimônio Líquido'][df_per['tipo'] == 'Crédito']['valor'].sum()
        sai_op = df_per[df_per['natureza'] == 'Despesa'][df_per['tipo'] == 'Débito']['valor'].sum()
        sai_pas = df_per[df_per['natureza'] == 'Passivo'][df_per['tipo'] == 'Débito']['valor'].sum()
        sai_enc = df_per[df_per['natureza'] == 'Encargos Financeiros'][df_per['tipo'] == 'Débito']['valor'].sum()
        sai_atv = df_per[(df_per['natureza'] == 'Ativo') & (df_per['tipo'] == 'Crédito')]['valor'].sum()
        
        e_total, s_total = ent_op + ent_pl, sai_op + sai_pas + sai_enc + sai_atv
        prop = (e_total / s_total) if s_total > 0 else (e_total if e_total > 0 else 0)

        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo Inicial", f"R$ {si:,.2f}")
        c2.metric("Variação", f"R$ {sf-si:,.2f}", delta=f"{sf-si:,.2f}")
        c3.metric("Saldo Final", f"R$ {sf:,.2f}")
        
        st.info(f"Liquidez: {'COM LIQUIDEZ' if e_total > s_total else 'DÉFICIT'} | Proporção: {prop:.2f}x")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""<div class="conta-card"><div class="conta-titulo">📥 Entradas Reais</div><div class="dre-linha"><span>(+) Receitas Operacionais</span> <span>R$ {ent_op:,.2f}</span></div><div class="dre-linha"><span>(+) Aportes de Capital (PL)</span> <span>R$ {ent_pl:,.2f}</span></div><div class="dre-total">Total Entradas: R$ {e_total:,.2f}</div></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="conta-card" style="border-left: 5px solid #dc2626;"><div class="conta-titulo">out Saídas Reais</div><div class="dre-linha"><span>(-) Despesas Operacionais</span> <span>R$ {sai_op:,.2f}</span></div><div class="dre-linha"><span>(-) Passivo (Pagamentos)</span> <span>R$ {sai_pas:,.2f}</span></div><div class="dre-linha"><span>(-) Encargos Financeiros</span> <span>R$ {sai_enc:,.2f}</span></div><div class="dre-linha"><span>(-) Créditos em Ativo</span> <span>R$ {sai_atv:,.2f}</span></div><div class="dre-total">Total Saídas: (R$ {s_total:,.2f})</div></div>""", unsafe_allow_html=True)

        st.subheader("📑 Disponibilidades")
        contas_dispo = df[(df['natureza'] == 'Ativo') & (df['descricao'].str.contains('CAIXA|BANCO', case=False))]['descricao'].unique()
        if len(contas_dispo) > 0:
            cols = st.columns(len(contas_dispo))
            for idx, c_nome in enumerate(sorted(contas_dispo)):
                df_c = df[(df['descricao'] == c_nome) & (df['data_lancamento'] <= data_fim)]
                saldo_c = df_c[df_c['tipo'] == 'Débito']['valor'].sum() - df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                with cols[idx]: st.metric(c_nome, f"R$ {saldo_c:,.2f}")

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 DRE")
        rec, desp, enc = df_periodo[df_periodo['natureza'] == 'Receita'], df_periodo[df_periodo['natureza'] == 'Despesa'], df_periodo[df_periodo['natureza'] == 'Encargos Financeiros']
        t_rec = rec[rec['tipo'] == 'Crédito']['valor'].sum() - rec[rec['tipo'] == 'Débito']['valor'].sum()
        t_desp = desp[desp['tipo'] == 'Débito']['valor'].sum() - desp[desp['tipo'] == 'Crédito']['valor'].sum()
        t_enc = enc[enc['tipo'] == 'Débito']['valor'].sum() - enc[enc['tipo'] == 'Crédito']['valor'].sum()
        st.metric("Lucro Líquido", f"R$ {t_rec - t_desp - t_enc:,.2f}")

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("⚙️ Gestão")
        ordem = st.selectbox("Ordenar por:", ["Mais recentes", "Mais antigos"])
        df_gestao = df.sort_values(by='data_lancamento', ascending=(ordem == "Mais antigos"))
        for _, row in df_gestao.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([5, 1, 1])
                c1.markdown(f"**[{row['data_lancamento']}] {row['descricao']}** - R$ {row['valor']:,.2f} ({row['tipo']})")
                if c2.button("✏️", key=f"ed_{row['id']}"): st.session_state.edit_id = row['id']; st.rerun()
                if c3.button("🗑️", key=f"del_{row['id']}"): supabase.table("lancamentos").delete().eq("id", row['id']).execute(); st.cache_data.clear(); st.rerun()
