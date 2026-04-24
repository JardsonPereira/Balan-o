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
        # Trava de segurança para a coluna status
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
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        idx_conta = opcoes_conta.index(item_edit['descricao']) if st.session_state.edit_id and item_edit['descricao'] in contas_existentes else 0
        
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        desc = st.text_input("Nome da Nova Conta", value="").upper().strip() if conta_sel == "+ Adicionar Nova Conta" else conta_sel

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

# --- CSS ORIGINAL REINTEGRADO ---
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
    
    entradas = df[(df['status'] == 'Pago') & (df['tipo'] == 'Débito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    saidas = df[(df['status'] == 'Pago') & (df['tipo'] == 'Crédito') & (df['natureza'] == 'Ativo')]['valor'].sum()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Saldo em Caixa (Pago)", f"R$ {entradas - saidas:,.2f}")
    m2.metric("Liquidez Corrente", f"{ac/pc:.2f}" if pc != 0 else "0.00")
    m3.metric("Ativo Circulante", f"R$ {ac:,.2f}")
    m4.metric("Passivo Circulante", f"R$ {pc:,.2f}")

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
                        v_deb_sum = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        v_cre_sum = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        
                        # Lógica de Saldo por Natureza
                        if grupo in ["Ativo", "Despesa"]: saldo = v_deb_sum - v_cre_sum
                        else: saldo = v_cre_sum - v_deb_sum
                        
                        deb_html = "".join([f"<div class='valor-item valor-deb'>D: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows()])
                        cre_html = "".join([f"<div class='valor-item valor-cre'>C: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows()])
                        
                        txt_saldo = f"Saldo: R$ {saldo:,.2f}"
                        cor_saldo = "#059669" if saldo >= 0 else "#dc2626"
                        
                        st.markdown(f"""
                            <div class="conta-card">
                                <div class="conta-titulo">{conta}</div>
                                <div class="conta-corpo">
                                    <div class="lado-debito">{deb_html}</div>
                                    <div class="lado-credito">{cre_html}</div>
                                </div>
                                <div class="conta-rodape" style="color: {cor_saldo};">{txt_saldo}</div>
                            </div>
                        """, unsafe_allow_html=True)

    elif st.session_state.menu_opcao == "🧾 Balancete":
        st.subheader("Balancete de Verificação")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d, c = df_c[df_c['tipo'] == 'Débito']['valor'].sum(), df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Saldo Devedor": d-c if d>c else 0, "Saldo Credor": c-d if c>d else 0})
        st.table(pd.DataFrame(bal_data).style.format(precision=2))

    elif st.session_state.menu_opcao == "📈 DRE":
        st.subheader("Resultado do Exercício")
        rec, des, enc = df[df['natureza'] == 'Receita']['valor'].sum(), df[df['natureza'] == 'Despesa']['valor'].sum(), df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        with st.expander(f"(=) RECEITA BRUTA: R$ {rec:,.2f}", expanded=True):
            for n, v in df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum().items(): st.write(f"• {n}: R$ {v:,.2f}")
        with st.expander(f"(-) DESPESAS: R$ {-des:,.2f}", expanded=True):
            for n, v in df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum().items(): st.write(f"• {n}: R$ {v:,.2f}")
        st.success(f"**(=) LUCRO LÍQUIDO: R$ {rec - des - enc:,.2f}**")

    elif st.session_state.menu_opcao == "💸 Fluxo de Caixa":
        st.subheader("Fluxo de Caixa (Apenas Pagos)")
        st.dataframe(df[df['status'] == 'Pago'][['descricao', 'tipo', 'valor', 'justificativa']], use_container_width=True)

    elif st.session_state.menu_opcao == "⚙️ Gestão":
        for _, row in df.iterrows():
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.write(f"**{row['descricao']}** | R$ {row['valor']:,.2f} ({row['status']})")
            if c2.button("✏️", key=f"ed_{row['id']}"): st.session_state.edit_id = row['id']; st.rerun()
            if c3.button("🗑️", key=f"del_{row['id']}"): supabase.table("lancamentos").delete().eq("id", row['id']).execute(); st.rerun()
