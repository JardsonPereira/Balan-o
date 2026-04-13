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

# 3. Formulário na Barra Lateral
with st.sidebar:
    st.header("➕ Novo Lançamento")
    
    # Obtém a lista de contas já criadas
    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes_conta = ["-- Nova Conta --"] + contas_existentes

    with st.form("form_mobile", clear_on_submit=True):
        # Seleção de conta existente
        conta_selecionada = st.selectbox("Selecione a Conta", opcoes_conta)
        
        # Campo para nova conta (visível sempre, mas usado se "Nova Conta" for selecionado)
        nova_conta = st.text_input("Ou digite o nome de uma Nova Conta").upper().strip()
        
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento", use_container_width=True):
            # Lógica para definir qual nome de conta usar
            desc_final = nova_conta if conta_selecionada == "-- Nova Conta --" else conta_selecionada
            
            if desc_final:
                novo = pd.DataFrame([{
                    'ID': st.session_state.id_cont,
                    'Descrição': desc_final,
                    'Natureza': natureza,
                    'Tipo': tipo,
                    'Valor': valor
                }])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.session_state.id_cont += 1
                st.toast(f"Lançado em {desc_final}!", icon="✅")
                st.rerun()
            else:
                st.error("Por favor, informe o nome da conta.")

# 4. Exibição dos Razonetes (Visualização em T)
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    contas = sorted(df['Descrição'].unique())

    st.subheader("🔍 Razonetes Ativos")
    
    for conta in contas:
        with st.expander(f"📊 {conta}", expanded=True):
            df_c = df[df['Descrição'] == conta]
            
            # Cabeçalho do Razonete
            col_esq, col_dir = st.columns(2)
            
            with col_esq:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>Débito (D)</b></p>", unsafe_allow_html=True)
                debitos = df_c[df_c['Tipo'] == 'Débito']
                for v in debitos['Valor']:
                    st.write(f"R$ {v:,.2f}")
                tot_d = debitos['Valor'].sum()
            
            with col_dir:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>Crédito (C)</b></p>", unsafe_allow_html=True)
                creditos = df_c[df_c['Tipo'] == 'Crédito']
                for v in creditos['Valor']:
                    st.write(f"R$ {v:,.2f}")
                tot_c = creditos['Valor'].sum()

            # Linha de Totais e Saldo
            st.divider()
            saldo = tot_d - tot_c
            
            c_tot1, c_tot2 = st.columns(2)
            c_tot1.caption(f"Total D: R$ {tot_d:,.2f}")
            c_tot2.caption(f"Total C: R$ {tot_c:,.2f}")

            if saldo > 0:
                st.success(f"**Saldo Devedor: R$ {abs(saldo):,.2f}**")
            elif saldo < 0:
                st.warning(f"**Saldo Credor: R$ {abs(saldo):,.2f}**")
            else:
                st.info("**Saldo Zerado**")

    # 5. Balancete Resumido
    st.divider()
    st.subheader("🏁 Balancete de Verificação")
    
    resumo_balancete = []
    for conta in contas:
        df_c = df[df['Descrição'] == conta]
        v_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
        v_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
        resumo_balancete.append({
            'Conta': conta,
            'Saldo Devedor': max(0.0, v_d - v_c),
            'Saldo Credor': max(0.0, v_c - v_d)
        })
    
    df_resumo = pd.DataFrame(resumo_balancete)
    st.table(df_resumo) # Table é melhor para visualização rápida no mobile

    if st.button("🗑️ Limpar Tudo", use_container_width=True):
        st.session_state.clear()
        st.rerun()
else:
    st.info("Nenhum razonete criado ainda. Use o menu lateral para começar.")
