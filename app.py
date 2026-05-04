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
    .destaque-balancete { background-color: #f1f5f9; border: 2px solid #1e293b; border-radius: 10px; padding: 15px; margin-top: 20px; }
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
    # --- 1. RAZONETES ---
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

    # --- 2. BALANCETE ---
    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("🧾 Balancete de Verificação")
        bal_data = []
        for conta in sorted(df_periodo['descricao'].unique()):
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            sd, sc = (d - c if d > c else 0), (c - d if c > d else 0)
            bal_data.append({"Conta": conta, "Débito (Mov)": d, "Crédito (Mov)": c, "Saldo Devedor": sd, "Saldo Credor": sc})
        
        bal_df = pd.DataFrame(bal_data)
        st.table(bal_df.style.format(precision=2, decimal=',', thousands='.'))

        st.markdown('<div class="destaque-balancete">', unsafe_allow_html=True)
        st.markdown("#### ⚖️ Resultados Consolidados")
        t_d, t_c = bal_df["Débito (Mov)"].sum(), bal_df["Crédito (Mov)"].sum()
        t_sd, t_sc = bal_df["Saldo Devedor"].sum(), bal_df["Saldo Credor"].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Soma Débitos", f"R$ {t_d:,.2f}")
        c2.metric("Soma Créditos", f"R$ {t_c:,.2f}")
        c3.metric("Total Devedor", f"R$ {t_sd:,.2f}")
        c4.metric("Total Credor", f"R$ {t_sc:,.2f}")
        if abs(t_sd - t_sc) < 0.01: st.success("✅ O Balancete está equilibrado.")
        else: st.error(f"⚠️ Desequilíbrio: R$ {abs(t_sd - t_sc):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. DRE ---
    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 DRE Detalhada")
        rec, desp, enc = df_periodo[df_periodo['natureza'] == 'Receita'], df_periodo[df_periodo['natureza'] == 'Despesa'], df_periodo[df_periodo['natureza'] == 'Encargos Financeiros']
        t_rec = rec[rec['tipo'] == 'Crédito']['valor'].sum() - rec[rec['tipo'] == 'Débito']['valor'].sum()
        t_desp = desp[desp['tipo'] == 'Débito']['valor'].sum() - desp[desp['tipo'] == 'Crédito']['valor'].sum()
        t_enc = enc[enc['tipo'] == 'Débito']['valor'].sum() - enc[enc['tipo'] == 'Crédito']['valor'].sum()
        lucro = t_rec - t_desp - t_enc
        st.markdown(f"### LUCRO LÍQUIDO: R$ {lucro:,.2f}")

    # --- 4. FLUXO DE CAIXA (LÓGICA CORRIGIDA) ---
    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Fluxo de Caixa (Impacto no Disponível)")
        contas_fin = ['CAIXA', 'BANCO', 'GIRO']
        
        def calc_saldo_acumulado(data_limite):
            # Filtro de status que movimentam o caixa
            status_movimentam = ["Pago", "Entrada", "Investimento"]
            mask = (df['data_lancamento'] <= data_limite) & \
                   (df['status'].isin(status_movimentam)) & \
                   (~df['status'].isin(["Transferência Interna", "Pendente"]))
            
            saldo = 0.0
            for _, row in df[mask].iterrows():
                # Entradas (Receita C, PL C)
                if row['tipo'] == 'Crédito' and row['natureza'] in ['Receita', 'Patrimônio Líquido']:
                    saldo += row['valor']
                # Saídas (Despesa D, Encargos D, PL D, Crédito no Ativo Financeiro)
                elif row['tipo'] == 'Débito' and row['natureza'] in ['Despesa', 'Encargos Financeiros', 'Patrimônio Líquido']:
                    saldo -= row['valor']
                elif row['tipo'] == 'Crédito' and row['natureza'] == 'Ativo' and any(c in row['descricao'].upper() for c in contas_fin):
                    saldo -= row['valor']
            return saldo

        si = calc_saldo_acumulado(data_ini - timedelta(days=1))
        sf = calc_saldo_acumulado(data_fim)
        variacao = sf - si

        st.columns(3)[0].metric("Saldo Inicial", f"R$ {si:,.2f}")
        st.columns(3)[1].metric("Variação Líquida", f"R$ {variacao:,.2f}", delta=f"{variacao:,.2f}")
        st.columns(3)[2].metric("Saldo Final", f"R$ {sf:,.2f}")
        
        st.divider()
        st.write("### Detalhamento Financeiro do Período")
        
        # Filtro para exibição na tabela
        df_f = df_periodo[
            (df_periodo['status'].isin(["Pago", "Entrada", "Investimento"])) & 
            (~df_periodo['status'].isin(["Transferência Interna", "Pendente"]))
        ]
        
        # Filtro para garantir que mostramos despesas pagas e créditos de ativo
        df_f = df_f[
            (df_f['natureza'].isin(['Receita', 'Despesa', 'Encargos Financeiros', 'Patrimônio Líquido'])) | 
            ((df_f['natureza'] == 'Ativo') & (df_f['tipo'] == 'Crédito'))
        ]

        if not df_f.empty:
            st.dataframe(df_f[['data_lancamento', 'descricao', 'natureza', 'tipo', 'valor', 'justificativa']].rename(columns={'justificativa': 'Observação'}), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma movimentação financeira identificada.")

    # --- 5. GESTÃO ---
    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("⚙️ Gestão")
        with st.expander("🚨 Zona de Perigo"):
            if st.button("🔥 RESETAR TUDO", type="primary"):
                supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
                st.cache_data.clear(); st.rerun()
        for _, row in df.sort_values(by='data_lancamento', ascending=False).iterrows():
            c1, c2, c3 = st.columns([5, 1, 1])
            c1.write(f"**[{row['data_lancamento']}] {row['descricao']}** - R$ {row['valor']:,.2f} | *{row['justificativa']}*")
            if c2.button("✏️", key=f"ed_{row['id']}"): st.session_state.edit_id = row['id']; st.rerun()
            if c3.button("🗑️", key=f"del_{row['id']}"): 
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.cache_data.clear(); st.rerun()
