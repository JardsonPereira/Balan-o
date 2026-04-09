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
            desc = st.text_input("Conta (Ex: Caixa)")
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
    contas = sorted(df['Descrição'].unique())
    
    # --- SEÇÃO 1: RAZONETES DETALHADOS COM RASTREABILIDADE ---
    st.header("📊 Razonetes (T) com Origem (#ID)")
    cols_raz = st.columns(2)
    resumo_balancete = []

    for i, conta in enumerate(contas):
        with cols_raz[i % 2]:
            st.subheader(f"Conta: {conta}")
            df_c = df[df['Descrição'] == conta]
            
            # Formatação com ID para identificar a origem
            debitos = []
            creditos = []
            
            for _, row in df_c.iterrows():
                info = f"R$ {row['Valor']:,.2f} (#{int(row['ID'])})"
                if row['Tipo'] == 'Débito':
                    debitos.append(info)
                else:
                    creditos.append(info)
            
            # Alinhamento visual do T
            max_len = max(len(debitos), len(creditos))
            debitos += ["-"] * (max_len - len(debitos))
            creditos += ["-"] * (max_len - len(creditos))
            
            st.table(pd.DataFrame({"Débito (D)": debitos, "Crédito (C)": creditos}))
            
            # Cálculos de Saldo
            t_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
            t_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
            s_d = max(0.0, t_d - t_c)
            s_c = max(0.0, t_c - t_d)
            
            resumo_balancete.append({
                'Conta': conta,
                'Natureza': df_c['Natureza'].iloc[0],
                'Saldo Devedor': s_d,
                'Saldo Credor': s_c
            })
            
            # Exibe o saldo individual abaixo de cada T
            if s_d > 0: st.caption(f"Saldo Devedor: R$ {s_d:,.2f}")
            elif s_c > 0: st.caption(f"Saldo Credor: R$ {s_c:,.2f}")
            else: st.caption("Conta Zerada")
            st.divider()

    # --- SEÇÃO 2: BALANCETE DE VERIFICAÇÃO ---
    st.header("🏁 Balancete de Verificação")
    df_final = pd.DataFrame(resumo_balancete)
    
    st.table(df_final[['Conta', 'Natureza', 'Saldo Devedor', 'Saldo Credor']].style.format({
        'Saldo Devedor': 'R$ {:,.2f}',
        'Saldo Credor': 'R$ {:,.2f}'
    }))

    # Linha de Totais Alinhada
    total_d = df_final['Saldo Devedor'].sum()
    total_c = df_final['Saldo Credor'].sum()
    
    # Proporção das colunas para alinhar com a tabela acima
    c_l, c_n, c_td, c_tc = st.columns([2, 1, 1, 1])
    c_l.markdown("**TOTAL GERAL**")
    c_td.markdown(f"**R$ {total_d:,.2f}**")
    c_tc.markdown(f"**R$ {total_c:,.2f}**")

    # --- SEÇÃO 3: RESULTADO DO EXERCÍCIO ---
    st.header("📈 Resultado do Exercício")
    receitas = df_final[df_final['Natureza'] == "Receita"]['Saldo Credor'].sum()
    despesas = df_final[df_final['Natureza'] == "Despesa"]['Saldo Devedor'].sum()
    resultado_liquido = receitas - despesas
    
    if resultado_liquido >= 0:
        st.metric("Lucro Líquido", f"R$ {resultado_liquido:,.2f}")
    else:
        st.metric("Prejuízo Líquido", f"R$ {abs(resultado_liquido):,.2f}", delta_color="inverse")

    # --- SEÇÃO 4: GESTÃO DE LANÇAMENTOS (DELETAR) ---
    st.divider()
    with st.expander("⚙️ Gerenciar Lançamentos (Consultar Origem #ID)"):
        st.write("Consulte o número após o '#' nos razonetes para identificar qual lançamento deletar:")
        for index, row in df.iterrows():
            col_inf, col_del = st.columns([5, 1])
            with col_inf:
                st.write(f"**#{int(row['ID'])}** | {row['Descrição']} | {row['Tipo']} | R$ {row['Valor']:,.2f}")
            with col_del:
                if st.button("🗑️", key=f"del_{row['ID']}"):
                    st.session_state.lancamentos = df[df['ID'] != row['ID']]
                    st.rerun()

    if st.button("🚨 Resetar Tudo"):
        st.session_state.clear()
        st.rerun()
else:
    st.info("Aguardando lançamentos para gerar os razonetes e o balancete.")
