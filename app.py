import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Estilização CSS para melhorar a legibilidade
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("📑 Sistema Contábil Integrado")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor', 'Justificativa']
    )
    st.session_state.id_cont = 1

if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None

# 3. Barra Lateral - Lançamentos
with st.sidebar:
    if st.session_state.edit_index is not None:
        st.header(f"📝 Editar Lançamento #{st.session_state.lancamentos.loc[st.session_state.edit_index, 'ID']}")
        row_to_edit = st.session_state.lancamentos.loc[st.session_state.edit_index]
        btn_label = "Salvar Alterações"
    else:
        st.header(f"➕ Novo Lançamento Nº {st.session_state.id_cont}")
        row_to_edit = None
        btn_label = "Confirmar Lançamento"

    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes = ["-- Selecione uma conta --"] + contas_existentes

    with st.form("form_contabil", clear_on_submit=True):
        idx_conta = opcoes.index(row_to_edit['Descrição']) if row_to_edit is not None and row_to_edit['Descrição'] in opcoes else 0
        escolha_conta = st.selectbox("Escolher Conta", opcoes, index=idx_conta)
        nova_conta_input = st.text_input("OU Nova Conta (Texto)").upper().strip()
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"]
        idx_nat = lista_nat.index(row_to_edit['Natureza']) if row_to_edit is not None else 0
        natureza = st.selectbox("Natureza", lista_nat, index=idx_nat)
        
        tipo_idx = 0 if row_to_edit is None or row_to_edit['Tipo'] == "Débito" else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True, index=tipo_idx)
        
        valor_padrao = float(row_to_edit['Valor']) if row_to_edit is not None else 0.00
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f", value=valor_padrao)
        
        justificativa = st.text_area("Justificativa / Histórico", value=row_to_edit['Justificativa'] if row_to_edit is not None else "")
        
        submit = st.form_submit_button(btn_label, use_container_width=True)
        
        if submit:
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione uma conta --" else None)
            if nome_final and valor > 0:
                if st.session_state.edit_index is not None:
                    st.session_state.lancamentos.iloc[st.session_state.edit_index] = [
                        row_to_edit['ID'], nome_final, natureza, tipo, valor, justificativa
                    ]
                    st.session_state.edit_index = None
                else:
                    novo = pd.DataFrame([{'ID': st.session_state.id_cont, 'Descrição': nome_final, 'Natureza': natureza, 'Tipo': tipo, 'Valor': valor, 'Justificativa': justificativa}])
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                    st.session_state.id_cont += 1
                st.rerun()

    if st.session_state.edit_index is not None:
        if st.button("Cancelar Edição", use_container_width=True):
            st.session_state.edit_index = None
            st.rerun()

