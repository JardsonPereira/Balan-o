import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(page_title="Balancete Pro", layout="wide")

st.title("📑 Balancete e Razonetes")

# 2. Inicialização do Banco de Dados em Memória
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Subgrupo', 'Tipo', 'Valor']
    )
    st.session_state.id_cont = 0

# 3. Formulário de Entrada
with st.expander("➕ Realizar Novo Lançamento", expanded=True):
    with st.form("form_contabil", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            desc = st.text_input("Nome da Conta (Ex: Caixa)")
            natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        with col2:
            sub = st.selectbox("Subgrupo (Se Ativo/Passivo)", ["Circulante", "Não Circulante", "N/A"])
            tipo = st.selectbox("Tipo de Lançamento", ["Débito", "Crédito"])
        
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento"):
            if desc:
                f_sub = sub if natureza in ["Ativo", "Passivo"] else "N/A"
                novo_dado = pd.DataFrame([{
                    'ID': st.session_state.id_cont,
                    'Descrição': desc.upper().strip(),
                    'Natureza': natureza,
                    'Subgrupo': f_sub,
                    'Tipo': tipo,
                    'Valor': valor
                }])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo_dado], ignore_index=True)
                st.session_state.id_cont += 1
                st.rerun()

# 4. Processamento e Exibição de Resultados
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    
    # Cálculo dos Saldos (Razonetes)
    resumo = []
    for conta in df['Descrição'].unique():
        filtro = df[df['Descrição'] == conta]
        debito_total = filtro[filtro['Tipo'] == 'Débito']['Valor'].sum()
        credito_total = filtro[filtro['Tipo'] == 'Crédito']['Valor'].sum()
        s_devedor = max(0.0, debito_total - credito_total)
        s_credor = max(0.0, credito_total - debito_total)
        resumo.append({
            'Conta': conta,
            'Natureza': filtro['Natureza'].iloc[0],
            'Subgrupo': filtro['Subgrupo'].iloc[0],
            'D': s_devedor,
            'C': s_credor
        })
    df_balancete = pd.DataFrame(resumo)

    # 5. Balanço Patrimonial
    st.divider()
    st.subheader("📈 Balanço Patrimonial")
    c_at, c_ps, c_pl = st.columns(3)

    with c_at:
        st.info("**ATIVO**")
        a_c = df_balancete[(df_balancete['Natureza'] == "Ativo") & (df_balancete['Subgrupo'] == "Circulante")]
        a_nc = df_balancete[(df_balancete['Natureza'] == "Ativo") & (df_balancete['Subgrupo'] == "Não Circulante")]
        if not a_c.empty: 
            st.write("Circulante")
            st.table(a_c[['Conta', 'D']])
        if not a_nc.empty: 
            st.write("Não Circulante")
            st.table(a_nc[['Conta', 'D']])
        st.write(f"**Total Ativo:** R$ {a_c['D'].sum() + a_nc['D'].sum():,.2f}")

    with c_ps:
        st.info("**PASSIVO**")
        p_c = df_balancete[(df_balancete['Natureza'] == "Passivo") & (df_balancete['Subgrupo'] == "Circulante")]
        p_nc = df_balancete[(df_balancete['Natureza'] == "Passivo") & (df_balancete['Subgrupo'] == "Não Circulante")]
        if not p_c.empty: 
            st.write("Circulante")
            st.table(p_c[['Conta', 'C']])
        if not p_nc.empty: 
            st.write("Não Circulante")
            st.table(p_nc[['Conta', 'C']])
        st.write(f"**Total Passivo:** R$ {p_c['C'].sum() + p_nc['C'].sum():,.2f}")

    with c_pl:
        st.info("**PATRIMÔNIO LÍQUIDO**")
        pl_d = df_balancete[df_balancete['Natureza'] == "Patrimônio Líquido"]
        if not pl_d.empty: 
            st.table(pl_d[['Conta', 'C']])
        st.write(f"**Total PL:** R$ {pl_d['C'].sum():,.2f}")

    # 6. Verificação de Equilíbrio
    st.divider()
    tot_d, tot_c = df_balancete['D'].sum(), df_balancete['C'].sum()
    if round(tot_d, 2) == round(tot_c, 2):
        st.success(f"✅ Balancete Fechado: R${tot_d:,.2f}")
    else:
        st.error(f"❌ Desequilíbrio! D: R${tot_d:,.2f} | C: R${tot_c:,.2f}")

    # 7. GESTÃO DE LANÇAMENTOS (Onde estava o erro de identação)
    st.divider()
    st.subheader("⚙️ Gestão de Lançamentos")
    st.write("Remover lançamentos individuais:")
    
    for index, row in df.iterrows():
        col_info, col_btn = st.columns([5, 1])
        with col_info:
            st.write(f"**{row['Descrição']}** | {row['Tipo']}: R$ {row['Valor']:,.2f}")
        with col_btn:
            # O botão deve estar exatamente aqui, identado dentro do 'with'
            if st.button("🗑️", key=f"del_{row['ID']}"):
                st.session_state.lancamentos = df[df['ID'] != row['ID']]
                st.rerun()

    # Botão para Limpar Tudo
    if st.button("🚨 Resetar Tudo"):
        st.session_state.lancamentos = pd.DataFrame(columns=['ID', 'Descrição', 'Natureza', 'Subgrupo', 'Tipo', 'Valor'])
        st.session_state.id_cont = 0
        st.rerun()

else:
    st.warning("Aguardando lançamentos...")
