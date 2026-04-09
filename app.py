import streamlit as st
import pandas as pd

# 1. Configuração para Celular
st.set_page_config(
    page_title="Balancete Mobile",
    layout="wide",
    initial_sidebar_state="collapsed" # Esconde o menu no celular para focar nos dados
)

# Estilo CSS para melhorar a visualização no celular
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    [data-testid="stForm"] { border: none; padding: 0; }
    </style>
    """, unsafe_allow_index=True)

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor'])
    st.session_state.id_cont = 0

# 3. Interface de Entrada (Botão de Adicionar)
with st.expander("➕ Novo Lançamento", expanded=False):
    with st.form("form_contabil", clear_on_submit=True):
        desc = st.text_input("Descrição (Ex: Caixa)")
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.selectbox("Operação", ["Débito", "Crédito"])
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento"):
            if desc and valor > 0:
                novo = pd.DataFrame([{'ID': st.session_state.id_cont, 'Descrição': desc.upper(), 
                                      'Natureza': natureza, 'Tipo': tipo, 'Valor': valor}])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.session_state.id_cont += 1
                st.rerun()

# 4. Painel de Resumo (Métricas)
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    
    # Cálculos de Saldos
    resumo = []
    for conta in df['Descrição'].unique():
        d_conta = df[df['Descrição'] == conta]
        deb = d_conta[d_conta['Tipo'] == 'Débito']['Valor'].sum()
        cre = d_conta[d_conta['Tipo'] == 'Crédito']['Valor'].sum()
        nat = d_conta['Natureza'].iloc[0]
        
        saldo_dev = max(0, deb - cre)
        saldo_cre = max(0, cre - deb)
        resumo.append({'Conta': conta, 'Natureza': nat, 'Devedor': saldo_dev, 'Credor': saldo_cre})
    
    df_balancete = pd.DataFrame(resumo)
    total_dev = df_balancete['Devedor'].sum()
    total_cre = df_balancete['Credor'].sum()

    col1, col2 = st.columns(2)
    col1.metric("Total Devedor", f"R${total_dev:,.2f}")
    col2.metric("Total Credor", f"R${total_cre:,.2f}")

    # 5. Balancete (Patrimoniais e Resultados)
    st.subheader("📈 Balancete")
    
    tab1, tab2 = st.tabs(["Patrimonial", "Resultado"])
    
    with tab1:
        patrimonial = df_balancete[df_balancete['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        st.dataframe(patrimonial, use_container_width=True, hide_index=True)
        
    with tab2:
        resultado = df_balancete[df_balancete['Natureza'].isin(["Receita", "Despesa"])]
        st.dataframe(resultado, use_container_width=True, hide_index=True)

    # 6. Razonetes (Visualização em Cards)
    st.subheader("📑 Razonetes (T)")
    for r in resumo:
        with st.container():
            st.markdown(f"**{r['Conta']}**")
            c_deb, c_cre = st.columns(2)
            c_deb.caption(f"D: R${r['Devedor']:,.2f}")
            c_cre.caption(f"C: R${r['Credor']:,.2f}")
            st.divider()

    # 7. Gerenciar Lançamentos (Deletar)
    with st.expander("⚙️ Gerenciar Lançamentos"):
        for i, row in df.iterrows():
            col_txt, col_btn = st.columns([4, 1])
            col_txt.write(f"{row['Descrição']} | {row['Tipo']} | R${row['Valor']:.2f}")
            if col_btn.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df[df['ID'] != row['ID']]
                st.rerun()
                
    # 8. Salvar Progresso
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Backup (CSV)", csv, "balancete.csv", "text/csv", use_container_width=True)

else:
    st.info("Toque no botão '+' acima para realizar o primeiro lançamento.")