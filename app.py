import streamlit as st
import pandas as pd

# 1. Configuração para Celular
st.set_page_config(
    page_title="Balancete Mobile",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📑 Balancete Pro")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor'])
    st.session_state.id_cont = 0

# 3. Interface de Entrada
with st.expander("➕ Novo Lançamento", expanded=True):
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

# 4. Painel de Resumo
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    
    resumo = []
    for conta in df['Descrição'].unique():
        d_conta = df[df['Descrição'] == conta]
        deb = d_conta[d_conta['Tipo'] == 'Débito']['Valor'].sum()
        cre = d_conta[d_conta['Tipo'] == 'Crédito']['Valor'].sum()
        nat = d_conta['Natureza'].iloc[0]
        
        saldo_dev = max(0, deb - cre)
        saldo_cre = max(0, cre - deb)
        resumo.append({'Conta': conta, 'Natureza': nat, 'Devedor': saldo_dev, 'Credor': saldo_cre})
    
    # Criamos o DataFrame do Balancete
    df_balancete = pd.DataFrame(resumo)
    
    # Organização: Contas Patrimoniais primeiro, depois Resultado
    df_balancete['Ordem'] = df_balancete['Natureza'].map({
        "Ativo": 1, "Passivo": 2, "Patrimônio Líquido": 3, "Receita": 4, "Despesa": 5
    })
    df_balancete = df_balancete.sort_values('Ordem').drop(columns=['Ordem'])

    total_dev = df_balancete['Devedor'].sum()
    total_cre = df_balancete['Credor'].sum()

    st.subheader("📊 Totais")
    col1, col2 = st.columns(2)
    col1.metric("Devedor", f"R${total_dev:,.2f}")
    col2.metric("Credor", f"R${total_cre:,.2f}")

    # 5. Balancete Unificado
    st.divider()
    st.subheader("📈 Balancete de Verificação")
    
    # Exibe a tabela única com todas as contas
    st.dataframe(df_balancete, use_container_width=True, hide_index=True)

    # 6. Gerenciar
    st.divider()
    with st.expander("⚙️ Ver/Deletar Lançamentos Individuais"):
        for i, row in df.iterrows():
            c_txt, c_btn = st.columns([4, 1])
            c_txt.write(f"{row['Descrição']} ({row['Tipo']}) | R${row['Valor']:.2f}")
            if c_btn.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df[df['ID'] != row['ID']]
                st.rerun()
                
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Backup", csv, "balancete.csv", "text/csv", use_container_width=True)

else:
    st.info("Toque no '+' para começar.")
