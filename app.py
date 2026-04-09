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
    
    # Grid de Razonetes
    cols_raz = st.columns(2) # Duas colunas para melhor leitura detalhada
    for i, conta in enumerate(contas):
        with cols_raz[i % 2]:
            st.markdown(f"### {conta}")
            df_c = df[df['Descrição'] == conta]
            
            # Criando a tabela de movimentação detalhada
            debitos = df_c[df_c['Tipo'] == 'Débito']['Valor'].tolist()
            creditos = df_c[df_c['Tipo'] == 'Crédito']['Valor'].tolist()
            
            # Alinhando as listas para a tabela (preenchendo com vazio onde não houver valor)
            max_len = max(len(debitos), len(creditos))
            debitos += [None] * (max_len - len(debitos))
            creditos += [None] * (max_len - len(creditos))
            
            df_t = pd.DataFrame({
                "Débito (D)": debitos,
                "Crédito (C)": creditos
            })
            
            # Exibe o "T"
            st.table(df_t.fillna("-"))
            
            # Cálculo do Saldo do Razonete
            tot_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
            tot_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
            saldo = tot_d - tot_c
            
            if saldo >= 0:
                st.write(f"**Saldo Devedor:** R$ {saldo:,.2f}")
            else:
                st.write(f"**Saldo Credor:** R$ {abs(saldo):,.2f}")
            st.divider()

    # 6. CONTA DE RESULTADO E BALANCETE (Consolidado)
    resumo = []
    for conta in contas:
        df_c = df[df['Descrição'] == conta]
        d_tot = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
        c_tot = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
        resumo.append({
            'Conta': conta,
            'Natureza': df_c['Natureza'].iloc[0],
            'Subgrupo': df_c['Subgrupo'].iloc[0],
            'Saldo_D': max(0.0, d_tot - c_tot),
            'Saldo_C': max(0.0, c_tot - d_tot)
        })
    df_res = pd.DataFrame(resumo)

    # Exibição Simplificada do Resultado
    st.header("📊 Resultado do Exercício")
    lucro = df_res[df_res['Natureza']=="Receita"]['Saldo_C'].sum() - df_res[df_res['Natureza']=="Despesa"]['Saldo_D'].sum()
    st.metric("Lucro/Prejuízo Líquido", f"R$ {lucro:,.2f}")

    # 7. GESTÃO DE LANÇAMENTOS
    with st.expander("⚙️ Ver Histórico / Deletar"):
        for index, row in df.iterrows():
            c_inf, c_del = st.columns([5, 1])
            c_inf.write(f"ID {row['ID']} | {row['Descrição']} | {row['Tipo']} | R$ {row['Valor']:,.2f}")
            if c_del.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df[df['ID'] != row['ID']]
                st.rerun()
else:
    st.info("Lance um valor para visualizar o detalhamento nos razonetes.")
