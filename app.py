import streamlit as st
import pandas as pd

# 1. Configuração de Página - Essencial para Mobile
st.set_page_config(
    page_title="Balancete Mobile", 
    layout="centered", # 'centered' costuma ser melhor para leitura em pé no celular
    initial_sidebar_state="collapsed" # Começa fechado para ganhar espaço
)

st.title("📑 Contabilidade Digital")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor']
    )
    st.session_state.id_cont = 0

# 3. Formulário Adaptativo na Barra Lateral
with st.sidebar:
    st.header("➕ Novo Lançamento")
    with st.form("form_mobile", clear_on_submit=True):
        desc = st.text_input("Conta")
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        if st.form_submit_button("Confirmar", use_container_width=True):
            if desc:
                novo = pd.DataFrame([{
                    'ID': st.session_state.id_cont,
                    'Descrição': desc.upper().strip(),
                    'Natureza': natureza,
                    'Tipo': tipo,
                    'Valor': valor
                }])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.session_state.id_cont += 1
                st.toast("Lançado!", icon="✅")
                st.rerun()

# 4. Conteúdo Principal
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    
    # Resumo em Cartões (Ótimo para Mobile)
    st.subheader("📊 Resumo Atual")
    c1, c2 = st.columns(2)
    tot_d = df[df['Tipo'] == 'Débito']['Valor'].sum()
    tot_c = df[df['Tipo'] == 'Crédito']['Valor'].sum()
    c1.metric("Total Débitos", f"R$ {tot_d:,.2f}")
    c2.metric("Total Créditos", f"R$ {tot_c:,.2f}")

    # --- SEÇÃO: BALANCETE (Tabela Responsiva) ---
    st.divider()
    st.subheader("🏁 Balancete de Verificação")
    
    contas = sorted(df['Descrição'].unique())
    resumo = []
    for conta in contas:
        df_c = df[df['Descrição'] == conta]
        v_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
        v_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
        resumo.append({
            'Conta': conta,
            'D': max(0.0, v_d - v_c),
            'C': max(0.0, v_c - v_d)
        })
    
    df_bal = pd.DataFrame(resumo)
    # st.dataframe com use_container_width permite scroll lateral no celular
    st.dataframe(df_bal, use_container_width=True, hide_index=True)

    # --- SEÇÃO: RAZONETES (Lista Empilhada) ---
    st.divider()
    with st.expander("🔍 Ver Razonetes Detalhados"):
        for conta in contas:
            st.markdown(f"**Conta: {conta}**")
            df_detalhe = df[df['Descrição'] == conta][['Tipo', 'Valor']]
            st.dataframe(df_detalhe, use_container_width=True, hide_index=True)
            st.divider()

    # --- SEÇÃO: GESTÃO (Toque amigável) ---
    with st.expander("⚙️ Gerenciar Lançamentos"):
        # Usamos uma lista mais simples para facilitar o clique no celular
        for index, row in df.iterrows():
            col_txt, col_btn = st.columns([4, 1])
            col_txt.write(f"{row['Descrição']} - R$ {row['Valor']:,.2f}")
            if col_btn.button("🗑️", key=f"del_{index}"):
                st.session_state.lancamentos = df.drop(index)
                st.rerun()

    if st.button("🚨 Resetar Sistema", use_container_width=True):
        st.session_state.clear()
        st.rerun()
else:
    st.info("Abra o menu lateral (>) para lançar.")
