import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Estilização - Adicionado 'overflow-y: auto' para garantir a rolagem
st.markdown("""
    <style>
    .main { 
        background-color: #f5f7f9; 
    }
    /* Força a rolagem vertical se o conteúdo exceder a tela */
    .stApp {
        overflow-y: auto;
    }
    .dre-header { font-size: 18px !important; font-weight: bold !important; color: #1E3A8A; margin-bottom: 0px; }
    .dre-value { font-size: 26px !important; font-weight: 900 !important; margin-bottom: 20px; }
    .justificativa-texto { font-style: italic; color: #555; font-size: 0.9em; margin-top: -10px; }
    .total-box { 
        text-align: center; padding: 10px; border-radius: 5px; 
        border: 2px solid #28a745; font-weight: bold; background-color: #ffffff;
    }
    .total-box-error { border-color: #ff4b4b; }
    .resumo-dre-linha { font-size: 1.1em; font-weight: bold; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
    
    /* Ajuste para evitar que as abas quebrem o layout */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 20px;
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

# 3. Barra Lateral
with st.sidebar:
    lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
    
    if st.session_state.edit_index is not None:
        idx = st.session_state.edit_index
        row_edit = st.session_state.lancamentos.iloc[idx]
        st.header(f"📝 Editar Lançamento #{idx + 1}")
        btn_label = "Salvar Alterações"
        if st.button("Cancelar Edição"):
            st.session_state.edit_index = None
            st.rerun()
    else:
        st.header(f"➕ Novo Lançamento Nº {len(st.session_state.lancamentos) + 1}")
        row_edit = None
        btn_label = "Confirmar Lançamento"

    with st.form("form_contabil", clear_on_submit=True):
        contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
        
        idx_conta = (contas_existentes.index(row_edit['Descrição']) + 1) if (row_edit is not None and row_edit['Descrição'] in contas_existentes) else 0
        escolha_conta = st.selectbox("Escolher Conta", ["-- Selecione --"] + contas_existentes, index=idx_conta)
        
        nova_conta_input = st.text_input("OU Nova Conta").upper().strip()
        
        idx_nat = lista_nat.index(row_edit['Natureza']) if row_edit is not None else 0
        natureza = st.selectbox("Natureza", lista_nat, index=idx_nat)
        
        idx_tipo = 0 if (row_edit is None or row_edit['Tipo'] == "Débito") else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=idx_tipo, horizontal=True)
        
        valor = st.number_input("Valor R$", min_value=0.00, value=float(row_edit['Valor']) if row_edit is not None else 0.0, format="%.2f")
        justificativa = st.text_area("Justificativa / Histórico", value=row_edit['Justificativa'] if row_edit is not None else "")
        
        if st.form_submit_button(btn_label, use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione --" else None)
            
            if nome_final and valor > 0:
                if st.session_state.edit_index is not None:
                    st.session_state.lancamentos.iloc[st.session_state.edit_index] = [nome_final, natureza, tipo, valor, justificativa]
                    st.session_state.edit_index = None
                else:
                    novo_dado = {'Descrição': nome_final, 'Natureza': natureza, 'Tipo': tipo, 'Valor': valor, 'Justificativa': justificativa}
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, pd.DataFrame([novo_dado])], ignore_index=True)
                st.rerun()

# 4. Interface Principal
if not st.session_state.lancamentos.empty:
    # Encapsulando em um container para garantir estabilidade do layout
    main_container = st.container()
    with main_container:
        tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE Interativa", "⚙️ Gestão"])
        df = st.session_state.lancamentos

        # Cálculos
        rec_tot = df[df['Natureza'] == 'Receita']['Valor'].sum()
        desp_op = df[df['Natureza'] == 'Despesa']['Valor'].sum()
        enc_fin = df[df['Natureza'] == 'Encargos Financeiros']['Valor'].sum()
        ebitda = rec_tot - desp_op
        lucro_real = ebitda - enc_fin

        def calcular_av(valor):
            return f"{(valor / rec_tot * 100):.2f}%" if rec_tot > 0 else "0.00%"

        # --- ABA DRE ---
        with tab_dre:
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<p class="dre-header">RECEITA TOTAL</p><p class="dre-value" style="color:#1E3A8A">R$ {rec_tot:,.2f}</p>', unsafe_allow_html=True)
            c2.markdown(f'<p class="dre-header">EBITDA</p><p class="dre-value" style="color:{"green" if ebitda >=0 else "red"}">R$ {ebitda:,.2f}</p>', unsafe_allow_html=True)
            c3.markdown(f'<p class="dre-header">ENCARGOS FIN.</p><p class="dre-value" style="color:#E11D48">R$ {enc_fin:,.2f}</p>', unsafe_allow_html=True)
            c4.markdown(f'<p class="dre-header">LUCRO REAL</p><p class="dre-value" style="color:{"#10B981" if lucro_real >=0 else "#EF4444"}">R$ {lucro_real:,.2f}</p>', unsafe_allow_html=True)

            st.divider()
            with st.expander(f"🟢 (=) RECEITA OPERACIONAL BRUTA: R$ {rec_tot:,.2f} (100%)", expanded=True):
                df_rec = df[df['Natureza'] == 'Receita'].copy()
                if not df_rec.empty:
                    df_rec['AV %'] = df_rec['Valor'].apply(calcular_av)
                    st.table(df_rec[['Descrição', 'Valor', 'AV %']])

            with st.expander(f"🔴 (-) DESPESAS OPERACIONAIS: R$ {desp_op:,.2f} ({calcular_av(desp_op)})", expanded=True):
                df_desp = df[df['Natureza'] == 'Despesa'].copy()
                if not df_desp.empty:
                    df_desp['AV %'] = df_desp['Valor'].apply(calcular_av)
                    st.table(df_desp[['Descrição', 'Valor', 'AV %']])

            st.markdown(f"<div class='resumo-dre-linha' style='background-color:#e1f5fe; color:#01579b; border-left: 5px solid #01579b;'>➔ (=) EBITDA: R$ {ebitda:,.2f} ({calcular_av(ebitda)})</div>", unsafe_allow_html=True)
            
            cor_f = "#c8e6c9" if lucro_real >= 0 else "#ffcdd2"
            st.markdown(f"<div class='resumo-dre-linha' style='background-color:{cor_f}; color:#2e7d32; font-size:1.3em; border-left: 5px solid #2e7d32;'>🏆 (=) {'LUCRO' if lucro_real >= 0 else 'PREJUÍZO'} LÍQUIDO REAL: R$ {lucro_real:,.2f} ({calcular_av(lucro_real)})</div>", unsafe_allow_html=True)

        # --- ABA RAZONETES ---
        with tab_raz:
            for conta in sorted(df['Descrição'].unique()):
                with st.expander(f"Razonete: {conta}"):
                    c_d, c_c = st.columns(2)
                    df_c = df[df['Descrição'] == conta]
                    v_d, v_c = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum(), df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
                    with c_d:
                        st.write("**DÉBITO**")
                        for i, r in df_c[df_c['Tipo'] == 'Débito'].iterrows(): st.caption(f"#{i+1}: R$ {r['Valor']:,.2f}")
                    with c_c:
                        st.write("**CRÉDITO**")
                        for i, r in df_c[df_c['Tipo'] == 'Crédito'].iterrows(): st.caption(f"#{i+1}: R$ {r['Valor']:,.2f}")
                    st.write(f"**Saldo: R$ {abs(v_d - v_c):,.2f} ({'Devedor' if v_d >= v_c else 'Credor'})**")

        # --- ABA BALANCETE ---
        with tab_bal:
            st.subheader("⚖️ Balancete de Verificação")
            df_pat = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
            resumo = []
            for c in sorted(df_pat['Descrição'].unique()):
                d_c = df_pat[df_pat['Descrição'] == c]
                sd, sc = d_c[d_c['Tipo']=='Débito']['Valor'].sum(), d_c[d_c['Tipo']=='Crédito']['Valor'].sum()
                resumo.append({'Conta': c, 'Devedor': max(0.0, sd-sc), 'Credor': max(0.0, sc-sd)})
            
            resumo.append({'Conta': 'RESULTADO DO PERÍODO', 'Devedor': abs(lucro_real) if lucro_real < 0 else 0.0, 'Credor': lucro_real if lucro_real > 0 else 0.0})
            df_b = pd.DataFrame(resumo)
            st.table(df_b.style.format({'Devedor': 'R$ {:,.2f}', 'Credor': 'R$ {:,.2f}'}))
            
            t_d, t_c = df_b['Devedor'].sum(), df_b['Credor'].sum()
            col_dev, col_cred = st.columns(2)
            c_box = "total-box" if round(t_d, 2) == round(t_c, 2) else "total-box total-box-error"
            col_dev.markdown(f"<div class='{c_box}'>Total Devedor: R$ {t_d:,.2f}</div>", unsafe_allow_html=True)
            col_cred.markdown(f"<div class='{c_box}'>Total Credor: R$ {t_c:,.2f}</div>", unsafe_allow_html=True)

        # --- ABA GESTÃO ---
        with tab_ges:
            for idx, row in df.iterrows():
                c1, c2, c3 = st.columns([4, 0.5, 0.5])
                c1.write(f"**#{idx+1} {row['Descrição']}** | {row['Natureza']} | R$ {row['Valor']:,.2f}")
                if c2.button("📝", key=f"e_{idx}"):
                    st.session_state.edit_index = idx
                    st.rerun()
                if c3.button("🗑️", key=f"d_{idx}"):
                    st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                    st.rerun()
                st.divider()
else:
    st.info("Insira lançamentos na barra lateral para ativar a visualização.")
