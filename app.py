import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(page_title="Balancete Pro - Gestão & Logística", layout="wide")

st.title("📑 Sistema Contábil Digital")

# 2. Inicialização do Estado (Banco de Dados em Memória)
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Subgrupo', 'Tipo', 'Valor', 'Contrapartida']
    )
    st.session_state.id_cont = 0

# 3. Interface de Lançamento (Com suporte a desmembramento)
with st.expander("➕ Registrar Movimentação (Mesmo ID para desmembrar)", expanded=True):
    st.write(f"Sessão de Lançamento atual: **ID #{st.session_state.id_cont}**")
    
    with st.form("form_contabil", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            desc = st.text_input("Conta (Ex: Banco, Estoque, Fornecedores)")
            natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
            sub = st.selectbox("Subgrupo", ["Circulante", "Não Circulante", "N/A"])
        with col2:
            tipo = st.selectbox("Operação", ["Débito", "Crédito"])
            valor = st.number_input("Valor R$", min_value=0.01, format="%.2f")
            contra = st.text_input("Contrapartida (Ex: Origem ou Destino do recurso)")
        
        c1, c2 = st.columns(2)
        with c1:
            add = st.form_submit_button("✅ Adicionar Parte ao ID Atual")
        with c2:
            finish = st.form_submit_button("💾 Finalizar Grupo e Mudar ID")

        if add:
            if desc:
                f_sub = sub if natureza in ["Ativo", "Passivo"] else "N/A"
                novo = pd.DataFrame([{
                    'ID': st.session_state.id_cont,
                    'Descrição': desc.upper().strip(),
                    'Natureza': natureza,
                    'Subgrupo': f_sub,
                    'Tipo': tipo,
                    'Valor': valor,
                    'Contrapartida': contra.upper().strip()
                }])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.rerun()
        
        if finish:
            st.session_state.id_cont += 1
            st.rerun()

# 4. Processamento de Dados
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    contas = sorted(df['Descrição'].unique())
    
    # --- SEÇÃO 1: RAZONETES DETALHADOS ---
    st.header("📊 Razonetes (T) com Rastreabilidade")
    cols_raz = st.columns(2)
    resumo_balancete = []

    for i, conta in enumerate(contas):
        with cols_raz[i % 2]:
            st.subheader(f"Conta: {conta}")
            df_c = df[df['Descrição'] == conta]
            
            debitos = []
            creditos = []
            
            for _, row in df_c.iterrows():
                # Formatação: Valor + (#ID) + Seta de Direção + Contrapartida
                seta = "→" if row['Tipo'] == 'Débito' else "←"
                info = f"R$ {row['Valor']:,.2f} (#{int(row['ID'])}) {seta} {row['Contrapartida']}"
                if row['Tipo'] == 'Débito':
                    debitos.append(info)
                else:
                    creditos.append(info)
            
            max_len = max(len(debitos), len(creditos))
            debitos += ["-"] * (max_len - len(debitos))
            creditos += ["-"] * (max_len - len(creditos))
            
            st.table(pd.DataFrame({"Débito (D)": debitos, "Crédito (C)": creditos}))
            
            # Saldos para o Balancete
            t_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
            t_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
            resumo_balancete.append({
                'Conta': conta,
                'Natureza': df_c['Natureza'].iloc[0],
                'Saldo Devedor': max(0.0, t_d - t_c),
                'Saldo Credor': max(0.0, t_c - t_d)
            })
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
    
    c_l, c_n, c_td, c_tc = st.columns([2, 1, 1, 1])
    c_l.markdown("**TOTAL GERAL**")
    c_td.markdown(f"**R$ {total_d:,.2f}**")
    c_tc.markdown(f"**R$ {total_c:,.2f}**")

    # --- SEÇÃO 3: RESULTADO DO EXERCÍCIO ---
    st.header("📈 Resultado Líquido")
    rec = df_final[df_final['Natureza'] == "Receita"]['Saldo Credor'].sum()
    des = df_final[df_final['Natureza'] == "Despesa"]['Saldo Devedor'].sum()
    res_liq = rec - des
    st.metric("Lucro/Prejuízo", f"R$ {res_liq:,.2f}")

    # --- SEÇÃO 4: GESTÃO DE LANÇAMENTOS (DELETAR) ---
    st.divider()
    with st.expander("⚙️ Gerenciar Lançamentos (Exclusão Individual)"):
        for index, row in df.iterrows():
            col_inf, col_del = st.columns([5, 1])
            with col_inf:
                st.write(f"**ID #{int(row['ID'])}** | {row['Descrição']} | {row['Tipo']} | R$ {row['Valor']:,.2f} | {row['Contrapartida']}")
            with col_del:
                if st.button("🗑️", key=f"del_{index}"): # Usamos index para garantir unicidade no botão
                    st.session_state.lancamentos = df.drop(index)
                    st.rerun()

    if st.button("🚨 Resetar Tudo"):
        st.session_state.clear()
        st.rerun()
else:
    st.info("Aguardando lançamentos para processar as contas.")
