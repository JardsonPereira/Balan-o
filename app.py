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
    st.session_state.id_cont = 1

# Indicador de Total de Lançamentos
if not st.session_state.lancamentos.empty:
    total_registros = len(st.session_state.lancamentos)
    st.markdown(f"**Total de Lançamentos:** `{total_registros}`")

# 3. Formulário na Barra Lateral
with st.sidebar:
    st.header(f"➕ Lançamento Nº {st.session_state.id_cont}")
    
    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes = ["-- Selecione uma conta existente --"] + contas_existentes

    with st.form("form_mobile", clear_on_submit=True):
        escolha_conta = st.selectbox("Escolher Conta Criada", opcoes)
        nova_conta_input = st.text_input("OU Digite uma Nova Conta").upper().strip()
        
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento", use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione uma conta existente --" else None)
            
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
                st.rerun()

# 4. Conteúdo Principal: Razonetes
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
                for _, row in debitos.iterrows():
                    # Efeito de Expoente: Valor acompanhado do ID em subscrito
                    st.markdown(f"R$ {row['Valor']:,.2f} <sup style='color:gray;'>({row['ID']})</sup>", unsafe_allow_html=True)
                tot_d = debitos['Valor'].sum()
            
            with col_dir:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                creditos = df_c[df_c['Tipo'] == 'Crédito']
                for _, row in creditos.iterrows():
                    # Efeito de Expoente: Valor acompanhado do ID em subscrito
                    st.markdown(f"R$ {row['Valor']:,.2f} <sup style='color:gray;'>({row['ID']})</sup>", unsafe_allow_html=True)
                tot_c = creditos['Valor'].sum()

            saldo = tot_d - tot_c
            st.divider()
            if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
            elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")
            else: st.info("Saldo Zerado")

    # 5. Balancete de Verificação
    st.divider()
    st.subheader("🏁 Balancete de Verificação")
    resumo_bal = []
    tot_receitas, tot_despesas = 0.0, 0.0

    for conta in contas:
        df_conta = df[df['Descrição'] == conta]
        nat = df_conta['Natureza'].iloc[0]
        v_d, v_c = df_conta[df_conta['Tipo'] == 'Débito']['Valor'].sum(), df_conta[df_conta['Tipo'] == 'Crédito']['Valor'].sum()
        s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
        resumo_bal.append({'Conta': conta, 'Natureza': nat, 'Saldo D': s_d, 'Saldo C': s_c})
        if nat == "Receita": tot_receitas += (v_c - v_d)
        if nat == "Despesa": tot_despesas += (v_d - v_c)
    
    st.dataframe(pd.DataFrame(resumo_bal), use_container_width=True, hide_index=True)

    t_d, t_c = sum(x['Saldo D'] for x in resumo_bal), sum(x['Saldo C'] for x in resumo_bal)
    col_t1, col_t2 = st.columns(2)
    col_t1.metric("Total Devedor", f"R$ {t_d:,.2f}")
    col_t2.metric("Total Credor", f"R$ {t_c:,.2f}")

    # 6. Resultado do Período
    st.divider()
    res = tot_receitas - tot_despesas
    st.latex(rf"Resultado = {tot_receitas:,.2f} - {tot_despesas:,.2f}")
    st.metric(label="LUCRO/PREJUÍZO", value=f"R$ {abs(res):,.2f}", delta=f"{res:,.2f}")

    # 7. Gestão de Lançamentos
    with st.expander("⚙️ Gerenciar Lançamentos"):
        for index, row in df.iterrows():
            c_txt, c_btn = st.columns([4, 1])
            c_txt.write(f"#{row['ID']} - {row['Descrição']} - R$ {row['Valor']:,.2f}")
            if c_btn.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df.drop(index).reset_index(drop=True)
                st.rerun()
else:
    st.info("Aguardando lançamentos no menu lateral.")
