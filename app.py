import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Contabilidade Digital Pro", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

st.title("📑 Sistema Contábil Integrado")

# 2. Inicialização do Estado (Preservando dados)
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor', 'Justificativa']
    )
    st.session_state.id_cont = 1

if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None

# 3. Formulário na Barra Lateral (Com Função Editar)
with st.sidebar:
    if st.session_state.edit_index is not None:
        st.header(f"📝 Editar Lançamento #{st.session_state.lancamentos.loc[st.session_state.edit_index, 'ID']}")
        row_to_edit = st.session_state.lancamentos.loc[st.session_state.edit_index]
        btn_label = "Salvar Alterações"
    else:
        st.header(f"➕ Novo Lançamento Nº {st.session_state.id_cont}")
        row_to_edit = None
        btn_label = "Confirmar Lançamento"

    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes = ["-- Selecione uma conta --"] + contas_existentes

    with st.form("form_contabil", clear_on_submit=True):
        idx_conta = opcoes.index(row_to_edit['Descrição']) if row_to_edit is not None and row_to_edit['Descrição'] in opcoes else 0
        escolha_conta = st.selectbox("Escolher Conta", opcoes, index=idx_conta)
        nova_conta_input = st.text_input("OU Nova Conta (Texto)").upper().strip()
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"]
        idx_nat = lista_nat.index(row_to_edit['Natureza']) if row_to_edit is not None else 0
        natureza = st.selectbox("Natureza", lista_nat, index=idx_nat)
        
        tipo_idx = 0 if row_to_edit is None or row_to_edit['Tipo'] == "Débito" else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True, index=tipo_idx)
        
        valor_padrao = float(row_to_edit['Valor']) if row_to_edit is not None else 0.00
        valor = st.number_input("Valor R$", min_value=0.00, format="%.2f", value=valor_padrao)
        
        justificativa = st.text_area("Justificativa / Histórico", value=row_to_edit['Justificativa'] if row_to_edit is not None else "")
        
        if st.form_submit_button(btn_label, use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione uma conta --" else None)
            if nome_final and valor > 0:
                if st.session_state.edit_index is not None:
                    # Aplica a edição
                    st.session_state.lancamentos.iloc[st.session_state.edit_index] = [
                        row_to_edit['ID'], nome_final, natureza, tipo, valor, justificativa
                    ]
                    st.session_state.edit_index = None
                else:
                    # Novo lançamento
                    novo = pd.DataFrame([{'ID': st.session_state.id_cont, 'Descrição': nome_final, 'Natureza': natureza, 'Tipo': tipo, 'Valor': valor, 'Justificativa': justificativa}])
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                    st.session_state.id_cont += 1
                st.rerun()

    if st.session_state.edit_index is not None:
        if st.button("Cancelar Edição", use_container_width=True):
            st.session_state.edit_index = None
            st.rerun()

# 4. Interface Principal por Abas
if not st.session_state.lancamentos.empty:
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE", "⚙️ Gestão"])
    
    df = st.session_state.lancamentos
    contas = sorted(df['Descrição'].unique())

    # --- ABA RAZONETES ---
    with tab_raz:
        for conta in contas:
            with st.expander(f"Conta: {conta}", expanded=True):
                df_c = df[df['Descrição'] == conta]
                col_d, col_c = st.columns(2)
                
                with col_d:
                    st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>DÉBITO</b></p>", unsafe_allow_html=True)
                    debs = df_c[df_c['Tipo'] == 'Débito']
                    for _, r in debs.iterrows():
                        st.button(f"R$ {r['Valor']:,.2f} ({r['ID']})", key=f"raz_d_{r['ID']}_{conta}", help=f"HISTÓRICO: {r['Justificativa']}", use_container_width=True)
                    tot_d = debs['Valor'].sum()
                    st.markdown(f"<p style='text-align:right; border-top:1px solid #eee;'>Total D: <b>R$ {tot_d:,.2f}</b></p>", unsafe_allow_html=True)
                
                with col_c:
                    st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                    creds = df_c[df_c['Tipo'] == 'Crédito']
                    for _, r in creds.iterrows():
                        st.button(f"R$ {r['Valor']:,.2f} ({r['ID']})", key=f"raz_c_{r['ID']}_{conta}", help=f"HISTÓRICO: {r['Justificativa']}", use_container_width=True)
                    tot_c = creds['Valor'].sum()
                    st.markdown(f"<p style='text-align:right; border-top:1px solid #eee;'>Total C: <b>R$ {tot_c:,.2f}</b></p>", unsafe_allow_html=True)
                
                saldo = tot_d - tot_c
                if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
                elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")

    # --- ABA BALANCETE ---
    with tab_bal:
        st.subheader("Balancete de Verificação")
        resumo_bal = []
        for c in contas:
            d_c = df[df['Descrição'] == c]
            v_d, v_c = d_c[d_c['Tipo'] == 'Débito']['Valor'].sum(), d_c[d_c['Tipo'] == 'Crédito']['Valor'].sum()
            s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
            resumo_bal.append({'Conta': c, 'D': s_d, 'C': s_c})
        
        st.table(pd.DataFrame(resumo_bal))
        
        sd_total = sum(x['D'] for x in resumo_bal)
        sc_total = sum(x['C'] for x in resumo_bal)
        
        c_tot_d, c_tot_c = st.columns(2)
        c_tot_d.markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:10px'><b>Total D: R$ {sd_total:,.2f}</b></div>", unsafe_allow_html=True)
        c_tot_c.markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:10px'><b>Total C: R$ {sc_total:,.2f}</b></div>", unsafe_allow_html=True)

    # --- ABA DRE ---
    with tab_dre:
        st.subheader("DRE - Demonstração do Resultado")
        recs = df[df['Natureza'] == 'Receita'].groupby('Descrição')['Valor'].sum()
        desps = df[df['Natureza'] == 'Despesa'].groupby('Descrição')['Valor'].sum()
        
        st.markdown("**(+) RECEITAS**")
        for n, v in recs.items(): st.write(f"{n}: R$ {v:,.2f}")
        st.write(f"**Total Receitas: R$ {recs.sum():,.2f}**")
        
        st.markdown("---")
        st.markdown("**(-) DESPESAS**")
        for n, v in desps.items(): st.write(f"{n}: (R$ {v:,.2f})")
        st.write(f"**Total Despesas: (R$ {desps.sum():,.2f})**")
        
        resultado = recs.sum() - desps.sum()
        st.divider()
        st.latex(rf"Resultado = {recs.sum():,.2f} - {desps.sum():,.2f}")
        if resultado >= 0: st.success(f"### LUCRO LÍQUIDO: R$ {resultado:,.2f}")
        else: st.error(f"### PREJUÍZO LÍQUIDO: R$ {abs(resultado):,.2f}")

    # --- ABA GESTÃO (Identificando Natureza) ---
    with tab_ges:
        st.subheader("Histórico e Gestão de Lançamentos")
        st.info("Abaixo você pode conferir a Natureza e o Tipo de cada operação registrada.")
        
        for idx, row in df.iterrows():
            with st.container():
                col_info, col_edit, col_del = st.columns([4, 0.5, 0.5])
                
                # Definindo cor baseada na natureza para facilitar visualização
                emoji_nat = "💰" if row['Natureza'] in ['Ativo', 'Receita'] else "📉"
                
                with col_info:
                    st.markdown(f"""
                    **{emoji_nat} #{row['ID']} - {row['Descrição']}** **Natureza:** `{row['Natureza']}` | **Tipo:** *{row['Tipo']}* **Valor:** R$ {row['Valor']:,.2f}  
                    *Histórico: {row['Justificativa'] if row['Justificativa'] else 'Sem histórico.'}*
                    """)
                
                if col_edit.button("📝", key=f"edit_btn_{idx}", help="Editar lançamento"):
                    st.session_state.edit_index = idx
                    st.rerun()
                
                if col_del.button("🗑️", key=f"del_btn_{idx}", help="Excluir lançamento"):
                    st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                    st.rerun()
                
                st.divider()

else:
    st.info("Utilize a barra lateral para inserir o primeiro lançamento.")
