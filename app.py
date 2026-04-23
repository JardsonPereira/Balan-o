# --- CSS PARA DESIGN PREMIUM ---
st.markdown("""
    <style>
    /* Importação de Fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Fundo do App */
    .stApp {
        background-color: #f8fafc;
    }

    /* Customização dos Botões do Menu (Tabs) */
    div.stButton > button {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        background-color: white;
        transition: all 0.3s ease;
        font-weight: 600;
        color: #475569;
    }
    
    div.stButton > button:hover {
        border-color: #3b82f6;
        color: #3b82f6;
        background-color: #eff6ff;
    }

    /* Estilo do Card Razonete */
    .conta-card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 24px;
        overflow: hidden;
    }

    .conta-titulo {
        background: #1e293b;
        color: #f8fafc;
        padding: 12px;
        text-align: center;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        font-size: 0.9rem;
    }

    .conta-corpo {
        display: flex;
        min-height: 100px;
        position: relative;
    }

    /* A Linha do "T" Contábil */
    .conta-corpo::after {
        content: "";
        position: absolute;
        left: 50%;
        top: 0;
        bottom: 0;
        width: 1.5px;
        background-color: #cbd5e1;
    }

    .lado-debito, .lado-credito {
        flex: 1;
        padding: 12px;
    }

    .valor-item {
        font-size: 0.85rem;
        margin-bottom: 6px;
        padding: 4px 8px;
        border-radius: 4px;
    }

    .valor-deb { 
        color: #059669; 
        background: #ecfdf5;
        border-left: 3px solid #10b981;
    }

    .valor-cre { 
        color: #dc2626; 
        background: #fef2f2;
        border-right: 3px solid #ef4444;
        text-align: right;
    }

    .just-hint {
        font-size: 0.7rem;
        color: #64748b;
        display: block;
        font-weight: 400;
    }

    .conta-rodape {
        padding: 10px;
        background: #f1f5f9;
        border-top: 1.5px solid #1e293b;
        text-align: center;
        font-weight: 700;
        font-size: 0.9rem;
    }

    /* Grupo Header */
    .grupo-header {
        background: linear-gradient(90deg, #334155 0%, #1e293b 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        margin: 30px 0 15px 0;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Esconder o erro de estatísticas do Streamlit no loop de colunas */
    [data-testid="stExpander"] { border: none; box-shadow: none; background: white; border-radius: 8px; margin-bottom: 5px;}
    </style>
""", unsafe_allow_html=True)

# --- INTERFACE PRINCIPAL ---
st.title("📑 Sistema Contábil Digital")
st.markdown("<p style='color: #64748b; margin-top: -20px;'>Gestão de lançamentos e demonstrações financeiras</p>", unsafe_allow_html=True)

# --- MENU COM ESTILO DE TABS ---
col_nav = st.columns(4)
botoes = [
    ("📊 Razonetes", "📊 Razonetes"),
    ("🧾 Balancete", "🧾 Balancete"),
    ("📈 DRE", "📈 DRE"),
    ("⚙️ Gestão", "⚙️ Gestão")
]

for i, (label, opcao) in enumerate(botoes):
    # Aplica um estilo diferente se o botão for a opção selecionada
    if col_nav[i].button(label, use_container_width=True):
        st.session_state.menu_opcao = opcao

opcao_menu = st.session_state.menu_opcao

# Indicador visual de qual menu está ativo
st.markdown(f"<div style='text-align: center; margin-top: -15px;'><small>Visualizando: <b>{opcao_menu}</b></small></div>", unsafe_allow_html=True)
st.divider()

if not df.empty:
    if opcao_menu == "📊 Razonetes":
        grupos = ["Ativo", "Passivo", "Patrimônio Líquido", "Receita", "Despesa", "Encargos Financeiros"]
        for grupo in grupos:
            df_grupo = df[df['natureza'] == grupo]
            if not df_grupo.empty:
                st.markdown(f"<div class='grupo-header'>{grupo.upper()}</div>", unsafe_allow_html=True)
                contas_grupo = sorted(df_grupo['descricao'].unique())
                
                # Grid de 3 colunas para Desktop, Streamlit ajusta automático no Mobile
                cols = st.columns(3)
                for i, conta in enumerate(contas_grupo):
                    with cols[i % 3]:
                        df_c = df_grupo[df_grupo['descricao'] == conta]
                        v_deb_sum = df_c[df_c['tipo'] == 'Débito']['valor'].sum()
                        v_cre_sum = df_c[df_c['tipo'] == 'Crédito']['valor'].sum()
                        saldo = v_deb_sum - v_cre_sum
                        
                        deb_html = "".join([f"<div class='valor-item valor-deb'>{r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Débito'].iterrows()])
                        cre_html = "".join([f"<div class='valor-item valor-cre'>{r['valor']:,.2f}<span class='just-hint'>{r['justificativa']}</span></div>" for _, r in df_c[df_c['tipo'] == 'Crédito'].iterrows()])
                        
                        if saldo > 0:
                            txt_saldo = f"Saldo Devedor: R$ {saldo:,.2f}"
                            cor_saldo = "#059669"
                        elif saldo < 0:
                            txt_saldo = f"Saldo Credor: R$ {abs(saldo):,.2f}"
                            cor_saldo = "#dc2626"
                        else:
                            txt_saldo = "Conta Zerada"
                            cor_saldo = "#64748b"

                        st.markdown(f"""
                            <div class="conta-card">
                                <div class="conta-titulo">{conta}</div>
                                <div class="conta-corpo">
                                    <div class="lado-debito">{deb_html}</div>
                                    <div class="lado-credito">{cre_html}</div>
                                </div>
                                <div class="conta-rodape" style="color: {cor_saldo};">
                                    {txt_saldo}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
