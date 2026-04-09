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
            desc = st.text_input("Conta (Ex: Mercadorias)")
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

# 4. Processamento de Dados
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    
    # 5. SEÇÃO DE RAZONETES (T-Accounts)
    st.header("📊 Razonetes")
    contas_unicas = df['Descrição'].unique()
    
    # Exibição em colunas para simular os "T" contábeis
    cols_raz = st.columns(3)
    for i, conta in enumerate(contas_unicas):
        with cols_raz[i % 3]:
            st.markdown(f"**{conta}**")
            df_c = df[df['Descrição'] == conta]
            # Simulação do T
            dados_t = pd.DataFrame({
                'Débito (D)': [df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()],
                'Crédito (C)': [df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()]
            })
            st.table(dados_t)
            
    # Consolidação para Balancete
    resumo = []
    for conta in contas_unicas:
        df_c = df[df['Descrição'] == conta]
        d_total = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
        c_total = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
        resumo.append({
            'Conta': conta,
            'Natureza': df_c['Natureza'].iloc[0],
            'Subgrupo': df_c['Subgrupo'].iloc[0],
            'Saldo_D': max(0.0, d_total - c_total),
            'Saldo_C': max(0.0, c_total - d_total)
        })
    df_res = pd.DataFrame(resumo)

    # 6. BALANÇO PATRIMONIAL (Ativo, Passivo, PL)
    st.divider()
    st.header("📈 Balanço Patrimonial")
    c_at, c_ps, c_pl = st.columns(3)

    with c_at:
        st.info("ATIVO")
        df_a = df_res[df_res['Natureza'] == "Ativo"]
        st.dataframe(df_a[['Conta', 'Subgrupo', 'Saldo_D']], hide_index=True, use_container_width=True)
        st.write(f"**Total Ativo:** R$ {df_a['Saldo_D'].sum():,.2f}")

    with c_ps:
        st.info("PASSIVO")
        df_p = df_res[df_res['Natureza'] == "Passivo"]
        st.dataframe(df_p[['Conta', 'Subgrupo', 'Saldo_C']], hide_index=True, use_container_width=True)
        st.write(f"**Total Passivo:** R$ {df_p['Saldo_C'].sum():,.2f}")

    with c_pl:
        st.info("P. LÍQUIDO")
        df_pl = df_res[df_res['Natureza'] == "Patrimônio Líquido"]
        st.dataframe(df_pl[['Conta', 'Saldo_C']], hide_index=True, use_container_width=True)
        st.write(f"**Total PL:** R$ {df_pl['Saldo_C'].sum():,.2f}")

    # 7. CONTAS DE RESULTADO (DRE Simplificada)
    st.divider()
    st.header("📊 Resultado do Exercício")
    c_rec, c_des = st.columns(2)
    
    with c_rec:
        st.success("RECEITAS")
        df_rec = df_res[df_res['Natureza'] == "Receita"]
        st.table(df_rec[['Conta', 'Saldo_C']])
        
    with c_des:
        st.error("DESPESAS")
        df_des = df_res[df_res['Natureza'] == "Despesa"]
        st.table(df_des[['Conta', 'Saldo_D']])
    
    lucro_prejuizo = df_rec['Saldo_C'].sum() - df_des['Saldo_D'].sum()
    st.metric("Resultado Líquido", f"R$ {lucro_prejuizo:,.2f}")

    # 8. GESTÃO DE LANÇAMENTOS
    st.divider()
    with st.expander("⚙️ Gerenciar / Deletar Lançamentos"):
        for index, row in df.iterrows():
            col_inf, col_del = st.columns([5, 1])
            col_inf.write(f"{row['Descrição']} | {row['Tipo']} | R$ {row['Valor']:,.2f}")
            if col_del.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df[df['ID'] != row['ID']]
                st.rerun()

    if st.button("🚨 Resetar Sistema"):
        st.session_state.clear()
        st.rerun()
else:
    st.info("Aguardando lançamentos para gerar razonetes e resultados.")
