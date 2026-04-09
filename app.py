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

# 4. Processamento e Exibição
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    
    # 5. RAZONETES DETALHADOS
    st.header("📊 Razonetes (Movimentações)")
    contas = df['Descrição'].unique()
    
    cols_raz = st.columns(2)
    resumo_balancete = []

    for i, conta in enumerate(contas):
        with cols_raz[i % 2]:
            st.markdown(f"### {conta}")
            df_c = df[df['Descrição'] == conta]
            
            debitos = df_c[df_c['Tipo'] == 'Débito']['Valor'].tolist()
            creditos = df_c[df_c['Tipo'] == 'Crédito']['Valor'].tolist()
            
            max_len = max(len(debitos), len(creditos))
            debitos += [None] * (max_len - len(debitos))
            creditos += [None] * (max_len - len(creditos))
            
            st.table(pd.DataFrame({"Débito (D)": debitos, "Crédito (C)": creditos}).fillna("-"))
            
            tot_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
            tot_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
            
            saldo_d = max(0.0, tot_d - tot_c)
            saldo_c = max(0.0, tot_c - tot_d)
            
            resumo_balancete.append({
                'Conta': conta,
                'Natureza': df_c['Natureza'].iloc[0],
                'Saldo Devedor': saldo_d,
                'Saldo Credor': saldo_c
            })
            
            if saldo_d > 0:
                st.write(f"**Saldo Final:** R$ {saldo_d:,.2f} (Devedor)")
            else:
                st.write(f"**Saldo Final:** R$ {saldo_c:,.2f} (Credor)")
            st.divider()

    # 6. BALANCETE DE VERIFICAÇÃO (Resultado Final Solicitado)
    st.header("🏁 Balancete de Verificação")
    df_final = pd.DataFrame(resumo_balancete)
    
    # Exibe a tabela comparativa final
    st.table(df_final[['Conta', 'Natureza', 'Saldo Devedor', 'Saldo Credor']].style.format({
        'Saldo Devedor': 'R$ {:,.2f}',
        'Saldo Credor': 'R$ {:,.2f}'
    }))

    # Totais Finais
    total_devedor = df_final['Saldo Devedor'].sum()
    total_credor = df_final['Saldo Credor'].sum()

    col_res_d, col_res_c = st.columns(2)
    col_res_d.metric("TOTAL DEVEDOR", f"R$ {total_devedor:,.2f}")
    col_res_c.metric("TOTAL CREDOR", f"R$ {total_credor:,.2f}")

    if round(total_devedor, 2) == round(total_credor, 2):
        st.success("✅ O Balancete está equilibrado!")
    else:
        st.error("❌ Atenção: Existe uma diferença entre os saldos!")

    # 7. GESTÃO
    with st.expander("⚙️ Ver Histórico / Deletar"):
        for index, row in df.iterrows():
            c_inf, c_del = st.columns([5, 1])
            c_inf.write(f"{row['Descrição']} | {row['Tipo']} | R$ {row['Valor']:,.2f}")
            if c_del.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df[df['ID'] != row['ID']]
                st.rerun()
else:
    st.info("Aguardando lançamentos.")
