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
st.set_page_config(page_title="Sistema Contábil Integrado", layout="wide")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro de conexão. Verifique as Secrets no Streamlit Cloud.")
    st.stop()

# --- ESTADOS DO SISTEMA ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None
if 'form_count' not in st.session_state:
    st.session_state.form_count = 0
if 'menu_opcao' not in st.session_state:
    st.session_state.menu_opcao = "📊 Razonetes"

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
st.sidebar.write(f"👤 **{st.session_state.user.email}**")
if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

def carregar_dados():
    try:
        res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
        return pd.DataFrame(res.data)
    except Exception: return pd.DataFrame()

df = carregar_dados()

# --- FORMULÁRIO COM RESET AUTOMÁTICO ---
with st.sidebar:
    st.divider()
    if st.session_state.edit_id:
        st.header("📝 Editar")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.header("➕ Novo")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"contabil_form_{st.session_state.form_count}"):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        
        idx_conta = 0
        if st.session_state.edit_id and item_edit['descricao'] in contas_existentes:
            idx_conta = opcoes_conta.index(item_edit['descricao'])
            
        conta_sel = st.selectbox("Selecione a Conta", opcoes_conta, index=idx_conta)
        
        if conta_sel == "+ Adicionar Nova Conta":
            desc = st.text_input("Nome da Nova Conta", value="").upper().strip()
        else:
            desc = conta_sel

        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=float(item_edit['valor']))
        just = st.text_area("Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Confirmar Lançamento"):
            if not desc:
                st.error("Informe o nome da conta!")
            else:
                payload = {"user_id": user_id, "descricao": desc, "natureza": nat, "tipo": tipo, "valor": valor, "justificativa": just}
                try:
                    if st.session_state.edit_id:
                        supabase.table("lancamentos").update(payload).eq("id", st.session_state.edit_id).execute()
                        st.session_state.edit_id = None
                    else:
                        supabase.table("lancamentos").insert(payload).execute()
                    
                    st.session_state.form_count += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

# --- INTERFACE PRINCIPAL ---
st.title("📑 Sistema Contábil Digital")

