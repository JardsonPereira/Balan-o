import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Estilização
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

st.title("📑 Sistema Contábil Integrado")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['Descrição', 'Natureza', 'Tipo', 'Valor', 'Justificativa']
    )

if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None

# 3. Barra Lateral - Formulário
with st.sidebar:
    if st.session_state.edit_index is not None:
        st.header(f"📝 Editar Lançamento #{st.session_state.edit_index + 1}")
        row_to_edit = st.session_state.lancamentos.iloc[st.session_state.edit_index]
        btn_label = "Salvar Alterações"
    else:
        proximo_id = len(st.session_state.lancamentos) + 1
        st.header(f"➕ Novo Lançamento Nº {proximo_id}")
        row_to_edit = None
        btn_label = "Confirmar Lançamento"

    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes = ["-- Selecione uma conta --"] + contas_existentes

    with st.form("form_contabil", clear_on_submit=True):
        idx_conta = opcoes.index(row_to_edit['Descrição']) if row_to_edit is not None and row_to_edit['Descrição'] in opcoes else 0
        escolha_conta = st.selectbox("Escolher Conta", opcoes, index=idx_conta)
        nova_conta_input = st.text_input("OU Nova Conta").upper().strip()
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"]
        idx_nat = lista_nat.index(row_to_edit['Natureza']) if row_to_edit is not None else 0
        natureza = st.selectbox("Natureza", lista_nat, index=idx_nat)
        
        tipo_idx = 0 if row_to_edit is None or row_to_edit['Tipo'] == "Débito" else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True, index=tipo_idx)
        
        valor_padrao = float(row_to_edit['Valor']) if row_to_edit is not None else 0.00
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f", value=valor_padrao)
        
        justificativa = st.text_area("Histórico", value=row_to_edit['Justificativa'] if row_to_edit is not None else "")
        
        if st.form_submit_button(btn_label, use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione uma conta --" else None)
            if nome_final and valor > 0:
                if st.session_state.edit_index is not None:
                    st.session_state.lancamentos.iloc[st.session_state.edit_index] = [nome_final, natureza, tipo, valor, justificativa]
                    st.session_state.edit_index = None
                else:
                    novo = pd.DataFrame([{'Descrição': nome_final, 'Natureza': natureza, 'Tipo': tipo, 'Valor': valor, 'Justificativa': justificativa}])
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.rerun()

# 4. Interface Principal
if not st.session_state.lancamentos.empty:
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete Patrimonial", "📈 DRE", "⚙️ Gestão"])
    df = st.session_state.lancamentos

    # --- ABA RAZONETES (Todos os lançamentos) ---
    with tab_raz:
        contas = sorted(df['Descrição'].unique())
        for conta in contas:
            with st.expander(f"Conta: {conta}", expanded=True):
                df_c = df[df['Descrição'] == conta]
                col_d, col_c = st.columns(2)
                with col_d:
                    st.markdown("<p style='text-align:center; border-bottom:1px solid #ccc'>DÉBITO</p>", unsafe_allow_html=True)
                    debs = df_c[df_c['Tipo'] == 'Débito']
                    for idx, r in debs.iterrows(): st.button(f"R$ {r['Valor']:,.2f} (#{idx+1})", key=f"rd_{idx}_{conta}", use_container_width=True)
                with col_c:
                    st.markdown("<p style='text-align:center; border-bottom:1px solid #ccc'>CRÉDITO</p>", unsafe_allow_html=True)
                    creds = df_c[df_c['Tipo'] == 'Crédito']
                    for idx, r in creds.iterrows(): st.button(f"R$ {r['Valor']:,.2f} (#{idx+1})", key=f"rc_{idx}_{conta}", use_container_width=True)
                
                s = debs['Valor'].sum() - creds['Valor'].sum()
                st.markdown(f"**Saldo: R$ {abs(s):,.2f} ({'Devedor' if s >= 0 else 'Credor'})**")

    # --- ABA BALANCETE (Apenas Ativo, Passivo e PL) ---
    with tab_bal:
        st.subheader("Balancete de Verificação (Contas Patrimoniais)")
        st.caption("Nota: Receitas e Despesas foram movidas para a aba DRE.")
        
        # Filtro para excluir Receitas e Despesas
        df_patrimonial = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        
        if not df_patrimonial.empty:
            resumo_bal = []
            for c in sorted(df_patrimonial['Descrição'].unique()):
                d_c = df_patrimonial[df_patrimonial['Descrição'] == c]
                nat = d_c['Natureza'].iloc[0]
                v_d = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum()
                v_c = d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
                s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
                resumo_bal.append({'Conta': c, 'Natureza': nat, 'Saldo Devedor': s_d, 'Saldo Credor': s_c})
            
            st.table(pd.DataFrame(resumo_bal).style.format({'Saldo Devedor': 'R$ {:,.2f}', 'Saldo Credor': 'R$ {:,.2f}'}))
        else:
            st.info("Nenhuma conta de Ativo, Passivo ou PL lançada.")

    # --- ABA DRE (Apenas Receitas e Despesas) ---
    with tab_dre:
        st.subheader("📈 Demonstração do Resultado")
        
        # Filtro exclusivo para contas de resultado
        recs = df[df['Natureza'] == 'Receita'].groupby('Descrição')['Valor'].sum()
        desps = df[df['Natureza'] == 'Despesa'].groupby('Descrição')['Valor'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**(+) RECEITAS**")
            for n, v in recs.items(): st.write(f"{n}: R$ {v:,.2f}")
            st.markdown(f"--- \n **Total: R$ {recs.sum():,.2f}**")
        
        with col2:
            st.markdown("**(-) DESPESAS**")
            for n, v in desps.items(): st.write(f"{n}: (R$ {v:,.2f})")
            st.markdown(f"--- \n **Total: (R$ {desps.sum():,.2f})**")
        
        res = recs.sum() - desps.sum()
        if res >= 0: st.success(f"### LUCRO LÍQUIDO: R$ {res:,.2f}")
        else: st.error(f"### PREJUÍZO LÍQUIDO: R$ {abs(res):,.2f}")

    # --- ABA GESTÃO ---
    with tab_ges:
        st.subheader("Histórico")
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([4, 0.5, 0.5])
            c1.markdown(f"**#{idx+1} {row['Descrição']}** | {row['Natureza']} | {row['Tipo']}: R$ {row['Valor']:,.2f}")
            if c2.button("📝", key=f"e_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
            if c3.button("🗑️", key=f"d_{idx}"):
                st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                st.rerun()
            st.divider()
else:
    st.info("Aguardando lançamentos na barra lateral.")
