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
        columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor', 'Justificativa']
    )
    st.session_state.id_cont = 1

# Garantia de colunas para dados antigos
if 'Justificativa' not in st.session_state.lancamentos.columns:
    st.session_state.lancamentos['Justificativa'] = "Sem justificativa."

# 3. Formulário na Barra Lateral
with st.sidebar:
    st.header(f"➕ Lançamento Nº {st.session_state.id_cont}")
    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes = ["-- Selecione uma conta --"] + contas_existentes

    with st.form("form_mobile", clear_on_submit=True):
        escolha_conta = st.selectbox("Escolher Conta", opcoes)
        nova_conta_input = st.text_input("OU Nova Conta").upper().strip()
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        justificativa = st.text_area("Justificativa / Histórico")
        
        if st.form_submit_button("Confirmar Lançamento", use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione uma conta --" else None)
            if nome_final:
                novo = pd.DataFrame([{
                    'ID': st.session_state.id_cont,
                    'Descrição': nome_final,
                    'Natureza': natureza,
                    'Tipo': tipo,
                    'Valor': valor,
                    'Justificativa': justificativa if justificativa else "Nenhuma justificativa informada."
                }])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.session_state.id_cont += 1
                st.rerun()

# 4. Razonetes (CORRIGIDO)
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    contas = sorted(df['Descrição'].unique())

    st.subheader("🔍 Razonetes (Contas T)")
    st.caption("Passe o mouse ou toque no botão para ver a justificativa.")
    
    for conta in contas:
        with st.expander(f"📊 {conta}", expanded=False):
            df_c = df[df['Descrição'] == conta]
            col_esq, col_dir = st.columns(2)
            
            with col_esq:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>DÉBITO</b></p>", unsafe_allow_html=True)
                debitos = df_c[df_c['Tipo'] == 'Débito']
                for _, row in debitos.iterrows():
                    # Usando st.button para evitar erro de HTML no st.write com help
                    st.button(
                        f"R$ {row['Valor']:,.2f} ({row['ID']})", 
                        key=f"btn_d_{row['ID']}",
                        help=f"JUSTIFICATIVA: {row['Justificativa']}",
                        use_container_width=True
                    )
                
            with col_dir:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                creditos = df_c[df_c['Tipo'] == 'Crédito']
                for _, row in creditos.iterrows():
                    st.button(
                        f"R$ {row['Valor']:,.2f} ({row['ID']})", 
                        key=f"btn_c_{row['ID']}",
                        help=f"JUSTIFICATIVA: {row['Justificativa']}",
                        use_container_width=True
                    )

            saldo = debitos['Valor'].sum() - creditos['Valor'].sum()
            st.divider()
            if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
            elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")

    # 5. Diário, Balancete e Resultado (Mantidos)
    st.divider()
    with st.expander("📖 Diário de Lançamentos"):
        st.dataframe(df[['ID', 'Descrição', 'Tipo', 'Valor', 'Justificativa']], use_container_width=True, hide_index=True)

    st.subheader("🏁 Balancete de Verificação")
    resumo_bal = []
    tot_rec, tot_desp = 0.0, 0.0
    for conta in contas:
        df_conta = df[df['Descrição'] == conta]
        nat = df_conta['Natureza'].iloc[0]
        v_d, v_c = df_conta[df_conta['Tipo'] == 'Débito']['Valor'].sum(), df_conta[df_conta['Tipo'] == 'Crédito']['Valor'].sum()
        s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
        resumo_bal.append({'Conta': conta, 'Nat': nat, 'D': s_d, 'C': s_c})
        if nat == "Receita": tot_rec += (v_c - v_d)
        if nat == "Despesa": tot_desp += (v_d - v_c)
    
    st.dataframe(pd.DataFrame(resumo_bal), use_container_width=True, hide_index=True)

    res = tot_rec - tot_desp
    st.latex(rf"Resultado = {tot_rec:,.2f} - {tot_desp:,.2f}")
    st.metric("LUCRO/PREJUÍZO", f"R$ {abs(res):,.2f}", delta=f"{res:,.2f}")

    with st.expander("⚙️ Gerenciar"):
        for index, row in df.iterrows():
            c_txt, c_btn = st.columns([4, 1])
            c_txt.write(f"#{row['ID']} - {row['Descrição']} (R$ {row['Valor']:,.2f})")
            if c_btn.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df.drop(index).reset_index(drop=True)
                st.rerun()
else:
    st.info("Aguardando lançamentos.")
