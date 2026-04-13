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

# 3. Formulário na Barra Lateral (Criar/Editar)
with st.sidebar:
    if st.session_state.edit_index is not None:
        st.header(f"📝 Editar #{st.session_state.lancamentos.loc[st.session_state.edit_index, 'ID']}")
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
        justificativa = st.text_area("Justificativa", value=row_to_edit['Justificativa'] if row_to_edit is not None else "")
        
        if st.form_submit_button(btn_label, use_container_width=True):
            nome_final = nova_conta_input if nova_conta_input else (escolha_conta if escolha_conta != "-- Selecione uma conta --" else None)
            if nome_final:
                if st.session_state.edit_index is not None:
                    st.session_state.lancamentos.iloc[st.session_state.edit_index] = [
                        row_to_edit['ID'], nome_final, natureza, tipo, valor, justificativa
                    ]
                    st.session_state.edit_index = None
                else:
                    novo = pd.DataFrame([{'ID': st.session_state.id_cont, 'Descrição': nome_final, 'Natureza': natureza, 'Tipo': tipo, 'Valor': valor, 'Justificativa': justificativa}])
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                    st.session_state.id_cont += 1
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
                debitos = df_c[df_c['Tipo'] == 'Débito']
                for _, r in debitos.iterrows():
                    st.button(f"R$ {r['Valor']:,.2f} ({r['ID']})", key=f"d_{r['ID']}_{conta}", help=r['Justificativa'], use_container_width=True)
                tot_d = debitos['Valor'].sum()
                st.markdown(f"<p style='text-align:right; border-top:1px dashed #888; color:gray;'>Total D: <b>R$ {tot_d:,.2f}</b></p>", unsafe_allow_html=True)
            
            with col_dir:
                st.markdown("<p style='text-align:center; border-bottom:2px solid #555'><b>CRÉDITO</b></p>", unsafe_allow_html=True)
                creditos = df_c[df_c['Tipo'] == 'Crédito']
                for _, r in creditos.iterrows():
                    st.button(f"R$ {r['Valor']:,.2f} ({r['ID']})", key=f"c_{r['ID']}_{conta}", help=r['Justificativa'], use_container_width=True)
                tot_c = creditos['Valor'].sum()
                st.markdown(f"<p style='text-align:right; border-top:1px dashed #888; color:gray;'>Total C: <b>R$ {tot_c:,.2f}</b></p>", unsafe_allow_html=True)

            saldo = tot_d - tot_c
            st.divider()
            if saldo > 0: st.success(f"Saldo Devedor: R$ {abs(saldo):,.2f}")
            elif saldo < 0: st.warning(f"Saldo Credor: R$ {abs(saldo):,.2f}")

    # 5. Balancete de Verificação (COM TOTAIS NAS COLUNAS)
    st.divider()
    st.subheader("🏁 Balancete de Verificação")
    
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
    
    # Exibe a tabela do balancete
    st.dataframe(pd.DataFrame(resumo_bal), use_container_width=True, hide_index=True)
    
    # Soma das colunas do Balancete
    soma_d = sum(item['D'] for item in resumo_bal)
    soma_c = sum(item['C'] for item in resumo_bal)
    
    # Exibição dos totais logo abaixo das colunas
    col_sum_d, col_sum_c = st.columns(2)
    col_sum_d.markdown(f"<div style='text-align: center; border-top: 2px solid #555;'><b>Total D: R$ {soma_d:,.2f}</b></div>", unsafe_allow_html=True)
    col_sum_c.markdown(f"<div style='text-align: center; border-top: 2px solid #555;'><b>Total C: R$ {soma_c:,.2f}</b></div>", unsafe_allow_html=True)
    
    # Verificação de Equilíbrio
    if round(soma_d, 2) == round(soma_c, 2):
        st.toast("Balancete Batido! ✅", icon="⚖️")
    else:
        st.error("Atenção: Balancete Desequilibrado! ❌")

    # 6. Resultado do Período
    st.divider()
    res = tot_rec - tot_desp
    st.markdown("### 📈 Apuração do Resultado")
    st.latex(rf"Resultado = {tot_rec:,.2f} (Receitas) - {tot_desp:,.2f} (Despesas)")
    st.metric("LUCRO/PREJUÍZO FINAL", f"R$ {abs(res):,.2f}", delta=f"{res:,.2f}")

    # 7. Gestão
    with st.expander("⚙️ Gerenciar Lançamentos"):
        for index, row in df.iterrows():
            c_info, c_edit, c_del = st.columns([3, 1, 1])
            c_info.write(f"#{row['ID']} - {row['Descrição']} (R$ {row['Valor']:,.2f})")
            if c_edit.button("📝", key=f"ed_{row['ID']}"):
                st.session_state.edit_index = index
                st.rerun()
            if c_del.button("🗑️", key=f"dl_{row['ID']}"):
                st.session_state.lancamentos = df.drop(index).reset_index(drop=True)
                st.rerun()
else:
    st.info("Aguardando lançamentos.")
