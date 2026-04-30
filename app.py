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
        opcoes_status = ["Entrada", "Pendente", "Pago", "Investimento"]
        status_pag = st.selectbox("Status Financeiro", opcoes_status, index=opcoes_status.index(item_edit.get('status', 'Pago')))
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar Lançamento"):
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
    .conta-rodape { padding: 8px; background: #f8fafc; border-top: 1.5px solid #1e293b; text-align: center; font-weight: 700; font-size: 0.85rem; }
    .grupo-header { background: linear-gradient(90deg, #1e293b, #334155); color: white; padding: 10px 15px; border-radius: 8px; margin: 25px 0 10px 0; font-size: 0.95rem; font-weight: 600; }
    .dre-linha { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #e2e8f0; }
    .dre-total { font-weight: 700; background-color: #e2e8f0; padding: 8px 5px; margin-top: 10px; }
</style>""", unsafe_allow_html=True)

st.title("📑 Sistema Contábil Digital")

# --- NAVEGAÇÃO ---
col_nav = st.columns(5)
opcoes = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "💸 Fluxo de Caixa", "⚙️ Gestão"]
for i, op in enumerate(opcoes):
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
                st.markdown(f"<div class='grupo-header'>{grupo.upper()}</div>", unsafe_allow_html=True)
                cols = st.columns(3)
                for i, conta in enumerate(sorted(df_g['descricao'].unique())):
                    df_c = df_g[df_g['descricao'] == conta]
                    v_d, v_c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                    saldo = (v_d - v_c) if grupo in ["Ativo", "Despesa"] else (v_c - v_d)
                    with cols[i % 3]:
                        st.markdown(f"""<div class="conta-card"><div class="conta-titulo">{conta}</div><div class="conta-corpo"><div class="lado-debito">{"".join([f"<div class='valor-item valor-deb'>D: {r['valor']:,.2f}</div>" for _,r in df_c[df_c['tipo']=='Débito'].iterrows()])}</div><div class="lado-credito">{"".join([f"<div class='valor-item valor-cre'>C: {r['valor']:,.2f}</div>" for _,r in df_c[df_c['tipo']=='Crédito'].iterrows()])}</div></div><div class="conta-rodape">Saldo: R$ {saldo:,.2f}</div></div>""", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader(f"🧾 Balancete de Verificação")
        bal_data = []
        for conta in sorted(df_periodo['descricao'].unique()):
            df_c = df_periodo[df_periodo['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Débito": d, "Crédito": c, "Saldo Devedor": d-c if d > c else 0, "Saldo Credor": c-d if c > d else 0})
        bal_df = pd.DataFrame(bal_data)
        st.table(bal_df.style.format(precision=2, decimal=',', thousands='.'))

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("📈 DRE do Período")
        rec = df_periodo[df_periodo['natureza'] == 'Receita']
        desp = df_periodo[df_periodo['natureza'] == 'Despesa']
        enc = df_periodo[df_periodo['natureza'] == 'Encargos Financeiros']
        t_rec = rec[rec['tipo'] == 'Crédito']['valor'].sum() - rec[rec['tipo'] == 'Débito']['valor'].sum()
        t_desp = desp[desp['tipo'] == 'Débito']['valor'].sum() - desp[desp['tipo'] == 'Crédito']['valor'].sum()
        t_enc = enc[enc['tipo'] == 'Débito']['valor'].sum() - enc[enc['tipo'] == 'Crédito']['valor'].sum()
        lucro = t_rec - t_desp - t_enc
        st.markdown(f"<div class='dre-total dre-linha' style='background:{'#059669' if lucro>=0 else '#dc2626'}; color:white;'><span>LUCRO LÍQUIDO</span> <span>R$ {lucro:,.2f}</span></div>", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("🌊 Demonstração do Fluxo de Caixa (Corrigida)")
        
        df_caixa_full = df[df['status'].isin(['Pago', 'Entrada', 'Investimento'])].copy()
        
        def calc_atividades(tdf):
            # 1. Operacional
            op_in = tdf[(tdf['natureza'] == 'Receita') & (tdf['tipo'] == 'Crédito')]['valor'].sum()
            op_out = tdf[(tdf['natureza'] == 'Despesa') & (tdf['tipo'] == 'Débito')]['valor'].sum()
            
            # 2. Financiamento (Aportes de PL e Pagamentos de Dívidas no Passivo)
            fin_in = tdf[(tdf['natureza'] == 'Patrimônio Líquido') & (tdf['tipo'] == 'Crédito')]['valor'].sum()
            fin_out = tdf[(tdf['natureza'] == 'Passivo') & (tdf['tipo'] == 'Débito')]['valor'].sum()
            
            # 3. Investimento (Lógica para anular o que foi financiado e mostrar apenas desembolso real)
            inv_in = tdf[(tdf['natureza'] == 'Ativo') & (tdf['tipo'] == 'Crédito') & (~tdf['descricao'].str.contains('CAIXA|BANCO', case=False))]['valor'].sum()
            
            total_compras_ativo = tdf[(tdf['natureza'] == 'Ativo') & (tdf['tipo'] == 'Débito') & (~tdf['descricao'].str.contains('CAIXA|BANCO', case=False))]['valor'].sum()
            valor_financiado_no_periodo = tdf[(tdf['natureza'] == 'Passivo') & (tdf['tipo'] == 'Crédito')]['valor'].sum()
            
            inv_out = total_compras_ativo - valor_financiado_no_periodo
            if inv_out < 0: inv_out = 0
            
            return op_in, op_out, fin_in, fin_out, inv_in, inv_out

        oi, oo, fi, fo, ii, io = calc_atividades(df_caixa_full[df_caixa_full['data_lancamento'] < data_ini])
        s_ini = (oi - oo) + (fi - fo) + (ii - io)
        
        df_per = df_caixa_full[(df_caixa_full['data_lancamento'] >= data_ini) & (df_caixa_full['data_lancamento'] <= data_fim)]
        op_in, op_out, fin_in, fin_out, inv_in, inv_out = calc_atividades(df_per)
        var_per = (op_in - op_out) + (fin_in - fin_out) + (inv_in - inv_out)

        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo Inicial", f"R$ {s_ini:,.2f}")
        c2.metric("Variação Líquida", f"R$ {var_per:,.2f}", delta=f"{var_per:,.2f}")
        c3.metric("Saldo Final em Caixa", f"R$ {s_ini + var_per:,.2f}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""<div class="conta-card"><div class="conta-titulo">1. Atividades Operacionais</div><div class="dre-linha"><span>(+) Recebimentos</span> <span>R$ {op_in:,.2f}</span></div><div class="dre-linha"><span>(-) Pagamentos</span> <span>(R$ {op_out:,.2f})</span></div><div class="dre-total">Líquido Operacional: R$ {op_in - op_out:,.2f}</div></div>
            <div class="conta-card"><div class="conta-titulo">2. Atividades de Investimento</div><div class="dre-linha"><span>(+) Venda de Ativos</span> <span>R$ {inv_in:,.2f}</span></div><div class="dre-linha"><span>(-) Compra de Ativos (Entrada Real)</span> <span>(R$ {inv_out:,.2f})</span></div><div class="dre-total">Líquido Investimento: R$ {inv_in - inv_out:,.2f}</div></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="conta-card" style="border-left: 5px solid #059669;"><div class="conta-titulo">3. Atividades de Financiamento</div><div class="dre-linha"><span>(+) Aportes/Capital</span> <span>R$ {fin_in:,.2f}</span></div><div class="dre-linha"><span>(-) Amortização Dívidas</span> <span>(R$ {fin_out:,.2f})</span></div><div class="dre-total">Líquido Financiamento: R$ {fin_in - fin_out:,.2f}</div></div>
            <div class="conta-card" style="background: #1e293b; color: white;"><div class="conta-titulo" style="background: #0f172a;">Resumo do Período</div><div class="dre-linha" style="padding:10px"><span>Saldo Final Conciliado</span> <span>R$ {s_ini + var_per:,.2f}</span></div></div>""", unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        st.subheader("⚙️ Gestão de Lançamentos")
        for _, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([5, 1, 1])
                c1.write(f"**[{row['data_lancamento']}] {row['descricao']}** - R$ {row['valor']:,.2f}")
                if c2.button("✏️", key=f"ed_{row['id']}"): st.session_state.edit_id = row['id']; st.rerun()
                if c3.button("🗑️", key=f"del_{row['id']}"): supabase.table("lancamentos").delete().eq("id", row['id']).execute(); st.cache_data.clear(); st.rerun()
