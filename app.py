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

# 3. Formulário de Entrada (Simples e Direto)
with st.expander("➕ Novo Lançamento", expanded=True):
    with st.form("form_contabil", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            desc = st.text_input("Conta (Ex: Caixa, Banco, Estoque)")
            natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        with col2:
            sub = st.selectbox("Subgrupo", ["Circulante", "Não Circulante", "N/A"])
            tipo = st.selectbox("Operação", ["Débito", "Crédito"])
        
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
    contas_unicas = sorted(df['Descrição'].unique())
    
    # --- SEÇÃO 1: RAZONETES (T) DETALHADOS ---
    st.header("📊 Razonetes (T)")
    cols_raz = st.columns(2)
    resumo_balancete = []

    for i, conta in enumerate(contas_unicas):
        with cols_raz[i % 2]:
            st.subheader(f"Conta: {conta}")
            df_c = df[df['Descrição'] == conta]
            
            # Listagem de movimentações individuais
            debitos = df_c[df_c['Tipo'] == 'Débito']['Valor'].tolist()
            creditos = df_c[df_c['Tipo'] == 'Crédito']['Valor'].tolist()
            
            max_len = max(len(debitos), len(creditos))
            debitos += [None] * (max_len - len(debitos))
            creditos += [None] * (max_len - len(creditos))
            
            st.table(pd.DataFrame({"Débito (D)": debitos, "Crédito (C)": creditos}).fillna("-"))
            
            # Cálculos de Saldo
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
            st.divider()

    # --- SEÇÃO 2: BALANCETE DE VERIFICAÇÃO ---
    st.header("🏁 Balancete de Verificação")
    df_balancete = pd.DataFrame(resumo_balancete)
    
    st.table(df_balancete[['Conta', 'Natureza', 'Saldo Devedor', 'Saldo Credor']].style.format({
        'Saldo Devedor': 'R$ {:,.2f}',
        'Saldo Credor': 'R$ {:,.2f}'
    }))

    # Totais Alinhados
    total_devedor = df_balancete['Saldo Devedor'].sum()
    total_credor = df_balancete['Saldo Credor'].sum()
    
    c_label, c_nat, c_res_d, c_res_c = st.columns([2, 1, 1, 1])
    c_label.markdown("**TOTAL GERAL**")
    c_res_d.markdown(f"**R$ {total_devedor:,.2f}**")
    c_res_c.markdown(f"**R$ {total_credor:,.2f}**")

    if round(total_devedor, 2) == round(total_credor, 2):
        st.success("✅ Balancete em equilíbrio!")
    else:
        st.error("❌ Desequilíbrio entre Débitos e Créditos!")

    # --- SEÇÃO 3: GESTÃO DE LANÇAMENTOS ---
    st.divider()
    with st.expander("⚙️ Gerenciar Lançamentos"):
        for index, row in df.iterrows():
            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.write(f"ID {int(row['ID'])} | **{row['Descrição']}** | {row['Tipo']}: R$ {row['Valor']:,.2f}")
            with col_btn:
                if st.button("🗑️", key=f"del_{index}"):
                    st.session_state.lancamentos = df.drop(index)
                    st.rerun()

    if st.button("🚨 Resetar Tudo"):
        st.session_state.clear()
        st.rerun()
else:
    st.info("Aguardando lançamentos...")
