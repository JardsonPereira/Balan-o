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

# 3. Formulário de Entrada na Barra Lateral
with st.sidebar:
    st.header("➕ Novo Lançamento")
    with st.form("form_contabil", clear_on_submit=True):
        desc = st.text_input("Nome da Conta")
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        sub = st.selectbox("Subgrupo", ["Circulante", "Não Circulante", "N/A"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        if st.form_submit_button("Confirmar Lançamento"):
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
                st.toast(f"Lançado: {desc.upper()}", icon="✅")
                st.rerun()

# 4. Dashboard e Balancete
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    contas_lista = sorted(df['Descrição'].unique())

    # Visualização Gráfica Nativa (Não precisa de Plotly)
    st.subheader("📊 Composição por Natureza")
    chart_data = df.groupby('Natureza')['Valor'].sum()
    st.bar_chart(chart_data)

    # --- SEÇÃO: BALANCETE ---
    st.divider()
    st.header("🏁 Balancete de Verificação")
    
    resumo = []
    for conta in contas_lista:
        df_c = df[df['Descrição'] == conta]
        t_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
        t_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
        resumo.append({
            'Conta': conta,
            'Natureza': df_c['Natureza'].iloc[0],
            'D': max(0.0, t_d - t_c),
            'C': max(0.0, t_c - t_d)
        })
    
    df_bal = pd.DataFrame(resumo)
    st.dataframe(df_bal, use_container_width=True, hide_index=True)

    # Totais Alinhados
    td, tc = df_bal['D'].sum(), df_bal['C'].sum()
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.markdown("**TOTAIS**")
    c2.write(f"**R$ {td:,.2f}**")
    c3.write(f"**R$ {tc:,.2f}**")

    # --- SEÇÃO: GESTÃO ---
    st.divider()
    with st.expander("⚙️ Gerenciar Lançamentos"):
        for index, row in df.iterrows():
            col_inf, col_del = st.columns([5, 1])
            col_inf.write(f"{row['Descrição']} | {row['Tipo']} | R$ {row['Valor']:,.2f}")
            if col_del.button("🗑️", key=f"del_{index}"):
                st.session_state.lancamentos = df.drop(index)
                st.rerun()

    if st.button("🚨 Resetar Tudo"):
        st.session_state.clear()
        st.rerun()
else:
    st.info("Aguardando lançamentos na barra lateral.")
