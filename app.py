import streamlit as st
import pandas as pd

# 1. Configuração para Celular
st.set_page_config(
    page_title="Balancete Mobile Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📑 Balancete Detalhado")

# 2. Inicialização do Estado
if 'lancamentos' not in st.session_state:
    st.session_state.lancamentos = pd.DataFrame(columns=['ID', 'Descrição', 'Natureza', 'Subgrupo', 'Tipo', 'Valor'])
    st.session_state.id_cont = 0

# 3. Interface de Entrada
with st.expander("➕ Novo Lançamento", expanded=True):
    with st.form("form_contabil", clear_on_submit=True):
        desc = st.text_input("Descrição (Ex: Caixa, Salários)")
        natureza = st.selectbox("Natureza", ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa"])
        
        # A MÁGICA ACONTECE AQUI: 
        # O subgrupo só é definido se for Ativo ou Passivo.
        # No Streamlit, para esconder o campo visualmente dentro de um form, 
        # usamos uma lógica de placeholder ou container.
        
        subgrupo_opcoes = ["Circulante", "Não Circulante"]
        
        tipo = st.selectbox("Operação", ["Débito", "Crédito"])
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        
        # Como estamos dentro de um st.form, precisamos tratar o subgrupo 
        # de forma que ele só seja capturado se a natureza permitir.
        sub_escolhido = st.selectbox("Subgrupo (Apenas para Ativo/Passivo)", ["N/A"] + subgrupo_opcoes)
        
        if st.form_submit_button("Confirmar Lançamento"):
            # Validação extra: se for Ativo/Passivo, não pode ser N/A
            if natureza in ["Ativo", "Passivo"] and sub_escolhido == "N/A":
                st.error("Para Ativo ou Passivo, selecione Circulante ou Não Circulante.")
            elif desc and valor > 0:
                # Se não for Ativo/Passivo, forçamos N/A independente da escolha
                final_sub = sub_escolhido if natureza in ["Ativo", "Passivo"] else "N/A"
                
                novo = pd.DataFrame([{
                    'ID': st.session_state.id_cont, 
                    'Descrição': desc.upper(), 
                    'Natureza': natureza, 
                    'Subgrupo': final_sub,
                    'Tipo': tipo, 
                    'Valor': valor
                }])
                st.session_state.lancamentos = pd.concat([st.session_state.lancamentos, novo], ignore_index=True)
                st.session_state.id_cont += 1
                st.rerun()

# 4. Processamento dos Dados
if not st.session_state.lancamentos.empty:
    df = st.session_state.lancamentos
    resumo = []
    for conta in df['Descrição'].unique():
        d_conta = df[df['Descrição'] == conta]
        deb = d_conta[d_conta['Tipo'] == 'Débito']['Valor'].sum()
        cre = d_conta[d_conta['Tipo'] == 'Crédito']['Valor'].sum()
        nat = d_conta['Natureza'].iloc[0]
        sub = d_conta['Subgrupo'].iloc[0]
        
        saldo_dev = max(0, deb - cre)
        saldo_cre = max(0, cre - deb)
        resumo.append({'Conta': conta, 'Natureza': nat, 'Subgrupo': sub, 'D': saldo_dev, 'C': saldo_cre})
    
    df_resumo = pd.DataFrame(resumo)

    # 5. Exibição em Colunas (Balanço Patrimonial)
    st.subheader("📈 Balanço Patrimonial")
    col_ativo, col_passivo, col_pl = st.columns(3)

    with col_ativo:
        st.markdown("### ATIVO")
        st.write("**Circulante**")
        df_ac = df_resumo[(df_resumo['Natureza'] == "Ativo") & (df_resumo['Subgrupo'] == "Circulante")]
        st.dataframe(df_ac[['Conta', 'D']], use_container_width=True, hide_index=True)
        
        st.write("**Não Circulante**")
        df_anc = df_resumo[(df_resumo['Natureza'] == "Ativo") & (df_resumo['Subgrupo'] == "Não Circulante")]
        st.dataframe(df_anc[['Conta', 'D']], use_container_width=True, hide_index=True)
        st.info(f"Total: R$ {df_ac['D'].sum() + df_anc['D'].sum():,.2f}")

    with col_passivo
