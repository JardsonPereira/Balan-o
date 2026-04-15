import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Estilização Personalizada
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .dre-card { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("📑 Sistema Contábil Integrado")

# 2. Inicialização do Estado (Session State)
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['Descrição', 'Natureza', 'Tipo', 'Valor', 'Justificativa']
    )

if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None

# 3. Barra Lateral - Formulário de Lançamentos
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
        escolha_conta = st.selectbox("Escolher Conta Existente", opcoes, index=idx_conta)
        
        nova_conta_input = st.text_input("OU Criar Nova Conta").upper().strip()
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"]
        idx_nat = lista_nat.index(row_to_edit['Natureza']) if row_to_edit is not None else 0
        natureza = st.selectbox("Natureza da Conta", lista_nat, index=idx_nat)
        
        tipo_idx = 0 if row_to_edit is None or row_to_edit['Tipo'] == "Débito" else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True, index=tipo_idx)
        
        valor_padrao = float(row_to_edit['Valor']) if row_to_edit is not None else 0.00
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f", value=valor_padrao)
        
        justificativa = st.text_area("Histórico / Justificativa", value=row_to_edit['Justificativa'] if row_to_edit is not None else "")
        
        submit = st.form_submit_button(btn_label, use_container_width=True)
        
        if submit:
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione uma conta --" else None)
            
            if nome_final and valor > 0:
                novo_dado = [nome_final, natureza, tipo, valor, justificativa]
                
                if st.session_state.edit_index is not None:
                    st.session_state.lancamentos.iloc[st.session_state.edit_index] = novo_dado
                    st.session_state.edit_index = None
                else:
                    novo_df = pd.DataFrame([dict(zip(st.session_state.lancamentos.columns, novo_dado))])
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo_df], ignore_index=True)
                
                st.rerun()
            else:
                st.error("Preencha a conta e o valor corretamente.")

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
                        st.caption(f"Ref: {idx + 1} | {r['Justificativa']}")
                        st.button(f"R$ {r['Valor']:,.2f}", key=f"raz_d_{idx}_{conta}", use_container_width=True)
                    tot_d = debs['Valor'].sum()
                    st.markdown(f"<p style='text-align:right;'>Total D: <b>R$ {tot_d:,.2f}</b></p>", unsafe_allow_html=True)
                
                with col_c:
                    st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                    creds = df_c[df_c['Tipo'] == 'Crédito']
                    for idx, r in creds.iterrows():
                        st.caption(f"Ref: {idx + 1} | {r['Justificativa']}")
                        st.button(f"R$ {r['Valor']:,.2f}", key=f"raz_c_{idx}_{conta}", use_container_width=True)
                    tot_c = creds['Valor'].sum()
                    st.markdown(f"<p style='text-align:right;'>Total C: <b>R$ {tot_c:,.2f}</b></p>", unsafe_allow_html=True)
                
                saldo = tot_d - tot_c
                if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
                elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")
                else: st.info("Saldo Zero")

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
        st.table(df_bal.style.format({'Saldo Devedor': 'R$ {:,.2f}', 'Saldo Credor': 'R$ {:,.2f}'}))
        
        sd_total = df_bal['Saldo Devedor'].sum()
        sc_total = df_bal['Saldo Credor'].sum()
        
        c_tot_d, c_tot_c = st.columns(2)
        color = "#28a745" if round(sd_total, 2) == round(sc_total, 2) else "#ff4b4b"
        
        c_tot_d.markdown(f"<div style='text-align:center; border:2px solid {color}; padding:10px; border-radius:5px'><b>Total Devedor: R$ {sd_total:,.2f}</b></div>", unsafe_allow_html=True)
        c_tot_c.markdown(f"<div style='text-align:center; border:2px solid {color}; padding:10px; border-radius:5px'><b>Total Credor: R$ {sc_total:,.2f}</b></div>", unsafe_allow_html=True)

    # --- ABA DRE ---
    with tab_dre:
        st.subheader("📈 Demonstração do Resultado do Exercício")
        
        # Filtramos apenas Receitas e Despesas
        df_receitas = df[df['Natureza'] == 'Receita']
        df_despesas = df[df['Natureza'] == 'Despesa']
        
        col_r, col_d = st.columns(2)
        
        with col_r:
            st.markdown("### (+) Receitas")
            if not df_receitas.empty:
                # Agrupamos por conta para somar lançamentos repetidos
                recs_agrup = df_receitas.groupby('Descrição')['Valor'].sum()
                for nome, val in recs_agrup.items():
                    st.write(f"**{nome}**: R$ {val:,.2f}")
                total_r = recs_agrup.sum()
            else:
                st.write("Nenhuma receita registrada.")
                total_r = 0.0
            st.markdown(f"**TOTAL RECEITAS: R$ {total_r:,.2f}**")

        with col_d:
            st.markdown("### (-) Despesas")
            if not df_despesas.empty:
                desps_agrup = df_despesas.groupby('Descrição')['Valor'].sum()
                for nome, val in desps_agrup.items():
                    st.write(f"**{nome}**: (R$ {val:,.2f})")
                total_d = desps_agrup.sum()
            else:
                st.write("Nenhuma despesa registrada.")
                total_d = 0.0
            st.markdown(f"**TOTAL DESPESAS: (R$ {total_d:,.2f})**")

        resultado = total_r - total_d
        st.divider()
        
        if resultado >= 0:
            st.success(f"## LUCRO LÍQUIDO: R$ {resultado:,.2f}")
        else:
            st.error(f"## PREJUÍZO LÍQUIDO: R$ {abs(resultado):,.2f}")

    # --- ABA GESTÃO ---
    with tab_ges:
        st.subheader("Histórico de Lançamentos")
        for idx, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([4, 0.5, 0.5])
                with c1:
                    st.markdown(f"**#{idx + 1} | {row['Descrição']}** ({row['Natureza']})")
                    st.markdown(f"*{row['Tipo']}*: R$ {row['Valor']:,.2f} — {row['Justificativa']}")
                
                if c2.button("📝", key=f"edit_{idx}"):
                    st.session_state.edit_index = idx
                    st.rerun()
                
                if c3.button("🗑️", key=f"del_{idx}"):
                    st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                    st.session_state.edit_index = None
                    st.rerun()
                st.divider()
else:
    st.info("Aguardando lançamentos... Utilize a barra lateral para começar.")
