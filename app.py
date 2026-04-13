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

# Verificação de segurança para colunas
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

# 4. Razonetes (Visualização Melhorada)
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
                for _, row in df_c[df_c['Tipo'] == 'Débito'].iterrows():
                    # Visualização com Tooltip (Interrogação para indicar info)
                    st.write(f"R$ {row['Valor']:,.2f} <sup>({row['ID']})</sup>", help=f"HISTÓRICO #{row['ID']}: {row['Justificativa']}")
                
            with col_dir:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                for _, row in df_c[df_c['Tipo'] == 'Crédito'].iterrows():
                    st.write(f"R$ {row['Valor']:,.2f} <sup>({row['ID']})</sup>", help=f"HISTÓRICO #{row['ID']}: {row['Justificativa']}")

            saldo = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum() - df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
            st.divider()
            if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
            elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")

    # 5. NOVO: Diário de Justificativas (Tabela Detalhada)
    st.divider()
    with st.expander("📖 Diário de Lançamentos (Ver Detalhes)"):
        st.dataframe(
            df[['ID', 'Descrição', 'Tipo', 'Valor', 'Justificativa']],
            use_container_width=True,
            hide_index=True
        )

    # 6. Balancete de Verificação
    st.subheader("🏁 Balancete de Verificação")
    resumo_bal = []
    tot_receitas, tot_despesas = 0.0, 0.0

    for conta in contas:
        df_conta = df[df['Descrição'] == conta]
        nat = df_conta['Natureza'].iloc[0]
        v_d, v_c = df_conta[df_conta['Tipo'] == 'Débito']['Valor'].sum(), df_conta[df_conta['Tipo'] == 'Crédito']['Valor'].sum()
        s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
        resumo_bal.append({'Conta': conta, 'Nat': nat, 'Saldo D': s_d, 'Saldo C': s_c})
        if nat == "Receita": tot_receitas += (v_c - v_d)
        if nat == "Despesa": tot_despesas += (v_d - v_c)
    
    st.table(pd.DataFrame(resumo_bal))

    # 7. Resultado
    res = tot_receitas - tot_despesas
    st.latex(rf"Resultado = {tot_receitas:,.2f} - {tot_despesas:,.2f}")
    st.metric(label="LUCRO/PREJUÍZO", value=f"R$ {abs(res):,.2f}", delta=f"{res:,.2f}")

    # 8. Gestão
    with st.expander("⚙️ Gerenciar / Excluir"):
        for index, row in df.iterrows():
            c_txt, c_btn = st.columns([4, 1])
            c_txt.write(f"#{row['ID']} - {row['Descrição']} (R$ {row['Valor']:,.2f})")
            if c_btn.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df.drop(index).reset_index(drop=True)
                st.rerun()
else:
    st.info("Aguardando lançamentos no menu lateral.")
