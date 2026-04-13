import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Balancete Mobile", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

st.title("📑 Contabilidade Digital")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor']
    )
    st.session_state.id_cont = 0

# 3. Formulário na Barra Lateral - FOCO EM ESCOLHA DE CONTA
with st.sidebar:
    st.header("➕ Novo Lançamento")
    
    # Lista de contas já existentes para o Selectbox
    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes = ["-- Selecione uma conta --", "+ Nova Conta"] + contas_existentes

    with st.form("form_mobile", clear_on_submit=True):
        # Opção 1: Escolher conta existente
        escolha_conta = st.selectbox("Escolha a Conta", opcoes)
        
        # Opção 2: Campo de texto (só usado se escolher "+ Nova Conta")
        nova_conta_input = st.text_input("Nome da Nova Conta (se aplicável)").upper().strip()
        
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento", use_container_width=True):
            # Lógica de definição do nome da conta
            nome_final = ""
            if escolha_conta == "+ Nova Conta":
                nome_final = nova_conta_input
            elif escolha_conta != "-- Selecione uma conta --":
                nome_final = escolha_conta
            
            if nome_final:
                novo = pd.DataFrame([{
                    'ID': st.session_state.id_cont,
                    'Descrição': nome_final,
                    'Natureza': natureza,
                    'Tipo': tipo,
                    'Valor': valor
                }])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.session_state.id_cont += 1
                st.toast(f"Lançado em {nome_final}!", icon="✅")
                st.rerun()
            else:
                st.error("Selecione uma conta ou digite o nome de uma nova.")

# 4. Conteúdo Principal: Razonetes (Contas T)
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    contas = sorted(df['Descrição'].unique())

    st.subheader("🔍 Razonetes (Contas T)")
    for conta in contas:
        with st.expander(f"📊 {conta}", expanded=False):
            df_c = df[df['Descrição'] == conta]
            col_esq, col_dir = st.columns(2)
            
            with col_esq:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>DÉBITO</b></p>", unsafe_allow_html=True)
                debitos = df_c[df_c['Tipo'] == 'Débito']
                for v in debitos['Valor']: st.write(f"R$ {v:,.2f}")
                tot_d = debitos['Valor'].sum()
            
            with col_dir:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                creditos = df_c[df_c['Tipo'] == 'Crédito']
                for v in creditos['Valor']: st.write(f"R$ {v:,.2f}")
                tot_c = creditos['Valor'].sum()

            saldo = tot_d - tot_c
            st.divider()
            if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
            elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")
            else: st.info("Saldo Zerado")

    # 5. Balancete de Verificação (Com Natureza e Totais)
    st.divider()
    st.subheader("🏁 Balancete de Verificação")
    
    resumo_bal = []
    tot_receitas, tot_despesas = 0.0, 0.0

    for conta in contas:
        df_conta = df[df['Descrição'] == conta]
        nat = df_conta['Natureza'].iloc[0]
        v_d = df_conta[df_conta['Tipo'] == 'Débito']['Valor'].sum()
        v_c = df_conta[df_conta['Tipo'] == 'Crédito']['Valor'].sum()
        
        s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
        resumo_bal.append({'Conta': conta, 'Natureza': nat, 'Saldo D': s_d, 'Saldo C': s_c})
        
        if nat == "Receita": tot_receitas += (v_c - v_d)
        if nat == "Despesa": tot_despesas += (v_d - v_c)
    
    df_bal = pd.DataFrame(resumo_bal)
    st.dataframe(df_bal, use_container_width=True, hide_index=True)

    # Totais Devedor e Credor
    t_d, t_c = df_bal['Saldo D'].sum(), df_bal['Saldo C'].sum()
    c_b1, c_b2 = st.columns(2)
    c_b1.metric("Total Devedor", f"R$ {t_d:,.2f}")
    c_b2.metric("Total Credor", f"R$ {t_c:,.2f}")

    # 6. Resultado do Período
    st.divider()
    st.subheader("📈 Resultado")
    res = tot_receitas - tot_despesas
    st.metric("LUCRO/PREJUÍZO", f"R$ {res:,.2f}", delta=res)

    # 7. Gestão de Lançamentos (Deletar)
    with st.expander("⚙️ Gerenciar Lançamentos"):
        for index, row in df.iterrows():
            c_txt, c_btn = st.columns([4, 1])
            c_txt.write(f"**{row['Descrição']}**: R$ {row['Valor']:,.2f} ({row['Tipo'][0]})")
            if c_btn.button("🗑️", key=f"del_{index}"):
                st.session_state.lancamentos = df.drop(index).reset_index(drop=True)
                st.rerun()
else:
    st.info("Abra o menu lateral para selecionar ou criar uma conta.")
