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
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"]
        idx_nat = lista_nat.index(row_to_edit['Natureza']) if row_to_edit is not None else 0
        natureza = st.selectbox("Natureza", lista_nat, index=idx_nat)
        
        tipo_idx = 0 if row_to_edit is None or row_to_edit['Tipo'] == "Débito" else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True, index=tipo_idx)
        
        valor_input = float(row_to_edit['Valor']) if row_to_edit is not None else 0.0
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f", value=valor_input)
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
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE Profissional", "⚙️ Gestão"])
    df = st.session_state.lancamentos

    # --- CÁLCULOS GERAIS ---
    df_rec = df[df['Natureza'] == 'Receita'].groupby('Descrição')['Valor'].sum()
    df_desp = df[df['Natureza'] == 'Despesa'].groupby('Descrição')['Valor'].sum()
    total_receita = df_rec.sum()
    total_despesa = df_desp.sum()
    lucro_liquido = total_receita - total_despesa
    ebitda = lucro_liquido # Simplificado
    margem = (lucro_liquido / total_receita * 100) if total_receita > 0 else 0

    # --- ABA RAZONETES ---
    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            with st.expander(f"Conta: {conta}"):
                c1, c2 = st.columns(2)
                df_c = df[df['Descrição'] == conta]
                c1.write("**DÉBITO**")
                for i, r in df_c[df_c['Tipo'] == 'Débito'].iterrows(): c1.caption(f"R$ {r['Valor']:,.2f} (#{i+1})")
                c2.write("**CRÉDITO**")
                for i, r in df_c[df_c['Tipo'] == 'Crédito'].iterrows(): c2.caption(f"R$ {r['Valor']:,.2f} (#{i+1})")

    # --- ABA BALANCETE ---
    with tab_bal:
        df_pat = df[df['Natureza'].isin(["Ativo", "Passivo", "Patrimônio Líquido"])]
        resumo = []
        for c in sorted(df_pat['Descrição'].unique()):
            d_c = df_pat[df_pat['Descrição'] == c]
            v_d, v_c = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum(), d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
            resumo.append({'Conta': c, 'Saldo Devedor': max(0, v_d-v_c), 'Saldo Credor': max(0, v_c-v_d)})
        resumo.append({'Conta': 'RESULTADO DO PERÍODO', 'Saldo Devedor': abs(lucro_liquido) if lucro_liquido < 0 else 0, 'Saldo Credor': lucro_liquido if lucro_liquido > 0 else 0})
        st.table(pd.DataFrame(resumo).style.format({'Saldo Devedor': 'R$ {:,.2f}', 'Saldo Credor': 'R$ {:,.2f}'}))

    # --- ABA DRE PROFISSIONAL (CORRIGIDA) ---
    with tab_dre:
        st.subheader("📈 Demonstração do Resultado")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Receita Bruta", f"R$ {total_receita:,.2f}")
        m2.metric("EBITDA", f"R$ {ebitda:,.2f}")
        m3.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}")
        m4.metric("Margem Líquida", f"{margem:.2f}%")

        dre_list = []
        dre_list.append(["(=) RECEITA OPERACIONAL BRUTA", total_receita, "100.00%"])
        for n, v in df_rec.items():
            dre_list.append([f"   (+) {n}", v, f"{(v/total_receita*100):.2f}%" if total_receita > 0 else "0.00%"])
        
        dre_list.append(["(-) DESPESAS OPERACIONAIS", -total_despesa, f"{(total_despesa/total_receita*100):.2f}%" if total_receita > 0 else "0.00%"])
        for n, v in df_desp.items():
            dre_list.append([f"   (-) {n}", -v, f"{(v/total_receita*100):.2f}%" if total_receita > 0 else "0.00%"])
        
        dre_list.append(["(=) RESULTADO LÍQUIDO", lucro_liquido, f"{margem:.2f}%"])

        df_dre_final = pd.DataFrame(dre_list, columns=["Descrição", "Valor", "Análise Vertical (AV)"])

        # Formatação manual para evitar erro de applymap/map
        def format_dre(row):
            color = "green" if row["Valor"] >= 0 else "red"
            bold = "font-weight: bold" if "=" in row["Descrição"] else ""
            return [bold, f"color: {color}; {bold}", bold]

        st.table(df_dre_final.style.format({"Valor": "R$ {:,.2f}"}).apply(lambda x: format_dre(x), axis=1))

    # --- ABA GESTÃO ---
    with tab_ges:
        for idx, row in df.iterrows():
            c1, c2, c3 = st.columns([4, 0.5, 0.5])
            with c1:
                st.write(f"**#{idx+1} {row['Descrição']}** | {row['Tipo']}: R$ {row['Valor']:,.2f}")
                st.caption(f"Justificativa: {row['Justificativa']}")
            if c2.button("📝", key=f"e_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
            if c3.button("🗑️", key=f"d_{idx}"):
                st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                st.rerun()
            st.divider()
else:
    st.info("Insira lançamentos na barra lateral para gerar os relatórios.")
