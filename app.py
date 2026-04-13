import streamlit as st
import pandas as pd

# 1. Configuração de Página
st.set_page_config(
    page_title="Balancete Mobile", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

st.title("📑 Contabilidade Digital")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(
        columns=['ID', 'Descrição', 'Natureza', 'Tipo', 'Valor', 'Justificativa']
    )
    st.session_state.id_cont = 1

if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None

# Indicador de Total de Lançamentos
if not st.session_state.lancamentos.empty:
    st.markdown(f"**Total de Lançamentos:** `{len(st.session_state.lancamentos)}`")

# 3. Formulário na Barra Lateral (Criar/Editar)
with st.sidebar:
    if st.session_state.edit_index is not None:
        st.header(f"📝 Editar Lançamento #{st.session_state.lancamentos.loc[st.session_state.edit_index, 'ID']}")
        row_to_edit = st.session_state.lancamentos.loc[st.session_state.edit_index]
        btn_label = "Salvar Alterações"
    else:
        st.header(f"➕ Lançamento Nº {st.session_state.id_cont}")
        row_to_edit = None
        btn_label = "Confirmar Lançamento"

    contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
    opcoes = ["-- Selecione uma conta --"] + contas_existentes

    with st.form("form_mobile", clear_on_submit=True):
        idx_conta = opcoes.index(row_to_edit['Descrição']) if row_to_edit is not None and row_to_edit['Descrição'] in opcoes else 0
        escolha_conta = st.selectbox("Escolher Conta", opcoes, index=idx_conta)
        nova_conta_input = st.text_input("OU Nova Conta").upper().strip()
        
        lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"]
        idx_nat = lista_nat.index(row_to_edit['Natureza']) if row_to_edit is not None else 0
        natureza = st.selectbox("Natureza", lista_nat, index=idx_nat)
        
        tipo_idx = 0 if row_to_edit is None or row_to_edit['Tipo'] == "Débito" else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], horizontal=True, index=tipo_idx)
        
        valor_padrao = float(row_to_edit['Valor']) if row_to_edit is not None else 0.01
        valor = st.number_input("Valor R$", min_value=0.01, format="%.2f", value=valor_padrao)
        
        just_padrao = row_to_edit['Justificativa'] if row_to_edit is not None else ""
        justificativa = st.text_area("Justificativa / Histórico", value=just_padrao)
        
        if st.form_submit_button(btn_label, use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione uma conta --" else None)
            
            if nome_final:
                if st.session_state.edit_index is not None:
                    # Atualizar registro existente
                    st.session_state.lancamentos.at[st.session_state.edit_index, 'Descrição'] = nome_final
                    st.session_state.lancamentos.at[st.session_state.edit_index, 'Natureza'] = natureza
                    st.session_state.lancamentos.at[st.session_state.edit_index, 'Tipo'] = tipo
                    st.session_state.lancamentos.at[st.session_state.edit_index, 'Valor'] = valor
                    st.session_state.lancamentos.at[st.session_state.edit_index, 'Justificativa'] = justificativa
                    st.session_state.edit_index = None
                else:
                    # Adicionar novo registro
                    novo = pd.DataFrame([{
                        'ID': st.session_state.id_cont,
                        'Descrição': nome_final, 'Natureza': natureza, 'Tipo': tipo,
                        'Valor': valor, 'Justificativa': justificativa if justificativa else "Sem justificativa."
                    }])
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                    st.session_state.id_cont += 1
                st.rerun()
    
    if st.session_state.edit_index is not None:
        if st.button("Cancelar Edição", use_container_width=True):
            st.session_state.edit_index = None
            st.rerun()

# 4. Razonetes
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    contas = sorted(df['Descrição'].unique())

    st.subheader("🔍 Razonetes (Contas T)")
    for conta in contas:
        with st.expander(f"📊 {conta}", expanded=False):
            df_c = df[df['Descrição'] == conta]
            col_esq, col_dir = st.columns(2)
            with col_esq:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>DÉBITO</b></p>", unsafe_allow_html=True)
                for _, row in df_c[df_c['Tipo'] == 'Débito'].iterrows():
                    st.button(f"R$ {row['Valor']:,.2f} ({row['ID']})", key=f"d_{row['ID']}", help=row['Justificativa'], use_container_width=True)
            with col_dir:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                for _, row in df_c[df_c['Tipo'] == 'Crédito'].iterrows():
                    st.button(f"R$ {row['Valor']:,.2f} ({row['ID']})", key=f"c_{row['ID']}", help=row['Justificativa'], use_container_width=True)

    # 5. Balancete e Resultado (COM A FÓRMULA MANTIDA)
    st.divider()
    st.subheader("🏁 Balancete e Resultado")
    resumo_bal = []
    tot_rec, tot_desp = 0.0, 0.0
    for conta in contas:
        df_conta = df[df['Descrição'] == conta]
        nat = df_conta['Natureza'].iloc[0]
        v_d, v_c = df_conta[df_conta['Tipo'] == 'Débito']['Valor'].sum(), df_conta[df_conta['Tipo'] == 'Crédito']['Valor'].sum()
        s_d, s_c = max(0.0, v_d - v_c), max(0.0, v_c - v_d)
        resumo_bal.append({'Conta': conta, 'D': s_d, 'C': s_c})
        if nat == "Receita": tot_rec += (v_c - v_d)
        if nat == "Despesa": tot_desp += (v_d - v_c)
    
    st.dataframe(pd.DataFrame(resumo_bal), use_container_width=True, hide_index=True)
    
    # Exibição da Fórmula do Lucro
    res = tot_rec - tot_desp
    st.markdown("### 📈 Apuração do Resultado")
    st.latex(rf"Resultado = {tot_rec:,.2f} (Receitas) - {tot_desp:,.2f} (Despesas)")
    st.metric("LUCRO/PREJUÍZO FINAL", f"R$ {abs(res):,.2f}", delta=f"{res:,.2f}")

    # 6. Gestão (Editar/Excluir)
    with st.expander("⚙️ Gerenciar Lançamentos"):
        for index, row in df.iterrows():
            c_info, c_edit, c_del = st.columns([3, 1, 1])
            c_info.write(f"#{row['ID']} - {row['Descrição']} (R$ {row['Valor']:,.2f})")
            if c_edit.button("📝", key=f"edit_list_{row['ID']}"):
                st.session_state.edit_index = index
                st.rerun()
            if c_del.button("🗑️", key=f"del_list_{row['ID']}"):
                st.session_state.lancamentos = df.drop(index).reset_index(drop=True)
                st.rerun()
else:
    st.info("Aguardando lançamentos.")
