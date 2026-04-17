import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS PARA CORREÇÃO DE ROLAGEM E ESTILO VISUAL ---
st.markdown("""
    <style>
    /* GARANTE A ROLAGEM DA PÁGINA */
    html, body, [data-testid="stAppViewContainer"], .main {
        overflow: auto !important;
        height: auto !important;
    }
    
    /* Espaço extra no fim da página para evitar cortes de visualização */
    .main .block-container {
        padding-bottom: 250px !important;
    }

    /* Estilização dos Cards de Gestão */
    .gestao-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 8px;
    }
    .badge-natureza {
        background-color: #f1f5f9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
    }
    
    /* DRE e Cabeçalhos */
    .dre-header { font-size: 16px !important; font-weight: bold !important; color: #1E3A8A; margin: 0; }
    .dre-value { font-size: 24px !important; font-weight: 900 !important; margin-bottom: 15px; }
    .resumo-dre-linha { font-size: 1.1em; font-weight: bold; padding: 12px; border-radius: 8px; margin-bottom: 8px; }
    
    /* Botões pequenos para gestão */
    .stButton > button {
        padding: 2px 10px;
        font-size: 14px;
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

# 3. Barra Lateral (Lógica de Inserção e Edição)
with st.sidebar:
    lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
    
    if st.session_state.edit_index is not None:
        idx = st.session_state.edit_index
        row_edit = st.session_state.lancamentos.iloc[idx]
        st.header(f"📝 Editar Lançamento")
        if st.button("❌ Cancelar Edição"):
            st.session_state.edit_index = None
            st.rerun()
    else:
        st.header(f"➕ Novo Lançamento")
        row_edit = None

    with st.form("form_contabil", clear_on_submit=True):
        contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
        idx_conta = (contas_existentes.index(row_edit['Descrição']) + 1) if (row_edit is not None and row_edit['Descrição'] in contas_existentes) else 0
        escolha_conta = st.selectbox("Conta Existente", ["-- Selecione --"] + contas_existentes, index=idx_conta)
        nova_conta_input = st.text_input("OU Nova Conta").upper().strip()
        
        idx_nat = lista_nat.index(row_edit['Natureza']) if row_edit is not None else 0
        natureza = st.selectbox("Natureza", lista_nat, index=idx_nat)
        
        idx_tipo = 0 if (row_edit is None or row_edit['Tipo'] == "Débito") else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=idx_tipo, horizontal=True)
        
        valor = st.number_input("Valor (R$)", min_value=0.0, value=float(row_edit['Valor']) if row_edit is not None else 0.0, format="%.2f")
        justificativa = st.text_area("Justificativa", value=row_edit['Justificativa'] if row_edit is not None else "")
        
        if st.form_submit_button("Confirmar Dados", use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione --" else None)
            if nome_final and valor > 0:
                if st.session_state.edit_index is not None:
                    st.session_state.lancamentos.iloc[st.session_state.edit_index] = [nome_final, natureza, tipo, valor, justificativa]
                    st.session_state.edit_index = None
                else:
                    novo_df = pd.DataFrame([{'Descrição': nome_final, 'Natureza': natureza, 'Tipo': tipo, 'Valor': valor, 'Justificativa': justificativa}])
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo_df], ignore_index=True)
                st.rerun()

# 4. Interface Principal
if not st.session_state.lancamentos.empty:
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Auditoria & Balancete", "📈 DRE Detalhada", "⚙️ Gestão"])
    df = st.session_state.lancamentos

    # --- Cálculos Base ---
    rec_tot = df[df['Natureza'] == 'Receita']['Valor'].sum()
    desp_op = df[df['Natureza'] == 'Despesa']['Valor'].sum()
    enc_fin = df[df['Natureza'] == 'Encargos Financeiros']['Valor'].sum()
    ebitda = rec_tot - desp_op
    lucro_real = ebitda - enc_fin
    def calcular_av(v): return f"{(v/rec_tot*100):.2f}%" if rec_tot > 0 else "0.00%"

    # --- ABA BALANCETE (SEM SALDO FINAL) ---
    with tab_bal:
        st.subheader("⚖️ Central de Auditoria e Balancete")

        resumo_balancete = []
        for conta in sorted(df['Descrição'].unique()):
            d_c = df[df['Descrição'] == conta]
            v_d, v_c = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum(), d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
            sd, sc = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
            if sd > 0 or sc > 0:
                resumo_balancete.append({
                    'Conta': conta, 
                    'Natureza': d_c['Natureza'].iloc[0], 
                    'Devedor': sd, 
                    'Credor': sc,
                    'Alerta': (sd > 0 and d_c['Natureza'].iloc[0] in ['Passivo', 'Receita', 'Patrimônio Líquido']) or 
                              (sc > 0 and d_c['Natureza'].iloc[0] in ['Ativo', 'Despesa', 'Encargos Financeiros'])
                })
        
        df_b = pd.DataFrame(resumo_balancete)
        col_auditoria, col_dados = st.columns([1, 2])

        with col_auditoria:
            st.markdown("🔍 **Auditoria Automática**")
            alertas = df_b[df_b['Alerta'] == True]
            if not alertas.empty:
                for _, alt in alertas.iterrows():
                    st.warning(f"**{alt['Conta']}**: Saldo invertido ({alt['Natureza']})")
            else:
                st.success("Saldos coerentes com a natureza.")
            
            t_d, t_c = df_b['Devedor'].sum(), df_b['Credor'].sum()
            dif = round(abs(t_d - t_c), 2)
            if dif == 0:
                st.info(f"✅ Partidas Dobradas OK (R$ {t_d:,.2f})")
            else:
                st.error(f"❌ Erro de Fechamento: R$ {dif:,.2f}")

        with col_dados:
            st.markdown("**Saldos de Verificação**")
            # Exibição sem a coluna Saldo Final e sem a coluna Alerta
            st.dataframe(
                df_b.drop(columns=['Alerta']).style.format({'Devedor': 'R$ {:,.2f}', 'Credor': 'R$ {:,.2f}'}),
                use_container_width=True, hide_index=True
            )
            
            st.markdown("---")
            c_res1, c_res2 = st.columns(2)
            c_res1.metric("Total Devedor", f"R$ {t_d:,.2f}")
            c_res2.metric("Total Credor", f"R$ {t_c:,.2f}")

        st.write("---")
        busca = st.text_input("🔍 Localizar conta no balancete:").upper()
        if busca:
            res_busca = df_b[df_b['Conta'].str.contains(busca)]
            if not res_busca.empty: st.table(res_busca[['Conta', 'Natureza', 'Devedor', 'Credor']])

    # --- ABA DRE DETALHADA ---
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

        with st.expander(f"🔴 (-) ENCARGOS FINANCEIROS: R$ {enc_fin:,.2f} ({calcular_av(enc_fin)})", expanded=True):
            df_enc = df[df['Natureza'] == 'Encargos Financeiros'].copy()
            if not df_enc.empty:
                df_enc['AV %'] = df_enc['Valor'].apply(calcular_av)
                st.table(df_enc[['Descrição', 'Valor', 'AV %']])

        st.markdown(f"<div class='resumo-dre-linha' style='background-color:#e1f5fe; color:#01579b; border-left: 5px solid #01579b;'>➔ (=) EBITDA: R$ {ebitda:,.2f} ({calcular_av(ebitda)})</div>", unsafe_allow_html=True)
        cor_f = "#c8e6c9" if lucro_real >= 0 else "#ffcdd2"
        st.markdown(f"<div class='resumo-dre-linha' style='background-color:{cor_f}; color:#2e7d32; border-left: 5px solid #2e7d32;'>🏆 (=) {'LUCRO' if lucro_real >= 0 else 'PREJUÍZO'} LÍQUIDO REAL: R$ {lucro_real:,.2f} ({calcular_av(lucro_real)})</div>", unsafe_allow_html=True)

    # --- ABA RAZONETES ---
    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            df_c = df[df['Descrição'] == conta]
            natureza_conta = df_c['Natureza'].iloc[0]
            
            with st.expander(f"📖 Razonete: {conta} | 🏷️ Natureza: {natureza_conta}"):
                c_d, c_c = st.columns(2)
                v_d, v_c = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum(), df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
                
                c_d.markdown("#### **DÉBITO**")
                for i, r in df_c[df_c['Tipo'] == 'Débito'].iterrows(): 
                    c_d.caption(f"Ref #{i+1}: R$ {r['Valor']:,.2f}")
                    if r['Justificativa']:
                        c_d.markdown(f"<div style='font-size: 0.8em; color: #64748b; margin-bottom: 10px; padding-left: 10px; border-left: 2px solid #ddd;'>{r['Justificativa']}</div>", unsafe_allow_html=True)
                
                c_c.markdown("#### **CRÉDITO**")
                for i, r in df_c[df_c['Tipo'] == 'Crédito'].iterrows(): 
                    c_c.caption(f"Ref #{i+1}: R$ {r['Valor']:,.2f}")
                    if r['Justificativa']:
                        c_c.markdown(f"<div style='font-size: 0.8em; color: #64748b; margin-bottom: 10px; padding-left: 10px; border-left: 2px solid #ddd;'>{r['Justificativa']}</div>", unsafe_allow_html=True)
                
                st.divider()
                st.write(f"**Saldo Final: R$ {abs(v_d - v_c):,.2f} ({'Devedor' if v_d >= v_c else 'Credor'})**")

    # --- ABA GESTÃO COMPACTA ---
    with tab_ges:
        st.subheader("📋 Gestão de Lançamentos")
        for idx, row in df.iterrows():
            cor_op = "#1E3A8A" if row['Tipo'] == "Débito" else "#10B981"
            st.markdown(f"""
            <div class="gestao-card" style="border-left-color: {cor_op}">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-weight: bold;">{idx+1}. {row['Descrição']}</span>
                    <span class="badge-natureza">{row['Natureza']}</span>
                </div>
                <div style="color: {cor_op}; font-weight: bold; margin: 5px 0;">
                    {"▼" if row['Tipo'] == "Débito" else "▲"} {row['Tipo']}: R$ {row['Valor']:,.2f}
                </div>
                <div style="font-size: 0.85em; color: #64748b;"><i>{row['Justificativa']}</i></div>
            </div>
            """, unsafe_allow_html=True)
            b1, b2, _ = st.columns([0.05, 0.05, 0.9])
            if b1.button("✏️", key=f"e_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
            if b2.button("🗑️", key=f"d_{idx}"):
                st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                st.rerun()
else:
    st.info("👋 Adicione lançamentos na barra lateral para começar.")
