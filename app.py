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
    .dre-header { font-size: 18px !important; font-weight: bold !important; color: #1E3A8A; margin-bottom: 0px; }
    .dre-value { font-size: 26px !important; font-weight: 900 !important; margin-bottom: 20px; }
    .justificativa-texto { font-style: italic; color: #555; font-size: 0.9em; margin-top: -10px; }
    .total-box { 
        text-align: center; padding: 10px; border-radius: 5px; 
        border: 2px solid #28a745; font-weight: bold; background-color: #ffffff;
    }
    .total-box-error { border-color: #ff4b4b; }
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
        st.header(f"➕ Novo Lançamento Nº {len(st.session_state.lancamentos) + 1}")
        row_to_edit = None
        btn_label = "Confirmar Lançamento"

    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes = ["-- Selecione uma conta --"] + contas_existentes

    with st.form("form_contabil", clear_on_submit=True):
        escolha_conta = st.selectbox("Escolher Conta", opcoes)
        nova_conta_input = st.text_input("OU Nova Conta").upper().strip()
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        natureza = st.selectbox("Natureza", lista_nat)
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f")
        justificativa = st.text_area("Justificativa / Histórico")
        
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
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE Interativa", "⚙️ Gestão"])
    df = st.session_state.lancamentos

    # Cálculos Base
    rec_tot = df[df['Natureza'] == 'Receita']['Valor'].sum()
    desp_op = df[df['Natureza'] == 'Despesa']['Valor'].sum()
    enc_fin = df[df['Natureza'] == 'Encargos Financeiros']['Valor'].sum()
    ebitda = rec_tot - desp_op
    lucro_real = ebitda - enc_fin

    # --- ABA DRE INTERATIVA ---
    with tab_dre:
        # Destaques Maiores
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown('<p class="dre-header">RECEITA TOTAL</p>', unsafe_allow_html=True)
        c1.markdown(f'<p class="dre-value" style="color:#1E3A8A">R$ {rec_tot:,.2f}</p>', unsafe_allow_html=True)
        c2.markdown('<p class="dre-header">EBITDA</p>', unsafe_allow_html=True)
        c2.markdown(f'<p class="dre-value" style="color:{"green" if ebitda >=0 else "red"}">R$ {ebitda:,.2f}</p>', unsafe_allow_html=True)
        c3.markdown('<p class="dre-header">ENCARGOS FIN.</p>', unsafe_allow_html=True)
        c3.markdown(f'<p class="dre-value" style="color:#E11D48">R$ {enc_fin:,.2f}</p>', unsafe_allow_html=True)
        c4.markdown('<p class="dre-header">LUCRO REAL</p>', unsafe_allow_html=True)
        c4.markdown(f'<p class="dre-value" style="color:{"#10B981" if lucro_real >=0 else "#EF4444"}">R$ {lucro_real:,.2f}</p>', unsafe_allow_html=True)

        # Gráfico Nativo (Sem dependência de Plotly)
        st.markdown("**Performance de Resultado**")
        chart_data = pd.DataFrame({'Valor': [rec_tot, ebitda, lucro_real]}, index=['Receita', 'EBITDA', 'Lucro Real'])
        st.bar_chart(chart_data)

        with st.expander("🔍 Detalhamento da DRE (Tabela)"):
            dre_items = [
                ["(=) RECEITA BRUTA", rec_tot, "100%"],
                ["(-) DESPESAS OPERACIONAIS", -desp_op, f"{(desp_op/rec_tot*100):.1f}%" if rec_tot>0 else "0%"],
                ["(=) EBITDA", ebitda, f"{(ebitda/rec_tot*100):.1f}%" if rec_tot>0 else "0%"],
                ["(-) ENCARGOS FINANCEIROS", -enc_fin, f"{(enc_fin/rec_tot*100):.1f}%" if rec_tot>0 else "0%"],
                ["(=) LUCRO LÍQUIDO REAL", lucro_real, f"{(lucro_real/rec_tot*100):.1f}%" if rec_tot>0 else "0%"]
            ]
            st.table(pd.DataFrame(dre_items, columns=["Indicador", "Valor (R$)", "AV (%)"]))

    # --- ABA RAZONETES ---
    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            with st.expander(f"Razonete: {conta}", expanded=True):
                df_c = df[df['Descrição'] == conta]
                col_d, col_c = st.columns(2)
                with col_d:
                    st.markdown("<p style='text-align:center; border-bottom:1px solid #555'>DÉBITO</p>", unsafe_allow_html=True)
                    debs = df_c[df_c['Tipo'] == 'Débito']
                    for i, r in debs.iterrows():
                        st.caption(f"Ref #{i+1}: {r['Justificativa']}")
                        st.button(f"R$ {r['Valor']:,.2f}", key=f"rd_{i}_{conta}", use_container_width=True)
                    st.markdown(f"<p style='text-align:right'>Total D: R$ {debs['Valor'].sum():,.2f}</p>", unsafe_allow_html=True)
                with col_c:
                    st.markdown("<p style='text-align:center; border-bottom:1px solid #555'>CRÉDITO</p>", unsafe_allow_html=True)
                    creds = df_c[df_c['Tipo'] == 'Crédito']
                    for i, r in creds.iterrows():
                        st.caption(f"Ref #{i+1}: {r['Justificativa']}")
                        st.button(f"R$ {r['Valor']:,.2f}", key=f"rc_{i}_{conta}", use_container_width=True)
                    st.markdown(f"<p style='text-align:right'>Total C: R$ {creds['Valor'].sum():,.2f}</p>", unsafe_allow_html=True)
                
                s = debs['Valor'].sum() - creds['Valor'].sum()
                if s > 0: st.success(f"Saldo Devedor: R$ {abs(s):,.2f}")
                elif s < 0: st.warning(f"Saldo Credor: R$ {abs(s):,.2f}")

    # --- ABA BALANCETE ---
    with tab_bal:
        st.subheader("Balancete Patrimonial")
        df_pat = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        resumo = []
        for c in sorted(df_pat['Descrição'].unique()):
            d_c = df_pat[df_pat['Descrição'] == c]
            v_d, v_c = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum(), d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
            resumo.append({'Conta': c, 'Devedor': max(0.0, v_d-v_c), 'Credor': max(0.0, v_c-v_d)})
        resumo.append({'Conta': 'RESULTADO DO PERÍODO', 'Devedor': abs(lucro_real) if lucro_real < 0 else 0, 'Credor': lucro_real if lucro_real > 0 else 0})
        df_b = pd.DataFrame(resumo)
        st.table(df_b.style.format({'Devedor': 'R$ {:,.2f}', 'Credor': 'R$ {:,.2f}'}))
        
        t_d, t_c = df_b['Devedor'].sum(), df_b['Credor'].sum()
        col_esp, col_dev, col_cred = st.columns([1.5, 1, 1])
        equi = round(t_d, 2) == round(t_c, 2)
        c_box = "total-box" if equi else "total-box total-box-error"
        col_dev.markdown(f"<div class='{c_box}'>Total Devedor<br>R$ {t_d:,.2f}</div>", unsafe_allow_html=True)
        col_cred.markdown(f"<div class='{c_box}'>Total Credor<br>R$ {t_c:,.2f}</div>", unsafe_allow_html=True)

    # --- ABA GESTÃO ---
    with tab_ges:
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([4, 0.5, 0.5])
            with c1:
                st.write(f"**#{idx+1} {row['Descrição']}** | {row['Tipo']}: R$ {row['Valor']:,.2f}")
                st.markdown(f"<p class='justificativa-texto'>Justificativa: {row['Justificativa']}</p>", unsafe_allow_html=True)
            if c2.button("📝", key=f"e_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
            if c3.button("🗑️", key=f"d_{idx}"):
                st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                st.rerun()
            st.divider()
else:
    st.info("Aguardando lançamentos na barra lateral.")
