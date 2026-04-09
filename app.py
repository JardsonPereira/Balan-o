import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração de Página
st.set_page_config(page_title="Balancete Pro - Interativo", layout="wide")

st.title("📑 Sistema Contábil Digital Interativo")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Subgrupo', 'Tipo', 'Valor']
    )
    st.session_state.id_cont = 0

# 3. Formulário de Entrada Interativo
with st.sidebar:
    st.header("➕ Novo Lançamento")
    with st.form("form_contabil", clear_on_submit=True):
        desc = st.text_input("Nome da Conta", placeholder="Ex: Caixa")
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        sub = st.selectbox("Subgrupo", ["Circulante", "Não Circulante", "N/A"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        submit = st.form_submit_button("Confirmar Lançamento")
        
        if submit and desc:
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
            st.toast(f"Lançamento em {desc.upper()} realizado!", icon="✅")
            st.rerun()

# 4. Dashboard e Visualização
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    
    # KPIs Rápidos
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    total_ativo = df[df['Natureza'] == 'Ativo']['Valor'].sum()
    total_receita = df[df['Natureza'] == 'Receita']['Valor'].sum()
    
    col_kpi1.metric("Total de Movimentações", len(df))
    col_kpi2.metric("Volume em Ativos", f"R$ {total_ativo:,.2f}")
    col_kpi3.metric("Receitas Registradas", f"R$ {total_receita:,.2f}")

    # Gráfico de Composição
    st.divider()
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        fig_natureza = px.pie(df, values='Valor', names='Natureza', title='Distribuição por Natureza', hole=0.4)
        st.plotly_chart(fig_natureza, use_container_width=True)
        
    with col_graf2:
        # Razonetes Detalhados (Resumo)
        st.subheader("📊 Razonetes Rápidos")
        contas_lista = sorted(df['Descrição'].unique())
        for conta in contas_lista:
            df_c = df[df['Descrição'] == conta]
            t_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
            t_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
            saldo = t_d - t_c
            cor = "blue" if saldo >= 0 else "red"
            st.markdown(f"**{conta}:** <span style='color:{cor}'>R$ {abs(saldo):,.2f}</span>", unsafe_allow_html=True)

    # 5. Balancete Estilizado
    st.divider()
    st.header("🏁 Balancete de Verificação")
    
    resumo_balancete = []
    for conta in contas_lista:
        df_c = df[df['Descrição'] == conta]
        t_d, t_c = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum(), df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
        resumo_balancete.append({
            'Conta': conta,
            'Natureza': df_c['Natureza'].iloc[0],
            'D': max(0.0, t_d - t_c),
            'C': max(0.0, t_c - t_d)
        })
    
    df_balancete = pd.DataFrame(resumo_balancete)
    
    # Estilização Condicional: Verde para Ativo/Receita, Laranja para Passivo/Despesa
    def style_natureza(v):
        if v in ['Ativo', 'Receita']: return 'color: #2e7d32; font-weight: bold;'
        if v in ['Passivo', 'Despesa']: return 'color: #d32f2f; font-weight: bold;'
        return ''

    st.dataframe(
        df_balancete.style.applymap(style_natureza, subset=['Natureza']).format({'D': 'R$ {:,.2f}', 'C': 'R$ {:,.2f}'}),
        use_container_width=True,
        hide_index=True
    )

    # Totais Alinhados
    total_d, total_c = df_balancete['D'].sum(), df_balancete['C'].sum()
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.markdown("**TOTAIS GERAIS**")
    c2.markdown(f"**R$ {total_d:,.2f}**")
    c3.markdown(f"**R$ {total_c:,.2f}**")

    # 6. Gestão de Lançamentos
    st.divider()
    with st.expander("⚙️ Gerenciar / Deletar Lançamentos"):
        for index, row in df.iterrows():
            col_inf, col_del = st.columns([5, 1])
            col_inf.write(f"ID {index} | {row['Descrição']} | {row['Tipo']} | R$ {row['Valor']:,.2f}")
            if col_del.button("🗑️", key=f"btn_{index}"):
                st.session_state.lancamentos = df.drop(index)
                st.rerun()

    if st.button("🚨 Resetar Tudo"):
        st.session_state.clear()
        st.rerun()
else:
    st.info("Utilize a barra lateral para realizar o primeiro lançamento!")
