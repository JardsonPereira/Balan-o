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
    .total-box { 
        text-align: center; 
        padding: 10px; 
        border-radius: 5px; 
        border: 2px solid #28a745; 
        font-weight: bold;
        background-color: #ffffff;
    }
    .total-box-error { 
        border-color: #ff4b4b; 
    }
    .justificativa-texto {
        font-style: italic;
        color: #555;
        font-size: 0.9em;
    }
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
        
        justificativa_padrao = row_to_edit['Justificativa'] if row_to_edit is not None else ""
        justificativa = st.text_area("Justificativa / Histórico", value=justificativa_padrao)
        
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

    # CÁLCULOS TÉCNICOS
    receitas_totais = df[df['Natureza'] == 'Receita']['Valor'].sum()
    despesas_totais = df[df['Natureza'] == 'Despesa']['Valor'].sum()
    lucro_prejuizo = receitas_totais - despesas_totais

    # --- ABA RAZONETES ---
    with tab_raz:
        contas = sorted(df['Descrição'].unique())
        for conta in contas:
            with st.expander(f"Conta: {conta}", expanded=True):
                df_c = df[df['Descrição'] == conta]
                col_d, col_c = st.columns(2)
                with col_d:
                    st.markdown("<p style='text-align:center; border-bottom:1px solid #ccc'>DÉBITO</p>", unsafe_allow_html=True)
                    debs = df_c[df_c['Tipo'] == 'Débito']
                    for idx, r in debs.iterrows():
                        st.caption(f"Ref #{idx+1}: {r['Justificativa']}") # Justificativa aqui
                        st.button(f"R$ {r['Valor']:,.2f}", key=f"rd_{idx}_{conta}", use_container_width=True)
                with col_c:
                    st.markdown("<p style='text-align:center; border-bottom:1px solid #ccc'>CRÉDITO</p>", unsafe_allow_html=True)
                    creds = df_c[df_c['Tipo'] == 'Crédito']
                    for idx, r in creds.iterrows():
                        st.caption(f"Ref #{idx+1}: {r['Justificativa']}") # Justificativa aqui
                        st.button(f"R$ {r['Valor']:,.2f}", key=f"rc_{idx}_{conta}", use_container_width=True)
                
                s = debs['Valor'].sum() - creds['Valor'].sum()
                st.markdown(f"**Saldo: R$ {abs(s):,.2f} ({'Devedor' if s >= 0 else 'Credor'})**")

    # --- ABA BALANCETE PATRIMONIAL ---
    with tab_bal:
        st.subheader("Balancete de Verificação Patrimonial")
        df_patrimonial = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        resumo_bal = []
        for c in sorted(df_patrimonial['Descrição'].unique()):
            d_c = df_patrimonial[df_patrimonial['Descrição'] == c]
            nat = d_c['Natureza'].iloc[0]
            v_d = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum()
            v_c = d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
            s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
            resumo_bal.append({'Conta': c, 'Natureza': nat, 'Saldo Devedor': s_d, 'Saldo Credor': s_c})
        
        if lucro_prejuizo > 0:
            resumo_bal.append({'Conta': 'LUCRO LÍQUIDO (DRE)', 'Natureza': 'Patrimônio Líquido', 'Saldo Devedor': 0.0, 'Saldo Credor': abs(lucro_prejuizo)})
        elif lucro_prejuizo < 0:
            resumo_bal.append({'Conta': 'PREJUÍZO LÍQUIDO (DRE)', 'Natureza': 'Patrimônio Líquido', 'Saldo Devedor': abs(lucro_prejuizo), 'Saldo Credor': 0.0})
        
        df_final_bal = pd.DataFrame(resumo_bal)
        st.table(df_final_bal.style.format({'Saldo Devedor': 'R$ {:,.2f}', 'Saldo Credor': 'R$ {:,.2f}'}))
        
        total_devedor = df_final_bal['Saldo Devedor'].sum()
        total_credor = df_final_bal['Saldo Credor'].sum()
        equilibrado = round(total_devedor, 2) == round(total_credor, 2)
        
        c_esp, c_td, c_tc = st.columns([1.5, 1, 1])
        css = "total-box" if equilibrado else "total-box total-box-error"
        c_td.markdown(f"<div class='{css}'>Total Devedor<br>R$ {total_devedor:,.2f}</div>", unsafe_allow_html=True)
        c_tc.markdown(f"<div class='{css}'>Total Credor<br>R$ {total_credor:,.2f}</div>", unsafe_allow_html=True)

    # --- ABA DRE ---
    with tab_dre:
        st.subheader("📈 Demonstração do Resultado")
        recs = df[df['Natureza'] == 'Receita'].groupby('Descrição')['Valor'].sum()
        desps = df[df['Natureza'] == 'Despesa'].groupby('Descrição')['Valor'].sum()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**(+) RECEITAS**")
            for n, v in recs.items(): st.write(f"{n}: R$ {v:,.2f}")
            st.markdown(f"**Total: R$ {receitas_totais:,.2f}**")
        with col2:
            st.markdown("**(-) DESPESAS**")
            for n, v in desps.items(): st.write(f"{n}: (R$ {v:,.2f})")
            st.markdown(f"**Total: (R$ {despesas_totais:,.2f})**")
        st.divider()
        if lucro_prejuizo >= 0: st.success(f"### LUCRO LÍQUIDO: R$ {lucro_prejuizo:,.2f}")
        else: st.error(f"### PREJUÍZO LÍQUIDO: R$ {abs(lucro_prejuizo):,.2f}")

    # --- ABA GESTÃO (ONDE O ERRO FOI CORRIGIDO) ---
    with tab_ges:
        st.subheader("Histórico de Lançamentos")
        for idx, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([4, 0.5, 0.5])
                with c1:
                    # Título com ID e Nome da Conta
                    st.markdown(f"**#{idx+1} - {row['Descrição']}** ({row['Natureza']})")
                    # Detalhes do Valor e Tipo
                    st.markdown(f"**{row['Tipo']}**: R$ {row['Valor']:,.2f}")
                    # JUSTIFICATIVA EXIBIDA AQUI:
                    if row['Justificativa']:
                        st.markdown(f"<p class='justificativa-texto'>Justificativa: {row['Justificativa']}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p class='justificativa-texto'>Sem justificativa informada.</p>", unsafe_allow_html=True)
                
                if c2.button("📝", key=f"edit_{idx}"):
                    st.session_state.edit_index = idx
                    st.rerun()
                if c3.button("🗑️", key=f"del_{idx}"):
                    st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                    st.rerun()
                st.divider()
else:
    st.info("Aguardando lançamentos na barra lateral.")
