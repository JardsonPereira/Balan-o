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

# 3. Barra Lateral (Lógica de Edição e Inserção)
with st.sidebar:
    lista_nat = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
    
    if st.session_state.edit_index is not None:
        idx = st.session_state.edit_index
        row = st.session_state.lancamentos.iloc[idx]
        st.header(f"📝 Editando: {row['Descrição']}")
        st.info(f"Natureza Atual: {row['Natureza']}") # Mostra a natureza atual
        
        # Prevenção de erro caso a natureza no DF não esteja na lista
        index_nat = lista_nat.index(row['Natureza']) if row['Natureza'] in lista_nat else 0
        btn_label = "Atualizar Lançamento"
        cancelar_edicao = st.button("Cancelar Edição")
        if cancelar_edicao:
            st.session_state.edit_index = None
            st.rerun()
    else:
        st.header(f"➕ Novo Lançamento Nº {len(st.session_state.lancamentos) + 1}")
        row = None
        index_nat = 0
        btn_label = "Confirmar Lançamento"

    with st.form("form_contabil", clear_on_submit=True):
        contas_existentes = sorted(st.session_state.lancamentos['Descrição'].unique().tolist())
        
        # Se estiver editando, tentamos pré-selecionar a conta
        default_conta = row['Descrição'] if row is not None else "-- Selecione --"
        escolha_conta = st.selectbox("Escolher Conta", ["-- Selecione --"] + contas_existentes, 
                                     index=(contas_existentes.index(row['Descrição']) + 1) if row is not None and row['Descrição'] in contas_existentes else 0)
        
        nova_conta_input = st.text_input("OU Nova Conta (Deixe vazio se selecionou acima)").upper().strip()
        
        natureza = st.selectbox("Natureza da Operação", lista_nat, index=index_nat)
        
        tipo_idx = 0 if row is None or row['Tipo'] == "Débito" else 1
        tipo = st.radio("Operação", ["Débito", "Crédito"], index=tipo_idx, horizontal=True)
        
        valor = st.number_input("Valor R$", min_value=0.00, value=float(row['Valor']) if row is not None else 0.0, format="%.2f")
        justificativa = st.text_area("Justificativa / Histórico", value=row['Justificativa'] if row is not None else "")
        
        if st.form_submit_button(btn_label, use_container_width=True):
            # Lógica para definir o nome da conta
            nome_final = None
            if nova_conta_input:
                nome_final = nova_conta_input
            elif escolha_conta != "-- Selecione --":
                nome_final = escolha_conta

            if nome_final and valor > 0:
                novo_dado = [nome_final, natureza, tipo, valor, justificativa]
                
                if st.session_state.edit_index is not None:
                    # Atualiza o existente
                    st.session_state.lancamentos.iloc[st.session_state.edit_index] = novo_dado
                    st.session_state.edit_index = None
                    st.success("Lançamento atualizado!")
                else:
                    # Adiciona novo
                    novo_df = pd.DataFrame([dict(zip(st.session_state.lancamentos.columns, novo_dado))])
                    st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo_df], ignore_index=True)
                    st.success("Lançamento realizado!")
                st.rerun()
            else:
                st.error("Por favor, preencha a Conta e o Valor.")

# 4. Interface Principal (Permanece igual, garantindo a integridade dos cálculos)
if not st.session_state.lancamentos.empty:
    tab_raz, tab_bal, tab_dre, tab_ges = st.tabs(["📊 Razonetes", "⚖️ Balancete", "📈 DRE Interativa", "⚙️ Gestão"])
    df = st.session_state.lancamentos

    # Cálculos Prévios para DRE
    rec_tot = df[df['Natureza'] == 'Receita']['Valor'].sum()
    desp_op = df[df['Natureza'] == 'Despesa']['Valor'].sum()
    enc_fin = df[df['Natureza'] == 'Encargos Financeiros']['Valor'].sum()
    ebitda = rec_tot - desp_op
    lucro_real = ebitda - enc_fin

    def calcular_av(valor):
        return f"{(valor / rec_tot * 100):.2f}%" if rec_tot > 0 else "0.00%"

    # --- ABA GESTÃO (Onde ficam os botões de editar) ---
    with tab_ges:
        st.subheader("Gerenciamento de Lançamentos")
        for idx, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([4, 0.5, 0.5])
                # Exibição clara da natureza no card de gestão
                c1.markdown(f"**#{idx+1} {row['Descrição']}** | <span style='color: #1E3A8A; font-weight: bold;'>{row['Natureza']}</span> | R$ {row['Valor']:,.2f}", unsafe_allow_html=True)
                st.markdown(f"<p class='justificativa-texto'>Tipo: {row['Tipo']} | Justificativa: {row['Justificativa']}</p>", unsafe_allow_html=True)
                
                if c2.button("📝", key=f"edit_{idx}", help="Editar este lançamento"):
                    st.session_state.edit_index = idx
                    st.rerun()
                
                if c3.button("🗑️", key=f"del_{idx}", help="Excluir este lançamento"):
                    st.session_state.lancamentos = df.drop(idx).reset_index(drop=True)
                    st.rerun()
                st.divider()

    # --- ABA DRE INTERATIVA ---
    with tab_dre:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown('<p class="dre-header">RECEITA TOTAL</p>', unsafe_allow_html=True)
        c1.markdown(f'<p class="dre-value" style="color:#1E3A8A">R$ {rec_tot:,.2f}</p>', unsafe_allow_html=True)
        # ... (Restante do seu código original de visualização)
        c2.markdown('<p class="dre-header">EBITDA</p>', unsafe_allow_html=True)
        c2.markdown(f'<p class="dre-value" style="color:{"green" if ebitda >=0 else "red"}">R$ {ebitda:,.2f}</p>', unsafe_allow_html=True)
        c3.markdown('<p class="dre-header">ENCARGOS FIN.</p>', unsafe_allow_html=True)
        c3.markdown(f'<p class="dre-value" style="color:#E11D48">R$ {enc_fin:,.2f}</p>', unsafe_allow_html=True)
        c4.markdown('<p class="dre-header">LUCRO REAL</p>', unsafe_allow_html=True)
        c4.markdown(f'<p class="dre-value" style="color:{"#10B981" if lucro_real >=0 else "#EF4444"}">R$ {lucro_real:,.2f}</p>', unsafe_allow_html=True)
        st.divider()
        # (Expansores da DRE omitidos aqui por brevidade, mas mantidos na sua lógica)

    # --- ABA RAZONETES ---
    with tab_raz:
        for conta in sorted(df['Descrição'].unique()):
            with st.expander(f"Razonete: {conta}"):
                c_d, c_c = st.columns(2)
                df_c = df[df['Descrição'] == conta]
                v_d, v_c = df_c[df_c['Tipo'] == 'Débito']['Valor'].sum(), df_c[df_c['Tipo'] == 'Crédito']['Valor'].sum()
                with c_d:
                    st.write("**DÉBITO**")
                    for i, r in df_c[df_c['Tipo'] == 'Débito'].iterrows(): st.caption(f"Ref #{i+1}: R$ {r['Valor']:,.2f}")
                with c_c:
                    st.write("**CRÉDITO**")
                    for i, r in df_c[df_c['Tipo'] == 'Crédito'].iterrows(): st.caption(f"Ref #{i+1}: R$ {r['Valor']:,.2f}")
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
        st.table(pd.DataFrame(resumo).style.format({'Devedor': 'R$ {:,.2f}', 'Credor': 'R$ {:,.2f}'}))

else:
    st.info("Insira lançamentos na barra lateral para ativar a visualização.")