# 4. Interface Principal
if not st.session_state.lancamentos.empty:
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE", "⚙️ Gestão"])
    df = st.session_state.lancamentos
    contas = sorted(df['Descrição'].unique())

    # --- ABA RAZONETES ---
    with tab_raz:
        for conta in contas:
            with st.expander(f"Conta: {conta}", expanded=True):
                df_c = df[df['Descrição'] == conta]
                col_d, col_c = st.columns(2)
                
                with col_d:
                    st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>DÉBITO</b></p>", unsafe_allow_html=True)
                    debs = df_c[df_c['Tipo'] == 'Débito']
                    for _, r in debs.iterrows():
                        st.button(f"R$ {r['Valor']:,.2f} ({r['ID']})", key=f"raz_d_{r['ID']}_{conta}", use_container_width=True)
                    tot_d = debs['Valor'].sum()
                    st.markdown(f"<p style='text-align:right;'>Total D: <b>R$ {tot_d:,.2f}</b></p>", unsafe_allow_html=True)
                
                with col_c:
                    st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                    creds = df_c[df_c['Tipo'] == 'Crédito']
                    for _, r in creds.iterrows():
                        st.button(f"R$ {r['Valor']:,.2f} ({r['ID']})", key=f"raz_c_{r['ID']}_{conta}", use_container_width=True)
                    tot_c = creds['Valor'].sum()
                    st.markdown(f"<p style='text-align:right;'>Total C: <b>R$ {tot_c:,.2f}</b></p>", unsafe_allow_html=True)
                
                saldo = tot_d - tot_c
                if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
                elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")

    # --- ABA BALANCETE (Natureza Incluída) ---
    with tab_bal:
        st.subheader("Balancete de Verificação")
        resumo_bal = []
        for c in contas:
            d_c = df[df['Descrição'] == c]
            natureza_c = d_c['Natureza'].iloc[0] # Pega a natureza definida no cadastro
            v_d, v_c = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum(), d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
            s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
            resumo_bal.append({'Conta': c, 'Natureza': natureza_c, 'Saldo Devedor': s_d, 'Saldo Credor': s_c})
        
        df_bal = pd.DataFrame(resumo_bal)
        st.dataframe(df_bal.style.format({'Saldo Devedor': 'R$ {:,.2f}', 'Saldo Credor': 'R$ {:,.2f}'}), use_container_width=True, hide_index=True)
        
        sd_total = df_bal['Saldo Devedor'].sum()
        sc_total = df_bal['Saldo Credor'].sum()
        
        st.divider()
        c_tot_d, c_tot_c = st.columns(2)
        
        # Alerta se o balancete não bater
        if round(sd_total, 2) != round(sc_total, 2):
            st.error(f"🚨 ERRO: O Balancete não está fechando! Diferença de R$ {abs(sd_total - sc_total):,.2f}")
            color = "#ff4b4b"
        else:
            st.success("✅ Partidas Dobradas verificadas: Débitos e Créditos em equilíbrio.")
            color = "#28a745"

        c_tot_d.markdown(f"<div style='text-align:center; border:2px solid {color}; padding:10px; border-radius:5px'><b>Total Devedor: R$ {sd_total:,.2f}</b></div>", unsafe_allow_html=True)
        c_tot_c.markdown(f"<div style='text-align:center; border:2px solid {color}; padding:10px; border-radius:5px'><b>Total Credor: R$ {sc_total:,.2f}</b></div>", unsafe_allow_html=True)

    # --- ABA DRE ---
    with tab_dre:
        st.subheader("DRE - Demonstração do Resultado")
        recs = df[df['Natureza'] == 'Receita'].groupby('Descrição')['Valor'].sum()
        desps = df[df['Natureza'] == 'Despesa'].groupby('Descrição')['Valor'].sum()
        
        st.markdown("**(+) RECEITAS**")
        for n, v in recs.items(): st.write(f"{n}: R$ {v:,.2f}")
        st.write(f"**Total Receitas: R$ {recs.sum():,.2f}**")
        
        st.markdown("---")
        st.markdown("**(-) DESPESAS**")
        for n, v in desps.items(): st.write(f"{n}: (R$ {v:,.2f})")
        st.write(f"**Total Despesas: (R$ {desps.sum():,.2f})**")
        
        resultado = recs.sum() - desps.sum()
        st.divider()
        if resultado >= 0: st.success(f"### LUCRO LÍQUIDO: R$ {resultado:,.2f}")
        else: st.error(f"### PREJUÍZO LÍQUIDO: R$ {abs(resultado):,.2f}")

    # --- ABA GESTÃO ---
    with tab_ges:
        st.subheader("Histórico e Gestão")
        for idx, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([4, 0.5, 0.5])
                with c1:
                    st.markdown(f"**#{row['ID']} - {row['Descrição']}** ({row['Natureza']}) | **{row['Tipo']}**: R$ {row['Valor']:,.2f}")
                    st.caption(f"Histórico: {row['Justificativa']}")
                if c2.button("📝", key=f"e_{idx}"):
                    st.session_state.edit_index = idx
                    st.rerun()
                if c3.button("🗑️", key=f"d_{idx}"):
                    st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                    st.rerun()
                st.divider()
else:
    st.info("Utilize a barra lateral para inserir o primeiro lançamento.")
