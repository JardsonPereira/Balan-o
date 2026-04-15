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
    .resumo-dre-linha { font-size: 1.1em; font-weight: bold; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
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

    with st.form("form_contabil", clear_on_submit=True):
        contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
        escolha_conta = st.selectbox("Escolher Conta", ["-- Selecione --"] + contas_existentes)
        nova_conta_input = st.text_input("OU Nova Conta").upper().strip()
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        natureza = st.selectbox("Natureza", lista_nat)
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f")
        justificativa = st.text_area("Justificativa")
        
        if st.form_submit_button(btn_label, use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione --" else None)
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

    # Cálculos Prévios
    df_rec = df[df['Natureza'] == 'Receita'].copy()
    df_desp = df[df['Natureza'] == 'Despesa'].copy()
    df_enc = df[df['Natureza'] == 'Encargos Financeiros'].copy()

    rec_tot = df_rec['Valor'].sum()
    desp_op = df_desp['Valor'].sum()
    enc_fin = df_enc['Valor'].sum()
    ebitda = rec_tot - desp_op
    lucro_real = ebitda - enc_fin

    # Cálculo da Análise Vertical (AV) por linha
    def calcular_av(valor):
        return f"{(valor / rec_tot * 100):.2f}%" if rec_tot > 0 else "0.00%"

    # --- ABA DRE INTERATIVA ---
    with tab_dre:
        # Indicadores de Topo (KPIs)
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
        st.subheader("📂 Detalhamento com Análise Vertical (AV %)")
        st.info("A coluna **AV %** indica o peso de cada lançamento em relação à Receita Total.")

        # MENU 1: RECEITAS
        with st.expander(f"🟢 (=) RECEITA OPERACIONAL BRUTA: R$ {rec_tot:,.2f} (100%)", expanded=True):
            if not df_rec.empty:
                df_rec['AV %'] = df_rec['Valor'].apply(calcular_av)
                st.dataframe(df_rec[['Descrição', 'Valor', 'AV %', 'Justificativa']], use_container_width=True, hide_index=True)
            else:
                st.write("Nenhuma receita lançada.")

        # MENU 2: DESPESAS OPERACIONAIS
        with st.expander(f"🔴 (-) DESPESAS OPERACIONAIS: R$ {desp_op:,.2f} ({calcular_av(desp_op)})", expanded=True):
            if not df_desp.empty:
                df_desp['AV %'] = df_desp['Valor'].apply(calcular_av)
                st.dataframe(df_desp[['Descrição', 'Valor', 'AV %', 'Justificativa']], use_container_width=True, hide_index=True)
            else:
                st.write("Nenhuma despesa operacional lançada.")

        # LINHA EBITDA
        st.markdown(f"<div class='resumo-dre-linha' style='background-color:#e1f5fe; color:#01579b; border-left: 5px solid #01579b;'>➔ (=) EBITDA: R$ {ebitda:,.2f} ({calcular_av(ebitda)})</div>", unsafe_allow_html=True)

        # MENU 3: ENCARGOS FINANCEIROS
        with st.expander(f"🟠 (-) ENCARGOS FINANCEIROS: R$ {enc_fin:,.2f} ({calcular_av(enc_fin)})", expanded=True):
            if not df_enc.empty:
                df_enc['AV %'] = df_enc['Valor'].apply(calcular_av)
                st.dataframe(df_enc[['Descrição', 'Valor', 'AV %', 'Justificativa']], use_container_width=True, hide_index=True)
            else:
                st.write("Nenhum encargo financeiro lançado.")

        # RESULTADO FINAL
        cor_f = "#c8e6c9" if lucro_real >= 0 else "#ffcdd2"
        txt_f = "LUCRO" if lucro_real >= 0 else "PREJUÍZO"
        st.markdown(f"<div class='resumo-dre-linha' style='background-color:{cor_f}; color:#2e7d32; font-size:1.3em; border-left: 5px solid #2e7d32;'>🏆 (=) {txt_f} LÍQUIDO REAL: R$ {lucro_real:,.2f} ({calcular_av(lucro_real)})</div>", unsafe_allow_html=True)

    # --- ABA RAZONETES ---
    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            with st.expander(f"Razonete: {conta}"):
                c_d, c_c = st.columns(2)
                df_c = df[df['Descrição'] == conta]
                v_d, v_c = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum(), df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
                with c_d:
                    st.write("**DÉBITO**")
                    for i, r in df_c[df_c['Tipo'] == 'Débito'].iterrows(): st.caption(f"R$ {r['Valor']:,.2f} - {r['Justificativa']}")
                with c_c:
                    st.write("**CRÉDITO**")
                    for i, r in df_c[df_c['Tipo'] == 'Crédito'].iterrows(): st.caption(f"R$ {r['Valor']:,.2f} - {r['Justificativa']}")
                st.write(f"**Saldo: R$ {abs(v_d - v_c):,.2f} ({'Devedor' if v_d >= v_c else 'Credor'})**")

    # --- ABA BALANCETE ---
    with tab_bal:
        df_pat = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        resumo = []
        for c in sorted(df_pat['Descrição'].unique()):
            d_c = df_pat[df_pat['Descrição'] == c]
            sd, sc = d_c[d_c['Tipo']=='Débito']['Valor'].sum(), d_c[d_c['Tipo']=='Crédito']['Valor'].sum()
            resumo.append({'Conta': c, 'Devedor': max(0.0, sd-sc), 'Credor': max(0.0, sc-sd)})
        resumo.append({'Conta': 'RESULTADO DO PERÍODO', 'Devedor': abs(lucro_real) if lucro_real < 0 else 0, 'Credor': lucro_real if lucro_real > 0 else 0})
        df_b = pd.DataFrame(resumo)
        st.table(df_b.style.format({'Devedor': 'R$ {:,.2f}', 'Credor': 'R$ {:,.2f}'}))
        
        t_d, t_c = df_b['Devedor'].sum(), df_b['Credor'].sum()
        col_esp, col_dev, col_cred = st.columns([1.5, 1, 1])
        c_box = "total-box" if round(t_d, 2) == round(t_c, 2) else "total-box total-box-error"
        col_dev.markdown(f"<div class='{c_box}'>Total Devedor<br>R$ {t_d:,.2f}</div>", unsafe_allow_html=True)
        col_cred.markdown(f"<div class='{c_box}'>Total Credor<br>R$ {t_c:,.2f}</div>", unsafe_allow_html=True)

    # --- ABA GESTÃO ---
    with tab_ges:
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([4, 0.5, 0.5])
            c1.write(f"**#{idx+1} {row['Descrição']}** | {row['Natureza']} | R$ {row['Valor']:,.2f}")
            st.markdown(f"<p class='justificativa-texto' style='margin-left: 0px;'>Justificativa: {row['Justificativa']}</p>", unsafe_allow_html=True)
            if c2.button("📝", key=f"e_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
            if c3.button("🗑️", key=f"d_{idx}"):
                st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                st.rerun()
            st.divider()
else:
    st.info("Insira lançamentos na barra lateral para ativar a visualização.")
