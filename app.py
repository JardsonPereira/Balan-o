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
    .total-box { 
        text-align: center; padding: 10px; border-radius: 5px; 
        border: 2px solid #28a745; font-weight: bold; background-color: #ffffff;
    }
    .total-box-error { border-color: #ff4b4b; }
    .justificativa-texto { font-style: italic; color: #555; font-size: 0.9em; margin-top: -10px; }
    
    /* Estilo para os destaques da DRE */
    .dre-header {
        font-size: 24px !important;
        font-weight: bold !important;
        color: #1E3A8A;
        margin-bottom: 5px;
    }
    .dre-value {
        font-size: 32px !important;
        font-weight: 900 !important;
        margin-bottom: 20px;
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
        
        valor_init = float(row_to_edit['Valor']) if row_to_edit is not None else 0.0
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f", value=valor_init)
        
        just_init = row_to_edit['Justificativa'] if row_to_edit is not None else ""
        justificativa = st.text_area("Justificativa / Histórico", value=just_init)
        
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
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE Profissional", "⚙️ Gestão"])
    df = st.session_state.lancamentos

    # --- CÁLCULOS DRE ---
    receitas = df[df['Natureza'] == 'Receita']['Valor'].sum()
    despesas_operacionais = df[df['Natureza'] == 'Despesa']['Valor'].sum()
    encargos_fin = df[df['Natureza'] == 'Encargos Financeiros']['Valor'].sum()
    
    ebitda_val = receitas - despesas_operacionais
    lucro_real = ebitda_val - encargos_fin

    # --- ABA DRE PROFISSIONAL (COM DESTAQUES MAIORES) ---
    with tab_dre:
        st.markdown("### 📊 Indicadores Principais de Resultado")
        
        # Colunas de destaque com HTML personalizado
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown('<p class="dre-header">RECEITA TOTAL</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="dre-value">R$ {receitas:,.2f}</p>', unsafe_allow_html=True)
            
        with c2:
            st.markdown('<p class="dre-header">EBITDA</p>', unsafe_allow_html=True)
            color_ebitda = "green" if ebitda_val >= 0 else "red"
            st.markdown(f'<p class="dre-value" style="color:{color_ebitda}">R$ {ebitda_val:,.2f}</p>', unsafe_allow_html=True)
            
        with c3:
            st.markdown('<p class="dre-header">ENCARGOS FIN.</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="dre-value" style="color:#E11D48">R$ {encargos_fin:,.2f}</p>', unsafe_allow_html=True)
            
        with c4:
            st.markdown('<p class="dre-header">LUCRO REAL</p>', unsafe_allow_html=True)
            color_lucro = "#10B981" if lucro_real >= 0 else "#EF4444"
            st.markdown(f'<p class="dre-value" style="color:{color_lucro}">R$ {lucro_real:,.2f}</p>', unsafe_allow_html=True)

        st.divider()
        st.subheader("📋 Detalhamento da DRE")
        
        # Construção da Tabela de Detalhes
        dre_data = [["(=) RECEITA OPERACIONAL BRUTA", receitas, "100.00%"]]
        for n, v in df[df['Natureza'] == 'Receita'].groupby('Descrição')['Valor'].sum().items():
            dre_data.append([f"   (+) {n}", v, f"{(v/receitas*100):.2f}%" if receitas > 0 else "0%"])
        
        dre_data.append(["(-) DESPESAS OPERACIONAIS", -despesas_operacionais, f"{(despesas_operacionais/receitas*100):.2f}%" if receitas > 0 else "0%"])
        for n, v in df[df['Natureza'] == 'Despesa'].groupby('Descrição')['Valor'].sum().items():
            dre_data.append([f"   (-) {n}", -v, f"{(v/receitas*100):.2f}%" if receitas > 0 else "0%"])
        
        dre_data.append(["(=) EBITDA", ebitda_val, f"{(ebitda_val/receitas*100):.2f}%" if receitas > 0 else "0%"])
        
        dre_data.append(["(-) ENCARGOS FINANCEIROS", -encargos_fin, f"{(encargos_fin/receitas*100):.2f}%" if receitas > 0 else "0%"])
        for n, v in df[df['Natureza'] == 'Encargos Financeiros'].groupby('Descrição')['Valor'].sum().items():
            dre_data.append([f"   (-) {n}", -v, f"{(v/receitas*100):.2f}%" if receitas > 0 else "0%"])
            
        dre_data.append(["(=) LUCRO LÍQUIDO REAL", lucro_real, f"{(lucro_real/receitas*100):.2f}%" if receitas > 0 else "0%"])

        df_dre_f = pd.DataFrame(dre_data, columns=["Descrição", "Valor", "AV (%)"])

        def style_dre(row):
            if "(=)" in row["Descrição"]:
                return ["font-weight: bold; background-color: #f1f5f9", "font-weight: bold; background-color: #f1f5f9", "font-weight: bold; background-color: #f1f5f9"]
            return ["", "", ""]

        st.table(df_dre_f.style.format({"Valor": "R$ {:,.2f}"}).apply(style_dre, axis=1))

    # --- AS OUTRAS ABAS (RAZONETES, BALANCETE, GESTÃO) PERMANECEM IGUAIS ---
    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            with st.expander(f"Razonete: {conta}"):
                c_d, c_c = st.columns(2)
                df_c = df[df['Descrição'] == conta]
                with c_d:
                    st.write("**DÉBITO**")
                    for i, r in df_c[df_c['Tipo'] == 'Débito'].iterrows(): st.caption(f"Ref #{i+1}: R$ {r['Valor']:,.2f}")
                with c_c:
                    st.write("**CRÉDITO**")
                    for i, r in df_c[df_c['Tipo'] == 'Crédito'].iterrows(): st.caption(f"Ref #{i+1}: R$ {r['Valor']:,.2f}")

    with tab_bal:
        st.subheader("Balancete Patrimonial")
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
    st.info("Utilize a barra lateral para inserir o primeiro lançamento.")
