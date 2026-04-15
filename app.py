import streamlit as st
import pandas as pd
try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    st.error("A biblioteca 'plotly' não foi encontrada. Instale-a com: pip install plotly")

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
    .justificativa-texto { font-style: italic; color: #555; font-size: 0.9em; }
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

# 3. Barra Lateral
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
        escolha_conta = st.selectbox("Escolher Conta", opcoes, index=0)
        nova_conta_input = st.text_input("OU Nova Conta").upper().strip()
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        natureza = st.selectbox("Natureza", lista_nat)
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f")
        justificativa = st.text_area("Justificativa")
        
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
        rec_tot = df[df['Natureza'] == 'Receita']['Valor'].sum()
        desp_op = df[df['Natureza'] == 'Despesa']['Valor'].sum()
        enc_fin = df[df['Natureza'] == 'Encargos Financeiros']['Valor'].sum()
        ebitda = rec_tot - desp_op
        lucro_real = ebitda - enc_fin
        margem = (lucro_real / rec_tot * 100) if rec_tot > 0 else 0

        # Destaques Maiores e Negritos
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown('<p class="dre-header">RECEITA TOTAL</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="dre-value" style="color:#1E3A8A">R$ {rec_tot:,.2f}</p>', unsafe_allow_html=True)
        with c2:
            st.markdown('<p class="dre-header">EBITDA</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="dre-value" style="color:{"green" if ebitda >=0 else "red"}">R$ {ebitda:,.2f}</p>', unsafe_allow_html=True)
        with c3:
            st.markdown('<p class="dre-header">ENCARGOS FIN.</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="dre-value" style="color:#E11D48">R$ {enc_fin:,.2f}</p>', unsafe_allow_html=True)
        with c4:
            st.markdown('<p class="dre-header">LUCRO REAL</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="dre-value" style="color:{"#10B981" if lucro_real >=0 else "#EF4444"}">R$ {lucro_real:,.2f}</p>', unsafe_allow_html=True)

        # Gráficos Plotly
        col_g1, col_g2 = st.columns([2, 1])
        with col_g1:
            fig_bar = go.Figure(data=[
                go.Bar(name='Valores', x=['Receita', 'EBITDA', 'Lucro Real'], y=[rec_tot, ebitda, lucro_real], 
                       marker_color=['#1E3A8A', '#3B82F6', '#10B981'], textposition='auto')
            ])
            fig_bar.update_layout(title="Performance Financeira", height=300, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_g2:
            despesas_data = df[df['Natureza'].isin(['Despesa', 'Encargos Financeiros'])].groupby('Descrição')['Valor'].sum()
            if not despesas_data.empty:
                fig_pie = px.pie(values=despesas_data.values, names=despesas_data.index, hole=.3)
                fig_pie.update_layout(title="Distribuição de Custos", height=300, margin=dict(t=30, b=0, l=0, r=0), showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)

        # Tabela Detalhada (Sem erros de Styler)
        with st.expander("🔍 Detalhamento Contábil Completo"):
            dre_items = [
                ["(=) RECEITA BRUTA", rec_tot, "100%"],
                ["(-) DESPESAS OPERACIONAIS", -desp_op, f"{(desp_op/rec_tot*100):.1f}%" if rec_tot>0 else "0%"],
                ["(=) EBITDA", ebitda, f"{(ebitda/rec_tot*100):.1f}%" if rec_tot>0 else "0%"],
                ["(-) ENCARGOS FINANCEIROS", -enc_fin, f"{(enc_fin/rec_tot*100):.1f}%" if rec_tot>0 else "0%"],
                ["(=) LUCRO LÍQUIDO REAL", lucro_real, f"{margem:.1f}%"]
            ]
            st.table(pd.DataFrame(dre_items, columns=["Indicador", "Valor (R$)", "AV (%)"]))

    # --- ABAS RAZONETE E BALANCETE (RESTAURADAS) ---
    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            with st.expander(f"Razonete: {conta}"):
                c_d, c_c = st.columns(2)
                df_c = df[df['Descrição'] == conta]
                v_d = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum()
                v_c = df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
                c_d.write("**DÉBITO**")
                for i, r in df_c[df_c['Tipo'] == 'Débito'].iterrows(): c_d.caption(f"R$ {r['Valor']:,.2f} - {r['Justificativa']}")
                c_c.write("**CRÉDITO**")
                for i, r in df_c[df_c['Tipo'] == 'Crédito'].iterrows(): c_c.caption(f"R$ {r['Valor']:,.2f} - {r['Justificativa']}")
                st.write(f"**Saldo Final: R$ {abs(v_d - v_c):,.2f} ({'Devedor' if v_d >= v_c else 'Credor'})**")

    with tab_bal:
        st.subheader("Balancete Patrimonial")
        df_pat = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        resumo = []
        for c in sorted(df_pat['Descrição'].unique()):
            d_c = df_pat[df_pat['Descrição'] == c]
            sd, sc = d_c[d_c['Tipo']=='Débito']['Valor'].sum(), d_c[d_c['Tipo']=='Crédito']['Valor'].sum()
            resumo.append({'Conta': c, 'Devedor': max(0.0, sd-sc), 'Credor': max(0.0, sc-sd)})
        resumo.append({'Conta': 'RESULTADO DO PERÍODO', 'Devedor': abs(lucro_real) if lucro_real < 0 else 0, 'Credor': lucro_real if lucro_real > 0 else 0})
        df_b = pd.DataFrame(resumo)
        st.table(df_b.style.format({'Devedor': 'R$ {:,.2f}', 'Credor': 'R$ {:,.2f}'}))
        st.write(f"**Total Devedor: R$ {df_b['Devedor'].sum():,.2f} | Total Credor: R$ {df_b['Credor'].sum():,.2f}**")

    with tab_ges:
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([4, 0.5, 0.5])
            c1.write(f"**#{idx+1} {row['Descrição']}** | R$ {row['Valor']:,.2f} | *{row['Justificativa']}*")
            if c2.button("📝", key=f"e_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
            if c3.button("🗑️", key=f"d_{idx}"):
                st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                st.rerun()
            st.divider()
else:
    st.info("Aguardando lançamentos na barra lateral.")
