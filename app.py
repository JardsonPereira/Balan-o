import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Estilização Global e Melhoria Visual dos Cards
st.markdown("""
    <style>
    .stApp { overflow-y: auto; }
    
    /* Estilização dos Cards de Gestão */
    .gestao-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .badge-natureza {
        background-color: #E2E8F0;
        color: #475569;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
        text-transform: uppercase;
    }
    .operacao-debito { color: #1E3A8A; font-weight: bold; }
    .operacao-credito { color: #10B981; font-weight: bold; }
    
    /* Estilos DRE e Balancete */
    .dre-header { font-size: 16px !important; font-weight: bold !important; color: #1E3A8A; margin-bottom: 0px; }
    .dre-value { font-size: 24px !important; font-weight: 900 !important; margin-bottom: 15px; }
    .resumo-dre-linha { font-size: 1.1em; font-weight: bold; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
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

# 3. Barra Lateral
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
        nova_conta_input = st.text_input("Nova Conta (Opcional)").upper().strip()
        
        idx_nat = lista_nat.index(row_edit['Natureza']) if row_edit is not None else 0
        natureza = st.selectbox("Natureza", lista_nat, index=idx_nat)
        
        idx_tipo = 0 if (row_edit is None or row_edit['Tipo'] == "Débito") else 1
        tipo = st.radio("Tipo de Operação", ["Débito", "Crédito"], index=idx_tipo, horizontal=True)
        
        valor = st.number_input("Valor (R$)", min_value=0.00, value=float(row_edit['Valor']) if row_edit is not None else 0.0, format="%.2f")
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
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE", "⚙️ Gestão de Lançamentos"])
    df = st.session_state.lancamentos

    # --- Cálculos Reutilizados ---
    rec_tot = df[df['Natureza'] == 'Receita']['Valor'].sum()
    desp_op = df[df['Natureza'] == 'Despesa']['Valor'].sum()
    enc_fin = df[df['Natureza'] == 'Encargos Financeiros']['Valor'].sum()
    ebitda = rec_tot - desp_op
    lucro_real = ebitda - enc_fin
    def calcular_av(valor): return f"{(valor / rec_tot * 100):.2f}%" if rec_tot > 0 else "0.00%"

    # --- ABAS (DRE, Razonetes e Balancete mantidos conforme anterior) ---
    with tab_dre:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<p class="dre-header">RECEITA TOTAL</p><p class="dre-value" style="color:#1E3A8A">R$ {rec_tot:,.2f}</p>', unsafe_allow_html=True)
        c2.markdown(f'<p class="dre-header">EBITDA</p><p class="dre-value" style="color:{"green" if ebitda >=0 else "red"}">R$ {ebitda:,.2f}</p>', unsafe_allow_html=True)
        c3.markdown(f'<p class="dre-header">ENCARGOS FIN.</p><p class="dre-value" style="color:#E11D48">R$ {enc_fin:,.2f}</p>', unsafe_allow_html=True)
        c4.markdown(f'<p class="dre-header">LUCRO REAL</p><p class="dre-value" style="color:{"#10B981" if lucro_real >=0 else "#EF4444"}">R$ {lucro_real:,.2f}</p>', unsafe_allow_html=True)
        st.divider()
        st.markdown(f"<div class='resumo-dre-linha' style='background-color:#e1f5fe; color:#01579b; border-left: 5px solid #01579b;'>➔ (=) EBITDA: R$ {ebitda:,.2f} ({calcular_av(ebitda)})</div>", unsafe_allow_html=True)
        cor_f = "#c8e6c9" if lucro_real >= 0 else "#ffcdd2"
        st.markdown(f"<div class='resumo-dre-linha' style='background-color:{cor_f}; color:#2e7d32; border-left: 5px solid #2e7d32;'>🏆 (=) {'LUCRO' if lucro_real >= 0 else 'PREJUÍZO'} LÍQUIDO: R$ {lucro_real:,.2f} ({calcular_av(lucro_real)})</div>", unsafe_allow_html=True)

    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            with st.expander(f"📖 Razonete: {conta}"):
                c_d, c_c = st.columns(2)
                df_c = df[df['Descrição'] == conta]
                v_d, v_c = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum(), df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
                c_d.write("**DÉBITO**")
                for i, r in df_c[df_c['Tipo'] == 'Débito'].iterrows(): c_d.caption(f"R$ {r['Valor']:,.2f}")
                c_c.write("**CRÉDITO**")
                for i, r in df_c[df_c['Tipo'] == 'Crédito'].iterrows(): c_c.caption(f"R$ {r['Valor']:,.2f}")
                st.write(f"**Saldo: R$ {abs(v_d - v_c):,.2f} ({'Devedor' if v_d >= v_c else 'Credor'})**")

    with tab_bal:
        df_pat = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        resumo = [{'Conta': c, 'Devedor': max(0.0, df_pat[df_pat['Descrição'] == c][df_pat['Tipo']=='Débito']['Valor'].sum() - df_pat[df_pat['Descrição'] == c][df_pat['Tipo']=='Crédito']['Valor'].sum()), 'Credor': max(0.0, df_pat[df_pat['Descrição'] == c][df_pat['Tipo']=='Crédito']['Valor'].sum() - df_pat[df_pat['Descrição'] == c][df_pat['Tipo']=='Débito']['Valor'].sum())} for c in sorted(df_pat['Descrição'].unique())]
        resumo.append({'Conta': 'RESULTADO DO PERÍODO', 'Devedor': abs(lucro_real) if lucro_real < 0 else 0.0, 'Credor': lucro_real if lucro_real > 0 else 0.0})
        st.table(pd.DataFrame(resumo).style.format({'Devedor': 'R$ {:,.2f}', 'Credor': 'R$ {:,.2f}'}))

    # --- ABA GESTÃO (VISUAL MELHORADO) ---
    with tab_ges:
        st.markdown("### 📋 Histórico de Lançamentos")
        
        for idx, row in df.iterrows():
            # Container estilizado como card
            cor_linha = "#1E3A8A" if row['Tipo'] == "Débito" else "#10B981"
            simbolo = "⬇️" if row['Tipo'] == "Débito" else "⬆️"
            
            with st.container():
                st.markdown(f"""
                <div class="gestao-card" style="border-left-color: {cor_linha}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1.1em; font-weight: bold;">{idx+1}. {row['Descrição']}</span>
                        <span class="badge-natureza">{row['Natureza']}</span>
                    </div>
                    <div style="margin-top: 8px;">
                        <span class="{'operacao-debito' if row['Tipo'] == 'Débito' else 'operacao-credito'}">
                            {simbolo} {row['Tipo']}: R$ {row['Valor']:,.2f}
                        </span>
                    </div>
                    <div style="font-size: 0.85em; color: #64748b; margin-top: 5px;">
                        <strong>Justificativa:</strong> {row['Justificativa'] if row['Justificativa'] else 'Sem histórico.'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botões de Ação integrados logo abaixo do card (ou dentro se preferir)
                b1, b2, _ = st.columns([0.1, 0.1, 0.8])
                if b1.button("✏️", key=f"edit_{idx}", help="Editar este lançamento"):
                    st.session_state.edit_index = idx
                    st.rerun()
                if b2.button("🗑️", key=f"del_{idx}", help="Excluir este lançamento"):
                    st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                    st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

else:
    st.info("👋 Bem-vindo! Comece inserindo um lançamento na barra lateral.")
