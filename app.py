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
        
        # NATUREZAS ATUALIZADAS: Incluindo Encargos Financeiros
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

    # --- LÓGICA DE CÁLCULO PROFISSIONAL ---
    receitas = df[df['Natureza'] == 'Receita']['Valor'].sum()
    despesas_operacionais = df[df['Natureza'] == 'Despesa']['Valor'].sum()
    encargos_financeiros = df[df['Natureza'] == 'Encargos Financeiros']['Valor'].sum()
    
    # EBITDA: Receitas - Despesas Operacionais (Não inclui juros/financeiro)
    ebitda_valor = receitas - despesas_operacionais
    # Lucro Líquido: EBITDA - Encargos Financeiros
    lucro_real = ebitda_valor - encargos_financeiros
    margem_real = (lucro_real / receitas * 100) if receitas > 0 else 0

    # --- ABA RAZONETES ---
    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            with st.expander(f"Conta: {conta}", expanded=False):
                df_c = df[df['Descrição'] == conta]
                col_d, col_c = st.columns(2)
                with col_d:
                    st.markdown("<p style='text-align:center; border-bottom:1px solid #555'><b>DÉBITO</b></p>", unsafe_allow_html=True)
                    debs = df_c[df_c['Tipo'] == 'Débito']
                    for i, r in debs.iterrows():
                        st.caption(f"Ref #{i+1}: {r['Justificativa']}")
                        st.button(f"R$ {r['Valor']:,.2f}", key=f"rd_{i}_{conta}", use_container_width=True)
                    tot_d = debs['Valor'].sum()
                with col_c:
                    st.markdown("<p style='text-align:center; border-bottom:1px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                    creds = df_c[df_c['Tipo'] == 'Crédito']
                    for i, r in creds.iterrows():
                        st.caption(f"Ref #{i+1}: {r['Justificativa']}")
                        st.button(f"R$ {r['Valor']:,.2f}", key=f"rc_{i}_{conta}", use_container_width=True)
                    tot_c = creds['Valor'].sum()
                
                saldo = tot_d - tot_c
                if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
                elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")
                else: st.info("Saldo Zero")

    # --- ABA BALANCETE ---
    with tab_bal:
        st.subheader("Balancete de Verificação Patrimonial")
        # No balancete, Ativo/Passivo/PL são permanentes. O resultado (Lucro Real) entra no PL.
        df_pat = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        resumo_bal = []
        for c in sorted(df_pat['Descrição'].unique()):
            d_c = df_pat[df_pat['Descrição'] == c]
            v_d, v_c = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum(), d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
            resumo_bal.append({'Conta': c, 'Saldo Devedor': max(0.0, v_d - v_c), 'Saldo Credor': max(0.0, v_c - v_d)})
        
        # Inclusão do Lucro Real
        resumo_bal.append({'Conta': 'LUCRO/PREJUÍZO LÍQUIDO (RESULTADO)', 'Saldo Devedor': abs(lucro_real) if lucro_real < 0 else 0, 'Saldo Credor': lucro_real if lucro_real > 0 else 0})

        df_final_bal = pd.DataFrame(resumo_bal)
        st.table(df_final_bal.style.format({'Saldo Devedor': 'R$ {:,.2f}', 'Saldo Credor': 'R$ {:,.2f}'}))
        
        t_dev, t_cred = df_final_bal['Saldo Devedor'].sum(), df_final_bal['Saldo Credor'].sum()
        col_esp, col_dev, col_cred = st.columns([1.5, 1, 1])
        class_box = "total-box" if round(t_dev, 2) == round(t_cred, 2) else "total-box total-box-error"
        col_dev.markdown(f"<div class='{class_box}'>Total Devedor<br>R$ {t_dev:,.2f}</div>", unsafe_allow_html=True)
        col_cred.markdown(f"<div class='{class_box}'>Total Credor<br>R$ {t_cred:,.2f}</div>", unsafe_allow_html=True)

    # --- ABA DRE PROFISSIONAL (ATUALIZADA) ---
    with tab_dre:
        st.subheader("📈 Demonstração do Resultado (Dedução EBITDA)")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Receita Total", f"R$ {receitas:,.2f}")
        m2.metric("EBITDA", f"R$ {ebitda_valor:,.2f}")
        m3.metric("Lucro Real", f"R$ {lucro_real:,.2f}")
        m4.metric("Margem Real", f"{margem_real:.2f}%")

        dre_data = [["(=) RECEITA OPERACIONAL BRUTA", receitas, "100.00%"]]
        # Detalhar Receitas
        for n, v in df[df['Natureza'] == 'Receita'].groupby('Descrição')['Valor'].sum().items():
            dre_data.append([f"   (+) {n}", v, f"{(v/receitas*100):.2f}%" if receitas > 0 else "0%"])
        
        # Despesas Operacionais
        dre_data.append(["(-) DESPESAS OPERACIONAIS", -despesas_operacionais, f"{(despesas_operacionais/receitas*100):.2f}%" if receitas > 0 else "0%"])
        for n, v in df[df['Natureza'] == 'Despesa'].groupby('Descrição')['Valor'].sum().items():
            dre_data.append([f"   (-) {n}", -v, f"{(v/receitas*100):.2f}%" if receitas > 0 else "0%"])
        
        # Subtotal EBITDA
        dre_data.append(["(=) EBITDA", ebitda_valor, f"{(ebitda_valor/receitas*100):.2f}%" if receitas > 0 else "0%"])
        
        # Encargos Financeiros (Dedução do EBITDA)
        dre_data.append(["(-) ENCARGOS FINANCEIROS", -encargos_financeiros, f"{(encargos_financeiros/receitas*100):.2f}%" if receitas > 0 else "0%"])
        for n, v in df[df['Natureza'] == 'Encargos Financeiros'].groupby('Descrição')['Valor'].sum().items():
            dre_data.append([f"   (-) {n}", -v, f"{(v/receitas*100):.2f}%" if receitas > 0 else "0%"])
            
        # Resultado Final
        dre_data.append(["(=) LUCRO LÍQUIDO REAL", lucro_real, f"{margem_real:.2f}%"])

        df_dre_f = pd.DataFrame(dre_data, columns=["Descrição", "Valor", "AV (%)"])

        def style_dre(row):
            if "(=)" in row["Descrição"]:
                color = "blue" if "EBITDA" in row["Descrição"] else ("green" if row["Valor"] >= 0 else "red")
                return ["font-weight: bold", f"color: {color}; font-weight: bold", "font-weight: bold"]
            return ["", "color: #333", ""]

        st.table(df_dre_f.style.format({"Valor": "R$ {:,.2f}"}).apply(style_dre, axis=1))

    # --- ABA GESTÃO ---
    with tab_ges:
        st.subheader("Histórico de Lançamentos")
        for idx, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([4, 0.5, 0.5])
                with c1:
                    st.write(f"**#{idx+1} {row['Descrição']}** | {row['Natureza']} | R$ {row['Valor']:,.2f}")
                    st.markdown(f"<p class='justificativa-texto'>Justificativa: {row['Justificativa'] if row['Justificativa'] else 'N/A'}</p>", unsafe_allow_html=True)
                if c2.button("📝", key=f"e_{idx}"):
                    st.session_state.edit_index = idx
                    st.rerun()
                if c3.button("🗑️", key=f"d_{idx}"):
                    st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                    st.rerun()
                st.divider()
else:
    st.info("Utilize a barra lateral para inserir lançamentos.")