# --- CSS PARA RESPONSIVIDADE MOBILE ---
st.markdown("""
    <style>
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] { display: flex; flex-wrap: wrap; gap: 5px; }
        div[data-testid="column"] { min-width: calc(50% - 5px) !important; flex: 1 1 calc(50% - 5px) !important; }
        .stMetric { padding: 5px !important; }
    }
    .conta-card { background: #ffffff; border: 1px solid #dfe3e8; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; width: 100%; }
    .conta-titulo { background: #f4f6f8; padding: 10px; text-align: center; font-weight: bold; border-bottom: 2px solid #202124; border-radius: 8px 8px 0 0; }
    .conta-corpo { display: flex; min-height: 60px; }
    .lado-debito { flex: 1; padding: 8px; border-right: 1px solid #dfe3e8; }
    .lado-credito { flex: 1; padding: 8px; }
    .valor-item { font-size: 0.8rem; margin-bottom: 4px; line-height: 1.2; }
    .valor-deb { color: #1e7e34; font-weight: bold; }
    .valor-cre { color: #d32f2f; font-weight: bold; }
    .just-hint { font-size: 0.65rem; color: #637381; font-style: italic; display: block; }
    .conta-rodape { padding: 8px; border-top: 1px solid #202124; text-align: center; font-weight: bold; font-size: 0.85rem; }
    .grupo-header { background-color: #202124; color: white; padding: 8px 15px; border-radius: 5px; margin: 25px 0 10px 0; font-size: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- MENU LADO A LADO ---
col_nav = st.columns(4)
if col_nav[0].button("📊 Razonetes", use_container_width=True): st.session_state.menu_opcao = "📊 Razonetes"
if col_nav[1].button("🧾 Balancete", use_container_width=True): st.session_state.menu_opcao = "🧾 Balancete"
if col_nav[2].button("📈 DRE", use_container_width=True): st.session_state.menu_opcao = "📈 DRE"
if col_nav[3].button("⚙️ Gestão", use_container_width=True): st.session_state.menu_opcao = "⚙️ Gestão"

opcao_menu = st.session_state.menu_opcao
st.divider()

if not df.empty:
    if opcao_menu == "📊 Razonetes":
        grupos = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        for grupo in grupos:
            df_grupo = df[df['natureza'] == grupo]
            if not df_grupo.empty:
                st.markdown(f"<div class='grupo-header'>{grupo.upper()}</div>", unsafe_allow_html=True)
                contas_grupo = sorted(df_grupo['descricao'].unique())
                cols = st.columns(3)
                for i, conta in enumerate(contas_grupo):
                    with cols[i % 3 if st.get_option("browser.gatherUsageStats") else 0]:
                        df_c = df_grupo[df_grupo['descricao'] == conta]
                        v_deb_sum = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        v_cre_sum = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        saldo = v_deb_sum - v_cre_sum
                        deb_html = "".join([f"<div class='valor-item valor-deb'>D: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows()])
                        cre_html = "".join([f"<div class='valor-item valor-cre'>C: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows()])
                        txt_saldo = f"Saldo D: R$ {saldo:,.2f}" if saldo > 0 else f"Saldo C: R$ {abs(saldo):,.2f}" if saldo < 0 else "Zerada"
                        cor_saldo = "#1e7e34" if saldo > 0 else "#d32f2f" if saldo < 0 else "#212529"
                        st.markdown(f"""<div class="conta-card"><div class="conta-titulo">{conta}</div><div class="conta-corpo"><div class="lado-debito">{deb_html}</div><div class="lado-credito">{cre_html}</div></div><div class="conta-rodape" style="color: {cor_saldo};">{txt_saldo}</div></div>""", unsafe_allow_html=True)

    elif opcao_menu == "🧾 Balancete":
        st.subheader("Balancete de Verificação")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Saldo Devedor": d-c if d>c else 0, "Saldo Credor": c-d if c>d else 0})
        bal_df = pd.DataFrame(bal_data)
        st.table(bal_df.style.format({"Saldo Devedor": "R$ {:,.2f}", "Saldo Credor": "R$ {:,.2f}"}).set_table_styles([{'selector': 'th', 'props': [('background-color', '#202124'), ('color', 'white')]}]))
        t_dev, t_cre = bal_df["Saldo Devedor"].sum(), bal_df["Saldo Credor"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Total Devedores", f"R$ {t_dev:,.2f}")
        c2.metric("Total Credores", f"R$ {t_cre:,.2f}")

    elif opcao_menu == "📈 DRE":
        st.subheader("Resultado do Exercício")
        df_rec = df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum()
        df_des = df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum()
        df_enc = df[df['natureza'] == 'Encargos Financeiros'].groupby('descricao')['valor'].sum()
        rec_t, des_t, enc_t = df_rec.sum(), df_des.sum(), df_enc.sum()
        ebitda, lucro = rec_t - des_t, (rec_t - des_t) - enc_t
        with st.expander(f"(=) RECEITA BRUTA: R$ {rec_t:,.2f}", expanded=True):
            for n, v in df_rec.items(): st.write(f"• {n}: R$ {v:,.2f}")
        with st.expander(f"(-) DESPESAS: R$ {-des_t:,.2f}", expanded=False):
            for n, v in df_des.items(): st.write(f"• {n}: R$ {v:,.2f}")
        st.info(f"**(=) EBITDA: R$ {ebitda:,.2f}**")
        with st.expander(f"(-) FINANCEIRO: R$ {-enc_t:,.2f}", expanded=False):
            for n, v in df_enc.items(): st.write(f"• {n}: R$ {v:,.2f}")
        st.success(f"**(=) LUCRO REAL: R$ {lucro:,.2f}**")

    elif opcao_menu == "⚙️ Gestão":
        st.subheader("Gestão")
        if st.button("⚠️ Resetar Tudo", use_container_width=True):
            if st.session_state.get('confirm_reset'):
                supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("Clique novamente para confirmar.")
        st.divider()
        for idx, row in df.iterrows():
            with st.container():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['descricao']}** ({row['natureza']})")
                c1.caption(f"R$ {row['valor']:,.2f} | {row['tipo']}")
                if row['justificativa']: st.caption(f"📝 {row['justificativa']}")
                b1, b2 = st.columns(2)
                if b1.button("✏️", key=f"ed_{row['id']}", use_container_width=True):
                    st.session_state.edit_id = row['id']; st.rerun()
                if b2.button("🗑️", key=f"del_{row['id']}", use_container_width=True):
                    supabase.table("lancamentos").delete().eq("id", row['id']).execute(); st.rerun()
                st.divider()
else:
    st.info("Aguardando lançamentos.")
