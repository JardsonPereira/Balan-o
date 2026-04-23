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
st.set_page_config(page_title="Sistema Contábil Pro", layout="wide", initial_sidebar_state="expanded")

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
    st.sidebar.markdown("<h2 style='text-align: center;'>🔐 Portal de Acesso</h2>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegação", ["Login", "Criar Conta"], label_visibility="collapsed")
    st.sidebar.divider()
    email = st.sidebar.text_input("E-mail").lower().strip()
    senha = st.sidebar.text_input("Senha", type="password")
    if menu == "Login":
        if st.sidebar.button("Acessar Sistema", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception: st.sidebar.error("Credenciais inválidas.")
    else:
        if st.sidebar.button("Registrar Conta", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.sidebar.success("Conta criada! Verifique seu e-mail.")
            except Exception as e: st.sidebar.error(f"Erro: {e}")

if st.session_state.user is None:
    gerenciar_acesso()
    st.stop()

user_id = st.session_state.user.id

# --- BARRA LATERAL (GESTÃO DO PERFIL E LANÇAMENTOS) ---
with st.sidebar:
    st.markdown(f"<div style='background-color: #f1f5f9; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 20px;'>"
                f"<small style='color: #64748b;'>Usuário Ativo</small><br><b>{st.session_state.user.email}</b></div>", unsafe_allow_html=True)
    
    if st.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    
    st.divider()
    
    def carregar_dados():
        try:
            res = supabase.table("lancamentos").select("*").eq("user_id", user_id).execute()
            return pd.DataFrame(res.data)
        except Exception: return pd.DataFrame()

    df = carregar_dados()

    # FORMULÁRIO DE ENTRADA
    if st.session_state.edit_id:
        st.subheader("📝 Edição de Lançamento")
        item_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
    else:
        st.subheader("➕ Novo Lançamento")
        item_edit = {"descricao": "", "natureza": "Ativo", "tipo": "Débito", "valor": 0.0, "justificativa": ""}

    with st.form(key=f"contabil_form_{st.session_state.form_count}", clear_on_submit=True):
        contas_existentes = sorted(df['descricao'].unique().tolist()) if not df.empty else []
        opcoes_conta = ["+ Adicionar Nova Conta"] + contas_existentes
        
        idx_conta = 0
        if st.session_state.edit_id and item_edit['descricao'] in contas_existentes:
            idx_conta = opcoes_conta.index(item_edit['descricao'])
            
        conta_sel = st.selectbox("Conta Contábil", opcoes_conta, index=idx_conta)
        
        if conta_sel == "+ Adicionar Nova Conta":
            desc = st.text_input("Nome da Conta", placeholder="EX: CAIXA").upper().strip()
        else:
            desc = conta_sel

        nat_list = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        nat = st.selectbox("Grupo", nat_list, index=nat_list.index(item_edit['natureza']))
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=0 if item_edit['tipo'] == "Débito" else 1, horizontal=True)
        valor = st.number_input("Valor (R$)", min_value=0.0, step=100.0, value=float(item_edit['valor']))
        just = st.text_input("Histórico / Justificativa", value=item_edit['justificativa'])
        
        if st.form_submit_button("Efetuar Lançamento", use_container_width=True):
            if not desc:
                st.error("Nome da conta é obrigatório!")
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
                except Exception as e: st.error(f"Falha ao salvar: {e}")

# --- ESTILO CSS PROFISSIONAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }

    /* Estilização de Cabeçalhos */
    .main-title { color: #0f172a; font-weight: 800; font-size: 2.2rem; margin-bottom: 0.2rem; }
    .sub-title { color: #64748b; margin-bottom: 2rem; font-size: 1rem; }

    /* Cards de Razonetes */
    .conta-card { 
        background: white; border-radius: 12px; border: 1px solid #e2e8f0; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 25px; overflow: hidden; 
    }
    .conta-titulo { 
        background: #1e293b; color: white; padding: 12px; text-align: center; 
        font-weight: 600; font-size: 0.85rem; letter-spacing: 0.5px;
    }
    .conta-corpo { display: flex; min-height: 100px; position: relative; }
    .conta-corpo::after { 
        content: ""; position: absolute; left: 50%; top: 0; bottom: 0; 
        width: 1.5px; background-color: #e2e8f0; 
    }
    .lado-debito, .lado-credito { flex: 1; padding: 12px; }
    
    /* Itens de Lançamento */
    .valor-item { font-size: 0.8rem; margin-bottom: 6px; line-height: 1.3; }
    .valor-deb { color: #10b981; font-weight: 600; }
    .valor-cre { color: #ef4444; font-weight: 600; text-align: right; }
    .just-hint { font-size: 0.65rem; color: #94a3b8; display: block; font-weight: 400; font-style: normal; }
    
    /* Rodapé do Saldo */
    .conta-rodape { 
        padding: 10px; background: #f8fafc; border-top: 1.5px solid #1e293b; 
        text-align: center; font-weight: 700; font-size: 0.85rem; 
    }
    
    /* Grupos */
    .grupo-header { 
        background: #f1f5f9; color: #334155; padding: 8px 16px; border-radius: 8px; 
        margin: 35px 0 15px 0; font-size: 0.9rem; font-weight: 700; 
        border-left: 4px solid #1e293b; text-transform: uppercase;
    }

    /* Botões de Navegação */
    div[data-testid="stHorizontalBlock"] button {
        border-radius: 8px !important; border: 1px solid #e2e8f0 !important;
        background-color: white !important; font-weight: 500 !important;
    }
    div[data-testid="stHorizontalBlock"] button:hover {
        border-color: #3b82f6 !important; color: #3b82f6 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CORPO PRINCIPAL ---
st.markdown('<h1 class="main-title">📑 Sistema Contábil Digital</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Gestão financeira e controladoria em tempo real</p>', unsafe_allow_html=True)

# Menu Superior
col_nav = st.columns(4)
botoes = ["📊 Razonetes", "🧾 Balancete", "📈 DRE", "⚙️ Gestão"]
for i, btn in enumerate(botoes):
    if col_nav[i].button(btn, use_container_width=True):
        st.session_state.menu_opcao = btn

st.divider()

if not df.empty:
    opcao = st.session_state.menu_opcao
    
    if opcao == "📊 Razonetes":
        grupos = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        for grupo in grupos:
            df_g = df[df['natureza'] == grupo]
            if not df_g.empty:
                st.markdown(f"<div class='grupo-header'>{grupo}</div>", unsafe_allow_html=True)
                contas = sorted(df_g['descricao'].unique())
                cols = st.columns(3)
                for i, conta in enumerate(contas):
                    with cols[i % 3]:
                        df_c = df_g[df_g['descricao'] == conta]
                        v_deb = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        v_cre = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        saldo = v_deb - v_cre
                        
                        deb_html = "".join([f"<div class='valor-item valor-deb'>{r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows()])
                        cre_html = "".join([f"<div class='valor-item valor-cre'>{r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows()])
                        
                        txt_saldo = f"SALDO DEVEDOR: R$ {saldo:,.2f}" if saldo > 0 else f"SALDO CREDOR: R$ {abs(saldo):,.2f}" if saldo < 0 else "CONTA ZERADA"
                        cor_saldo = "#10b981" if saldo > 0 else "#ef4444" if saldo < 0 else "#64748b"
                        
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

    elif opcao == "🧾 Balancete":
        st.subheader("Balancete de Verificação")
        bal_data = []
        for conta in sorted(df['descricao'].unique()):
            df_c = df[df['descricao'] == conta]
            d = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
            c = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
            bal_data.append({"Conta": conta, "Natureza": df_c['natureza'].iloc[0], "Débito": d, "Crédito": c, "Saldo Devedor": d-c if d>c else 0, "Saldo Credor": c-d if c>d else 0})
        
        bal_df = pd.DataFrame(bal_data)
        st.dataframe(bal_df.style.format({c: "R$ {:,.2f}" for c in ["Débito", "Crédito", "Saldo Devedor", "Saldo Credor"]}), use_container_width=True)
        
        t1, t2 = st.columns(2)
        t1.metric("Total de Saldos Devedores", f"R$ {bal_df['Saldo Devedor'].sum():,.2f}")
        t2.metric("Total de Saldos Credores", f"R$ {bal_df['Saldo Credor'].sum():,.2f}")

    elif opcao == "📈 DRE":
        st.subheader("Demonstração do Resultado do Exercício")
        rec_t = df[df['natureza'] == 'Receita']['valor'].sum()
        des_t = df[df['natureza'] == 'Despesa']['valor'].sum()
        enc_t = df[df['natureza'] == 'Encargos Financeiros']['valor'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Receita Bruta", f"R$ {rec_t:,.2f}")
        c2.metric("EBITDA", f"R$ {rec_t - des_t:,.2f}", delta_color="normal")
        c3.metric("Lucro Real", f"R$ {rec_t - des_t - enc_t:,.2f}")
        
        with st.expander("Ver Detalhamento da DRE"):
            st.write("**Receitas:**")
            st.json(df[df['natureza'] == 'Receita'].groupby('descricao')['valor'].sum().to_dict())
            st.write("**Despesas Operacionais:**")
            st.json(df[df['natureza'] == 'Despesa'].groupby('descricao')['valor'].sum().to_dict())

    elif opcao == "⚙️ Gestão":
        st.subheader("Administração de Dados")
        tab1, tab2 = st.tabs(["Listagem Detalhada", "Configurações"])
        
        with tab1:
            for idx, row in df.iterrows():
                with st.expander(f"📌 {row['descricao']} - R$ {row['valor']:,.2f} ({row['tipo']})"):
                    st.write(f"**Grupo:** {row['natureza']} | **Data:** {row.get('created_at', 'N/A')}")
                    st.write(f"**Justificativa:** {row['justificativa']}")
                    c1, c2, _ = st.columns([1,1,4])
                    if c1.button("✏️ Editar", key=f"ed_{row['id']}"):
                        st.session_state.edit_id = row['id']
                        st.rerun()
                    if c2.button("🗑️ Excluir", key=f"del_{row['id']}"):
                        supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                        st.rerun()
        
        with tab2:
            st.warning("Atenção: As ações abaixo não podem ser desfeitas.")
            if st.button("🗑️ Resetar Todo o Banco de Dados", use_container_width=True):
                supabase.table("lancamentos").delete().eq("user_id", user_id).execute()
                st.success("Dados resetados com sucesso.")
                st.rerun()

else:
    st.info("Nenhum lançamento registrado. Utilize o painel lateral para começar.")
