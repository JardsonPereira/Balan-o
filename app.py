import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(page_title="Balancete Pro", layout="wide")

st.title("📑 Sistema Contábil Digital")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Subgrupo', 'Tipo', 'Valor']
    )
    st.session_state.id_cont = 0

# 3. Formulário de Entrada
with st.expander("➕ Novo Lançamento", expanded=True):
    with st.form("form_contabil", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            desc = st.text_input("Conta (Ex: Banco)")
            natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        with col2:
            sub = st.selectbox("Subgrupo", ["Circulante", "Não Circulante", "N/A"])
            tipo = st.selectbox("Operação", ["Débito", "Crédito"])
        
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        if st.form_submit_button("Lançar"):
            if desc:
                f_sub = sub if natureza in ["Ativo", "Passivo"] else "N/A"
                novo = pd.DataFrame([{
                    'ID': st.session_state.id_cont,
                    'Descrição': desc.upper().strip(),
                    'Natureza': natureza,
                    'Subgrupo': f_sub,
                    'Tipo': tipo,
                    'Valor': valor
                }])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.session_state.id_cont += 1
                st.rerun()

# 4. Processamento
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    contas = df['Descrição'].unique()
    resumo_balancete = []

    # Processamento dos Razonetes (Oculto ou Exibido conforme preferir)
    for conta in contas:
        df_c = df[df['Descrição'] == conta]
        tot_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
        tot_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
        
        resumo_balancete.append({
            'Conta': conta,
            'Natureza': df_c['Natureza'].iloc[0],
            'Saldo Devedor': max(0.0, tot_d - tot_c),
            'Saldo Credor': max(0.0, tot_c - tot_d)
        })

    # 5. BALANCETE DE VERIFICAÇÃO COM TOTAIS ALINHADOS
    st.header("🏁 Balancete de Verificação")
    df_final = pd.DataFrame(resumo_balancete)
    
    # Totais
    total_d = df_final['Saldo Devedor'].sum()
    total_c = df_final['Saldo Credor'].sum()

    # Exibição da Tabela principal
    st.table(df_final[['Conta', 'Natureza', 'Saldo Devedor', 'Saldo Credor']].style.format({
        'Saldo Devedor': 'R$ {:,.2f}',
        'Saldo Credor': 'R$ {:,.2f}'
    }))

    # Criando a linha de totalização visualmente alinhada
    # Usamos colunas para "empurrar" os totais para baixo das colunas corretas
    col_label, col_nat, col_tot_d, col_tot_c = st.columns([2, 1, 1, 1])
    
    with col_label:
        st.markdown("**TOTAL GERAL**")
    with col_tot_d:
        st.markdown(f"**R$ {total_d:,.2f}**")
    with col_tot_c:
        st.markdown(f"**R$ {total_c:,.2f}**")

    # Alerta de Equilíbrio
    if round(total_d, 2) == round(total_c, 2):
        st.success("✅ Partidas Dobradas verificadas: Débitos e Créditos em equilíbrio.")
    else:
        st.error(f"❌ Erro de Equilíbrio: Diferença de R$ {abs(total_d - total_c):,.2f}")

    # 6. GESTÃO / RAZONETES (Opcional - Exibição compacta)
    with st.expander("🔍 Ver Razonetes Detalhados"):
        for conta in contas:
            df_c = df[df['Descrição'] == conta]
            st.write(f"**{conta}**")
            st.dataframe(df_c[['Tipo', 'Valor']], hide_index=True)

    with st.expander("⚙️ Gerenciar / Deletar Lançamentos"):
        for index, row in df.iterrows():
            c_inf, c_del = st.columns([5, 1])
            c_inf.write(f"{row['Descrição']} | {row['Tipo']} | R$ {row['Valor']:,.2f}")
            if c_del.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df[df['ID'] != row['ID']]
                st.rerun()
else:
    st.info("Aguardando lançamentos.")
