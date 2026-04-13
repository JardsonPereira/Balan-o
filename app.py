import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Balancete Mobile", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

st.title("📑 Contabilidade Digital")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor']
    )
    st.session_state.id_cont = 0

# 3. Formulário na Barra Lateral
with st.sidebar:
    st.header("➕ Novo Lançamento")
    with st.form("form_mobile", clear_on_submit=True):
        desc = st.text_input("Conta (Ex: Caixa, Estoque)")
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
    contas = sorted(df['Descrição'].unique())

    # --- SEÇÃO: RAZONETES (Visualização em T) ---
    st.subheader("🔍 Razonetes (Contas T)")
    
    for conta in contas:
        with st.expander(f"📖 Conta: {conta}", expanded=True):
            df_c = df[df['Descrição'] == conta]
            
            # Divide a tela em duas colunas para simular o "T"
            col_esq, col_dir = st.columns(2)
            
            with col_esq:
                st.markdown("<p style='text-align:center; font-weight:bold; border-bottom:1px solid black'>Débito (D)</p>", unsafe_allow_html=True)
                debitos = df_c[df_c['Tipo'] == 'Débito']
                for v in debitos['Valor']:
                    st.write(f"R$ {v:,.2f}")
                tot_d = debitos['Valor'].sum()
                st.markdown(f"**Total D: R$ {tot_d:,.2f}**")

            with col_dir:
                st.markdown("<p style='text-align:center; font-weight:bold; border-bottom:1px solid black'>Crédito (C)</p>", unsafe_allow_html=True)
                creditos = df_c[df_c['Tipo'] == 'Crédito']
                for v in creditos['Valor']:
                    st.write(f"R$ {v:,.2f}")
                tot_c = creditos['Valor'].sum()
                st.markdown(f"**Total C: R$ {tot_c:,.2f}**")

            # Cálculo do Saldo Final da Conta
            saldo = tot_d - tot_c
            if saldo > 0:
                st.success(f"**Saldo Devedor: R$ {abs(saldo):,.2f}**")
            elif saldo < 0:
                st.warning(f"**Saldo Credor: R$ {abs(saldo):,.2f}**")
            else:
                st.info("**Saldo Zerado**")

    # --- SEÇÃO: BALANCETE FINAL ---
    st.divider()
    st.subheader("🏁 Balancete de Verificação")
    
    resumo = []
    for conta in contas:
        df_c = df[df['Descrição'] == conta]
        v_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
        v_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
        resumo.append({
            'Conta': conta,
            'Natureza': df_c['Natureza'].iloc[0],
            'Saldo D': max(0.0, v_d - v_c),
            'Saldo C': max(0.0, v_c - v_d)
        })
    
    df_bal = pd.DataFrame(resumo)
    st.dataframe(df_bal, use_container_width=True, hide_index=True)
    
    # Verificação de Equilíbrio
    total_d = df_bal['Saldo D'].sum()
    total_c = df_bal['Saldo C'].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("Total Devedor", f"R$ {total_d:,.2f}")
    c2.metric("Total Credor", f"R$ {total_c:,.2f}")

    if round(total_d, 2) == round(total_c, 2):
        st.success("✅ O Balancete está fechado!")
    else:
        st.error("⚠️ Diferença detectada entre Débitos e Créditos!")

    # --- GESTÃO ---
    st.divider()
    with st.expander("⚙️ Opções"):
        if st.button("🚨 Resetar Tudo", use_container_width=True):
            st.session_state.clear()
            st.rerun()
else:
    st.info("Nenhum lançamento encontrado. Abra o menu lateral (>) para começar.")
