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
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📑 Sistema Contábil Integrado")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    # Removi o ID fixo das colunas, pois o "ID" agora será o (index + 1)
    st.session_state.lancamentos = pd.DataFrame(
        columns=['Descrição', 'Natureza', 'Tipo', 'Valor', 'Justificativa']
    )

if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None

# 3. Barra Lateral - Lançamentos
with st.sidebar:
    if st.session_state.edit_index is not None:
        st.header(f"📝 Editar Lançamento #{st.session_state.edit_index + 1}")
        row_to_edit = st.session_state.lancamentos.iloc[st.session_state.edit_index]
        btn_label = "Salvar Alterações"
    else:
        # A numeração sugerida para o novo lançamento é o tamanho atual + 1
        proximo_id = len(st.session_state.lancamentos) + 1
        st.header(f"➕ Novo Lançamento Nº {proximo_id}")
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
        
        if st.form_submit_button(btn_label, use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione uma conta --" else None)
            if nome_final and valor > 0:
                if st.session_state.edit_index is not None:
                    # Edição: atualiza a linha específica
                    st.session_state.lancamentos.iloc[st.session_state.edit_index] = [
                        nome_final, natureza, tipo, valor, justificativa
                    ]
                    st.session_state.edit_index = None
                else:
                    # Adição: Novo DataFrame e concatenação
                    novo = pd.DataFrame([{'Descrição': nome_final, 'Natureza': natureza, 'Tipo': tipo, 'Valor': valor, 'Justificativa': justificativa}])
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
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
                    for idx, r in debs.iterrows():
                        # O ID exibido aqui é o index original do dataframe + 1
                        st.button(f"R$ {r['Valor']:,.2f} (Ref: {idx + 1})", key=f"raz_d_{idx}_{conta}", use_container_width=True)
                    tot_d = debs['Valor'].sum()
                    st.markdown(f"<p style='text-align:right;'>Total D: <b>R$ {tot_d:,.2f}</b></p>", unsafe_allow_html=True)
                
                with col_c:
                    st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                    creds = df_c[df_c['Tipo'] == 'Crédito']
                    for idx, r in creds.iterrows():
                        st.button(f"R$ {r['Valor']:,.2f} (Ref: {idx + 1})", key=f"raz_c_{idx}_{conta}", use_container_width=True)
                    tot_c = creds['Valor'].sum()
                    st.markdown(f"<p style='text-align:right;'>Total C: <b>R$ {tot_c:,.2f}</b></p>", unsafe_allow_html=True)
                
                saldo = tot_d - tot_c
                if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
                elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")

    # --- ABA BALANCETE ---
    with tab_bal:
        st.subheader("Balancete de Verificação")
        resumo_bal = []
        for c in contas:
            d_c = df[df['Descrição'] == c]
            natureza_c = d_c['Natureza'].iloc[0]
            v_d, v_c = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum(), d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
            s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
            resumo_bal.append({'Conta': c, 'Natureza': natureza_c, 'Saldo Devedor': s_d, 'Saldo Credor': s_c})
        
        df_bal = pd.DataFrame(resumo_bal)
        st.dataframe(df_bal.style.format({'Saldo Devedor': 'R$ {:,.2f}', 'Saldo Credor': 'R$ {:,.2f}'}), use_container_width=True, hide_index=True)
        
        sd_total = df_bal['Saldo Devedor'].sum()
        sc_total = df_bal['Saldo Credor'].sum()
        
        st.divider()
        c_tot_d, c_tot_c = st.columns(2)
        
        if round(sd_total, 2) != round(sc_total, 2):
            st.error(f"🚨 Diferença de R$ {abs(sd_total - sc_total):,.2f}")
            color = "#ff4b4b"
        else:
            st.success("✅ Balancete equilibrado.")
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
        st.markdown(f"**Total Receitas: R$ {recs.sum():,.2f}**")
        
        st.markdown("---")
        st.markdown("**(-) DESPESAS**")
        for n, v in desps.items(): st.write(f"{n}: (R$ {v:,.2f})")
        st.markdown(f"**Total Despesas: (R$ {desps.sum():,.2f})**")
        
        resultado = recs.sum() - desps.sum()
        st.divider()
        if resultado >= 0: st.success(f"### LUCRO LÍQUIDO: R$ {resultado:,.2f}")
        else: st.error(f"### PREJUÍZO LÍQUIDO: R$ {abs(resultado):,.2f}")

    # --- ABA GESTÃO (Aqui a renumeração acontece) ---
    with tab_ges:
        st.subheader("Histórico e Gestão")
        # Criamos uma cópia para iterar com segurança
        for idx, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([4, 0.5, 0.5])
                with c1:
                    # O número exibido é sempre o índice atual + 1
                    st.markdown(f"**Lançamento #{idx + 1} - {row['Descrição']}** ({row['Natureza']})")
                    st.markdown(f"**{row['Tipo']}**: R$ {row['Valor']:,.2f} | *{row['Justificativa']}*")
                
                if c2.button("📝", key=f"edit_{idx}"):
                    st.session_state.edit_index = idx
                    st.rerun()
                
                if c3.button("🗑️", key=f"del_{idx}"):
                    # Ao remover, usamos o reset_index(drop=True) para que o próximo 
                    # item da lista assuma o número anterior imediatamente.
                    st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                    st.session_state.edit_index = None # Previne erro se estiver editando o que foi excluído
                    st.rerun()
                st.divider()
else:
    st.info("Utilize a barra lateral para inserir o primeiro lançamento.")
