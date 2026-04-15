import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

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
    .dre-header { font-size: 20px !important; font-weight: bold !important; color: #1E3A8A; }
    .dre-value { font-size: 28px !important; font-weight: 900 !important; margin-bottom: 15px; }
    .justificativa-texto { font-style: italic; color: #555; font-size: 0.9em; margin-top: -10px; }
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
        idx_conta = opcoes.index(row_to_edit['Descrição']) if row_to_edit is not None and row_to_edit['Descrição'] in opcoes else 0
        escolha_conta = st.selectbox("Escolher Conta", opcoes, index=idx_conta)
        nova_conta_input = st.text_input("OU Nova Conta").upper().strip()
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        idx_nat = lista_nat.index(row_to_edit['Natureza']) if row_to_edit is not None else 0
        natureza = st.selectbox("Natureza", lista_nat, index=idx_nat)
        
        tipo_idx = 0 if row_to_edit is None or row_to_edit['Tipo'] == "Débito" else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True, index=tipo_idx)
        
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f", value=float(row_to_edit['Valor']) if row_to_edit is not None else 0.0)
        justificativa = st.text_area("Justificativa", value=row_to_edit['Justificativa'] if row_to_edit is not None else "")
        
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

    # --- ABA DRE INTERATIVA ---
    with tab_dre:
        # Cálculos de Resultado
        rec_tot = df[df['Natureza'] == 'Receita']['Valor'].sum()
        desp_op = df[df['Natureza'] == 'Despesa']['Valor'].sum()
        enc_fin = df[df['Natureza'] == 'Encargos Financeiros']['Valor'].sum()
        ebitda = rec_tot - desp_op
        lucro_real = ebitda - enc_fin
        margem = (lucro_real / rec_tot * 100) if rec_tot > 0 else 0

        # Cabeçalho com Métricas Visuais
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown('<p class="dre-header">RECEITA TOTAL</p>', unsafe_allow_html=True)
        c1.markdown(f'<p class="dre-value" style="color:#1E3A8A">R$ {rec_tot:,.2f}</p>', unsafe_allow_html=True)
        
        c2.markdown('<p class="dre-header">EBITDA</p>', unsafe_allow_html=True)
        c2.markdown(f'<p class="dre-value" style="color:{"green" if ebitda >=0 else "red"}">R$ {ebitda:,.2f}</p>', unsafe_allow_html=True)
        
        c3.markdown('<p class="dre-header">ENCARGOS FIN.</p>', unsafe_allow_html=True)
        c3.markdown(f'<p class="dre-value" style="color:#E11D48">R$ {enc_fin:,.2f}</p>', unsafe_allow_html=True)
        
        c4.markdown('<p class="dre-header">LUCRO REAL</p>', unsafe_allow_html=True)
        c4.markdown(f'<p class="dre-value" style="color:{"#10B981" if lucro_real >=0 else "#EF4444"}">R$ {lucro_real:,.2f}</p>', unsafe_allow_html=True)

        st.divider()

        # Gráficos Interativos
        col_graph1, col_graph2 = st.columns([2, 1])

        with col_graph1:
            st.markdown("**Comparativo de Performance Financeira**")
            fig_perf = go.Figure()
            fig_perf.add_trace(go.Bar(x=['Receita', 'EBITDA', 'Lucro Real'], y=[rec_tot, ebitda, lucro_real], 
                                     marker_color=['#1E3A8A', '#3B82F6', '#10B981']))
            fig_perf.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_perf, use_container_width=True)

        with col_graph2:
            st.markdown("**Composição de Custos/Encargos**")
            despesas_detalhe = df[df['Natureza'].isin(['Despesa', 'Encargos Financeiros'])].groupby('Descrição')['Valor'].sum()
            if not despesas_detalhe.empty:
                fig_pizza = px.pie(values=despesas_detalhe.values, names=despesas_detalhe.index, hole=.4,
                                   color_discrete_sequence=px.colors.sequential.RdBu)
                fig_pizza.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
                st.plotly_chart(fig_pizza, use_container_width=True)
            else:
                st.info("Sem despesas para exibir gráfico.")

        # Tabela Detalhada Expansível
        with st.expander("🔍 Ver Detalhamento Contábil (Tabela)", expanded=False):
            dre_list = [["(=) RECEITA OPERACIONAL BRUTA", rec_tot, "100.00%"]]
            for n, v in df[df['Natureza'] == 'Receita'].groupby('Descrição')['Valor'].sum().items():
                dre_list.append([f"   (+) {n}", v, f"{(v/rec_tot*100):.2f}%" if rec_tot > 0 else "0%"])
            dre_list.append(["(-) DESPESAS OPERACIONAIS", -desp_op, f"{(desp_op/rec_tot*100):.2f}%" if rec_tot > 0 else "0%"])
            for n, v in df[df['Natureza'] == 'Despesa'].groupby('Descrição')['Valor'].sum().items():
                dre_list.append([f"   (-) {n}", -v, f"{(v/rec_tot*100):.2f}%" if rec_tot > 0 else "0%"])
            dre_list.append(["(=) EBITDA", ebitda, f"{(ebitda/rec_tot*100):.2f}%" if rec_tot > 0 else "0%"])
            dre_list.append(["(-) ENCARGOS FINANCEIROS", -enc_fin, f"{(enc_fin/rec_tot*100):.2f}%" if rec_tot > 0 else "0%"])
            for n, v in df[df['Natureza'] == 'Encargos Financeiros'].groupby('Descrição')['Valor'].sum().items():
                dre_list.append([f"   (-) {n}", -v, f"{(v/rec_tot*100):.2f}%" if rec_tot > 0 else "0%"])
            dre_list.append(["(=) LUCRO LÍQUIDO REAL", lucro_real, f"{margem:.2f}%"])

            df_dre_f = pd.DataFrame(dre_list, columns=["Descrição", "Valor", "AV (%)"])
            st.table(df_dre_f.style.format({"Valor": "R$ {:,.2f}"}))

    # --- OUTRAS ABAS (Mantidas conforme solicitado) ---
    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            with st.expander(f"Razonete: {conta}"):
                c_d, c_c = st.columns(2)
                df_c = df[df['Descrição'] == conta]
                with c_d:
                    st.write("**DÉBITO**")
                    debs = df_c[df_c['Tipo'] == 'Débito']
                    for i, r in debs.iterrows(): st.caption(f"Ref #{i+1}: R$ {r['Valor']:,.2f} - {r['Justificativa']}")
                    st.markdown(f"**Total D: R$ {debs['Valor'].sum():,.2f}**")
                with c_c:
                    st.write("**CRÉDITO**")
                    creds = df_c[df_c['Tipo'] == 'Crédito']
                    for i, r in creds.iterrows(): st.caption(f"Ref #{i+1}: R$ {r['Valor']:,.2f} - {r['Justificativa']}")
                    st.markdown(f"**Total C: R$ {creds['Valor'].sum():,.2f}**")
                res_s = debs['Valor'].sum() - creds['Valor'].sum()
                if res_s > 0: st.success(f"Saldo Devedor: R$ {res_s:,.2f}")
                elif res_s < 0: st.warning(f"Saldo Credor: R$ {abs(res_s):,.2f}")

    with tab_bal:
        st.subheader("Equilíbrio Patrimonial")
        df_pat = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        resumo = []
        for c in sorted(df_pat['Descrição'].unique()):
            d_c = df_pat[df_pat['Descrição'] == c]
            v_d, v_c = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum(), d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
            resumo.append({'Conta': c, 'Saldo Devedor': max(0.0, v_d - v_c), 'Saldo Credor': max(0.0, v_c - v_d)})
        resumo.append({'Conta': 'RESULTADO DO PERÍODO', 'Saldo Devedor': abs(lucro_real) if lucro_real < 0 else 0, 'Saldo Credor': lucro_real if lucro_real > 0 else 0})
        st.table(pd.DataFrame(resumo).style.format({'Saldo Devedor': 'R$ {:,.2f}', 'Saldo Credor': 'R$ {:,.2f}'}))

    with tab_ges:
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([4, 0.5, 0.5])
            with c1:
                st.write(f"**#{idx+1} {row['Descrição']}** | {row['Natureza']} | R$ {row['Valor']:,.2f}")
                st.caption(f"Justificativa: {row['Justificativa']}")
            if c2.button("📝", key=f"e_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
            if c3.button("🗑️", key=f"d_{idx}"):
                st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                st.rerun()
            st.divider()
else:
    st.info("Insira lançamentos para ativar a DRE interativa.")
