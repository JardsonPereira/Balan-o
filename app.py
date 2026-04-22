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
        st.markdown("""
            <style>
            .conta-card { background: #ffffff; border: 1px solid #dfe3e8; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
            .conta-titulo { background: #f4f6f8; padding: 10px; text-align: center; font-weight: bold; border-bottom: 2px solid #202124; border-radius: 8px 8px 0 0; }
            .conta-corpo { display: flex; min-height: 80px; }
            .lado-debito { flex: 1; padding: 10px; border-right: 1px solid #dfe3e8; }
            .lado-credito { flex: 1; padding: 10px; }
            .valor-item { font-size: 0.85rem; margin-bottom: 2px; }
            .valor-deb { color: #1e7e34; }
            .valor-cre { color: #d32f2f; }
            .just-hint { font-size: 0.7rem; color: #637381; font-style: italic; display: block; }
            .conta-rodape { padding: 8px; border-top: 1px solid #202124; text-align: center; font-weight: bold; font-size: 0.9rem; }
            .grupo-header { background-color: #202124; color: white; padding: 5px 15px; border-radius: 5px; margin: 20px 0 10px 0; font-size: 1.1rem; }
            </style>
        """, unsafe_allow_html=True)

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
                        saldo = v_deb_sum - v_cre_sum
                        deb_html = "".join([f"<div class='valor-item valor-deb'>D: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows()])
                        cre_html = "".join([f"<div class='valor-item valor-cre'>C: {r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows()])
                        txt_saldo = f"Saldo D: R$ {saldo:,.2f}" if saldo > 0 else f"Saldo C: R$ {abs(saldo):,.2f}" if saldo < 0 else "Zerada"
                        cor_saldo = "#1e7e34" if saldo > 0 else "#d32f2f" if saldo < 0 else "#212529"
                        st.markdown(f"""
                            <div class="conta-card">
                                <div class="conta-titulo">{conta}</div>
                                <div class="conta-corpo"><div class="lado-debito">{deb_html}</div><div class="lado-credito">{cre_html}</div></div>
                                <div class="conta-rodape" style="color: {cor_saldo};">{txt_saldo}</div>
                            </div>
                        """, unsafe_allow_html=True)

    elif opcao_menu == "🧾 Balancete":
        st.subheader("Balancete de Verificação de Saldos")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Saldo Devedor": d-c if d>c else 0, "Saldo Credor": c-d if c>d else 0})
        
        bal_df = pd.DataFrame(bal_data)
        
        # Estilização profissional do Balancete
        styled_bal = bal_df.style.format({
            "Saldo Devedor": "R$ {:,.2f}",
            "Saldo Credor": "R$ {:,.2f}"
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#202124'), ('color', 'white'), ('text-align', 'center'), ('font-weight', 'bold')]},
            {'selector': 'td', 'props': [('text-align', 'right'), ('padding', '10px')]},
            {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#f8f9fa')]}
        ], overwrite=False)

        st.table(styled_bal)
        
        t_dev, t_cre = bal_df["Saldo Devedor"].sum(), bal_df["Saldo Credor"].sum()
        col_b1, col_b2 = st.columns(2)
        col_b1.metric("Total de Saldos Devedores", f"R$ {t_dev:,.2f}", delta=None)
        col_b2.metric("Total de Saldos Credores", f"R$ {t_cre:,.2f}", delta=None)
        
        if round(t_dev, 2) == round(t_cre, 2):
            st.success("✅ O Balancete está equilibrado (Débitos = Créditos)")
        else:
            st.error("❌ O Balancete está desequilibrado! Verifique seus lançamentos.")

    elif opcao_menu == "📈 DRE":
        st.subheader("Demonstração do Resultado")
        df_rec = df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum()
        df_des = df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum()
        df_enc = df[df['natureza'] == 'Encargos Financeiros'].groupby('descricao')['valor'].sum()
        rec_total, des_total, enc_total = df_rec.sum(), df_des.sum(), df_enc.sum()
        ebitda = rec_total - des_total
        lucro_real = ebitda - enc_total
        with st.expander(f"(=) RECEITA BRUTA OPERACIONAL: R$ {rec_total:,.2f}", expanded=True):
            for nome, valor in df_rec.items(): st.write(f"   (+) {nome}: R$ {valor:,.2f}")
        with st.expander(f"(-) DESPESAS OPERACIONAIS: R$ {-des_total:,.2f}", expanded=False):
            for nome, valor in df_des.items(): st.write(f"   (-) {nome}: R$ {valor:,.2f}")
        st.info(f"**(=) EBITDA (LAJIDA): R$ {ebitda:,.2f}**")
        with st.expander(f"(-) RESULTADO FINANCEIRO: R$ {-enc_total:,.2f}", expanded=False):
            for nome, valor in df_enc.items(): st.write(f"   (-) {nome}: R$ {valor:,.2f}")
        st.success(f"### **(=) LUCRO REAL LÍQUIDO: R$ {lucro_real:,.2f}**")

    elif opcao_menu == "⚙️ Gestão":
        st.subheader("Gestão do Sistema")
        if st.button("⚠️ Resetar Todos os Lançamentos", type="secondary"):
            if st.session_state.get('confirm_reset'):
                supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
                st.session_state.confirm_reset = False
                st.success("Dados apagados.")
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("Clique novamente para confirmar a limpeza TOTAL.")
        st.divider()
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            c1.write(f"**{row['descricao']}** | {row['natureza']} | R$ {row['valor']:,.2f}")
            if row['justificativa']: c1.info(f"📝 {row['justificativa']}")
            if c2.button("Editar", key=f"ed_{row['id']}"):
                st.session_state.edit_id = row['id']
                st.rerun()
            if c3.button("Excluir", key=f"del_{row['id']}"):
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
            st.divider()
else:
    st.info("Aguardando lançamentos.")
