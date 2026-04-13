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
    
    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes_conta = ["-- Nova Conta --"] + contas_existentes

    with st.form("form_mobile", clear_on_submit=True):
        conta_selecionada = st.selectbox("Selecione a Conta", opcoes_conta)
        nova_conta = st.text_input("Ou digite o nome de uma Nova Conta").upper().strip()
        
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento", use_container_width=True):
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

# 4. Exibição dos Razonetes (Contas T)
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

    # 5. BALANCETE DE VERIFICAÇÃO COM NATUREZA E RESULTADO
    st.divider()
    st.subheader("🏁 Balancete de Verificação")
    
    resumo_balancete = []
    tot_receitas = 0.0
    tot_despesas = 0.0

    for conta in contas:
        df_conta = df[df['Descrição'] == conta]
        nat = df_conta['Natureza'].iloc[0] # Pega a natureza definida no cadastro
        
        v_d = df_conta[df_conta['Tipo'] == 'Débito']['Valor'].sum()
        v_c = df_conta[df_conta['Tipo'] == 'Crédito']['Valor'].sum()
        
        saldo_d = max(0.0, v_d - v_c)
        saldo_c = max(0.0, v_c - v_d)
        
        # Acumula para o Resultado (DRE Simplificada)
        if nat == "Receita": tot_receitas += (v_c - v_d)
        if nat == "Despesa": tot_despesas += (v_d - v_c)

        resumo_balancete.append({
            'Conta': conta,
            'Natureza': nat,
            'Saldo D': saldo_d,
            'Saldo C': saldo_c
        })
    
    # Exibe a tabela do Balancete
    df_bal = pd.DataFrame(resumo_balancete)
    st.dataframe(df_bal, use_container_width=True, hide_index=True)

    # 6. APURAÇÃO DO RESULTADO (LUCRO OU PREJUÍZO)
    st.subheader("📈 Apuração do Resultado")
    resultado_final = tot_receitas - tot_despesas
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Receitas", f"R$ {tot_receitas:,.2f}")
    c2.metric("Despesas", f"R$ {tot_despesas:,.2f}")
    
    if resultado_final >= 0:
        c3.metric("LUCRO", f"R$ {resultado_final:,.2f}", delta_color="normal")
        st.success(f"O resultado do período é um Lucro de R$ {resultado_final:,.2f}")
    else:
        c3.metric("PREJUÍZO", f"R$ {abs(resultado_final):,.2f}", delta="-", delta_color="inverse")
        st.error(f"O resultado do período é um Prejuízo de R$ {abs(resultado_final):,.2f}")

    # 7. GESTÃO
    st.divider()
    with st.expander("⚙️ Gerenciar Lançamentos"):
        for index, row in df.iterrows():
            c_info, c_del = st.columns([4, 1])
            c_info.write(f"{row['Descrição']} ({row['Natureza']}): R$ {row['Valor']:,.2f} - {row['Tipo']}")
            if c_del.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df.drop(index).reset_index(drop=True)
                st.rerun()

else:
    st.info("Aguardando lançamentos...")
