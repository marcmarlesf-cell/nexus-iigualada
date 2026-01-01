import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Marc Marlés Control", layout="wide", page_icon="🎓")

# --- ESTILS CSS PREMIUM & FIX BUGS ---
st.markdown("""
<style>
    /* 1. Fons fosc net i professional */
    [data-testid="stAppViewContainer"] {
        background-color: #0E1117;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }

    /* 2. SOLUCIÓ ERROR TEXT INPUT (Amagar instruccions 'Press Enter') */
    [data-testid="InputInstructions"] {
        display: none !important;
    }
    
    /* Millorar l'input de text per evitar superposicions */
    div[data-baseweb="input"] {
        background-color: #1F2937 !important;
        border: 1px solid #374151;
        color: white;
    }

    /* 3. KPI Cards amb efecte elevat */
    div[data-testid="stMetric"] {
        background-color: #1F2937; 
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* 4. Tipografia global neta */
    h1, h2, h3, .briefing-title, .briefing-text, p, label {
        color: #E5E7EB !important;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* 5. Pestanyes (Tabs) Estilitzades */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #111827;
        border-radius: 6px;
        color: #9CA3AF;
        padding: 8px 16px;
        border: 1px solid #374151;
    }
    .stTabs [aria-selected="true"] {
        background-color: #7C3AED !important; /* Lila Institució */
        color: white !important;
        border-color: #7C3AED;
    }

    /* Expander arreglat */
    .streamlit-expanderHeader {
        background-color: #1F2937 !important;
        color: white !important;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- CAPÇALERA ---
col_head_1, col_head_2 = st.columns([3,1])
with col_head_1:
    st.title("🎓 Marc Marlés - Estratègia")
with col_head_2:
    st.caption("v12.0 Strategic")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuració")
url_master = st.sidebar.text_input("URL Master Excel", help="Enganxi l'enllaç aquí")

# Botó d'acció manual per evitar refrescos constants
if st.sidebar.button("🔄 Actualitzar Dades", use_container_width=True):
    st.cache_data.clear()

conn = st.connection("gsheets", type=GSheetsConnection)

def netejar_numero(val):
    try:
        if isinstance(val, (int, float)): return float(val)
        if pd.isna(val) or str(val).strip() == '': return 0.0
        s = str(val).strip().replace('€', '')
        if ',' in s: s = s.replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

def get_icon(categoria):
    cat = str(categoria).upper().strip()
    if "ESPORTS" in cat: return "⚽"
    if "IDIOMES" in cat: return "🇬🇧"
    if "LUDIC" in cat: return "🎨"
    if "TECNOLOGIC" in cat: return "🤖"
    if "ARTISTIC" in cat: return "🎭"
    return "📝"

if url_master:
    try:
        # --- CÀRREGA DE DADES ---
        df_config = conn.read(spreadsheet=url_master, worksheet=0)
        df_config.columns = df_config.columns.str.strip()
        
        cols_num = ['Preu_Alumne', 'Num_Alumnes', 'Cost_Material_Fix', 'Preu_Hora_Monitor']
        for col in cols_num:
            if col in df_config.columns: df_config[col] = df_config[col].apply(netejar_numero)
        
        df_config['Ingressos_Previstos'] = df_config['Preu_Alumne'] * df_config['Num_Alumnes']
        df_config['Activitat_Join'] = df_config['Activitat'].astype(str).str.strip().str.upper()

        df_registre = conn.read(spreadsheet=url_master, worksheet=1)
        df_registre.columns = df_registre.columns.str.strip()
        if 'Hores_Fetes' in df_registre.columns: df_registre['Hores_Fetes'] = df_registre['Hores_Fetes'].apply(netejar_numero)
        
        df_registre['Data_DT'] = pd.to_datetime(df_registre['Data'], dayfirst=True, errors='coerce')
        df_registre['Mes_Any'] = df_registre['Data_DT'].dt.strftime('%Y-%m')
        df_registre['Activitat_Join'] = df_registre['Activitat'].astype(str).str.strip().str.upper()

        mesos = df_registre['Mes_Any'].dropna().unique()
        
        if len(mesos) > 0:
            mesos_ordenats = sorted(mesos, reverse=True)
            
            # --- ZONA DE FILTRES ---
            st.divider()
            col_ctrl_1, col_ctrl_2 = st.columns([1, 4])
            with col_ctrl_1:
                mes = st.selectbox("📅 Període:", mesos_ordenats)
            with col_ctrl_2:
                opcions_cat = ["TOTS"] + sorted(list(df_config['Categoria'].unique()))
                cat_filter = st.radio("Departament:", opcions_cat, horizontal=True)

            # --- MOTOR DE CÀLCUL ---
            df_reg_mes = df_registre[df_registre['Mes_Any'] == mes].copy()
            df_hores = df_reg_mes.groupby('Activitat_Join')['Hores_Fetes'].sum().reset_index()
            
            df_final = pd.merge(df_config, df_hores, on='Activitat_Join', how='left')
            df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
            
            df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
            df_final['Despeses'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
            df_final['Marge_Real'] = df_final['Ingressos_Previstos'] - df_final['Despeses']
            
            # FILTRATGE PER VISUALITZACIÓ
            df_view = df_final.copy()
            if cat_filter != "TOTS":
                df_view = df_view[df_view['Categoria'] == cat_filter]

            # --- PANEL KPIS PRINCIPALS ---
            tot_ing = df_view['Ingressos_Previstos'].sum()
            tot_ben = df_view['Marge_Real'].sum()
            tot_students = df_view['Num_Alumnes'].sum()
            marge_pc = (tot_ben / tot_ing * 100) if tot_ing > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("👥 Alumnes", f"{tot_students:.0f}")
            k2.metric("Facturació", f"{tot_ing:,.0f} €")
            k3.metric("Marge Comercial", f"{marge_pc:.1f} %")
            k4.metric("Benefici Net", f"{tot_ben:,.0f} €", delta=f"{tot_ben:,.0f} €")

            st.markdown("---")
            
            # --- ANALÍTICA AVANÇADA (TABS) ---
            tab1, tab2, tab3 = st.tabs(["📊 Rànquing", "🎯 Matriu Estratègica", "📈 Tendència"])
            
            df_chart = df_view if cat_filter != "TOTS" else df_final

            # TAB 1: RÀNQUING (El que li agrada)
            with tab1:
                if not df_chart.empty:
                    df_sorted_bar = df_chart.sort_values('Marge_Real', ascending=True)
                    fig_bar = px.bar(
                        df_sorted_bar,
                        x='Marge_Real',
                        y='Activitat',
                        orientation='h',
                        text='Marge_Real',
                        color='Marge_Real',
                        color_continuous_scale=['#EF4444', '#10B981'],
                        title="Classificació per Benefici Real (€)"
                    )
                    fig_bar.update_traces(texttemplate='%{text:.0f} €', textposition='outside')
                    fig_bar.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        xaxis_title=None,
                        yaxis_title=None,
                        height=max(400, len(df_chart)*30),
                        margin=dict(l=0, r=0, t=30, b=0)
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

            # TAB 2: MATRIU ESTRATÈGICA (Substitut del Mapa Visual)
            with tab2:
                st.info("💡 **Com llegir-ho:** A la dreta activitats amb molts alumnes. A dalt activitats amb molt benefici.")
                if not df_chart.empty:
                    # Scatter Plot: Eix X = Alumnes, Eix Y = Benefici
                    fig_matrix = px.scatter(
                        df_chart,
                        x="Num_Alumnes",
                        y="Marge_Real",
                        color="Categoria",
                        size="Ingressos_Previstos", # La bola és més gran si factura més
                        hover_name="Activitat",
                        text="Activitat",
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    
                    # Línia de "Break-even" (Benefici 0)
                    fig_matrix.add_hline(y=0, line_dash="dash", line_color="white", annotation_text="Llindar Rentabilitat")
                    
                    fig_matrix.update_traces(textposition='top center')
                    fig_matrix.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)', # Grid fosc suau
                        font=dict(color='white'),
                        xaxis=dict(title="Volum d'Alumnes", showgrid=True, gridcolor='#374151'),
                        yaxis=dict(title="Benefici Net (€)", showgrid=True, gridcolor='#374151'),
                        height=500,
                        showlegend=False
                    )
                    st.plotly_chart(fig_matrix, use_container_width=True)

            # TAB 3: TENDÈNCIA (Nou)
            with tab3:
                # Càlcul ràpid d'evolució (agrupat per mesos global)
                try:
                    df_trend = df_registre.groupby('Mes_Any')['Hores_Fetes'].sum().reset_index()
                    if not df_trend.empty:
                        fig_line = px.line(
                            df_trend, x='Mes_Any', y='Hores_Fetes', 
                            markers=True, 
                            title="Evolució d'Hores Realitzades"
                        )
                        fig_line.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'),
                            xaxis_title=None,
                            yaxis_title="Hores Totals",
                            height=400
                        )
                        fig_line.update_traces(line_color='#8B5CF6', line_width=4)
                        st.plotly_chart(fig_line, use_container_width=True)
                    else:
                        st.caption("No hi ha prou dades històriques encara.")
                except:
                    st.caption("Falten dades de dates per mostrar la tendència.")

            # --- FITXES DE DETALL ---
            st.subheader("📋 Detall d'Activitats")
            if not df_view.empty:
                df_sorted = df_view.sort_values(by='Marge_Real', ascending=False)
                for index, row in df_sorted.iterrows():
                    ben = row['Marge_Real']
                    nom = row['Activitat']
                    icon = get_icon(row['Categoria'])
                    ing = row['Ingressos_Previstos']
                    
                    with st.expander(f"{icon} {nom}  |  {ben:,.0f} €", expanded=False):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Alumnes", f"{row['Num_Alumnes']:.0f}")
                        c2.metric("Costos", f"{row['Despeses']:.0f} €")
                        
                        # Semàfor visual
                        color_t = "green" if ben > 0 else "red"
                        c3.markdown(f"**Resultat:** :{color_t}[{ben:,.0f} €]")
                        
                        if ing > 0:
                            st.progress(max(0, min(1.0, ben / ing)))
            
    except Exception as e:
        st.error(f"⚠️ Error crític: {e}")
        st.info("Verifiqui que el full de càlcul tingui les columnes: 'Activitat', 'Preu_Alumne', 'Num_Alumnes', etc.")

else:
    st.info("👈 Introdueixi la URL del full de càlcul per començar.")