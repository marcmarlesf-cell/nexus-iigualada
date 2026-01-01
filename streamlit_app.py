import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Marc Marlés Control", layout="wide", page_icon="🎓")

# --- ESTILS CSS PREMIUM ---
st.markdown("""
<style>
    /* Fons fosc net */
    [data-testid="stAppViewContainer"] {
        background-color: #0E1117;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }

    /* KPI Cards */
    div[data-testid="stMetric"] {
        background-color: #1F2937; 
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Textos principals en blanc */
    h1, h2, h3, .briefing-title, .briefing-text, p, label {
        color: #E5E7EB !important;
    }
    
    /* Pestanyes (Tabs) personalitzades */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1F2937;
        border-radius: 4px;
        color: white;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #8B5CF6 !important;
        color: white !important;
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
st.title("🎓 Marc Marlés - Coordinació")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Dades")
url_master = st.sidebar.text_input("URL Master Excel", help="Enllaç Google Sheet")
if st.sidebar.button("🔄 Refrescar", use_container_width=True):
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
        # 1. CARREGAR DADES
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
            
            # --- CONTROLS ---
            st.divider()
            col_ctrl_1, col_ctrl_2 = st.columns([1, 3])
            with col_ctrl_1:
                mes = st.selectbox("📅 Període:", mesos_ordenats)
            with col_ctrl_2:
                filtre_cats = ["TOTS"] + list(df_config['Categoria'].unique())
                cat_filter = st.selectbox("🔍 Filtrar Departament:", filtre_cats)

            # --- CÀLCULS ---
            df_reg_mes = df_registre[df_registre['Mes_Any'] == mes].copy()
            df_hores = df_reg_mes.groupby('Activitat_Join')['Hores_Fetes'].sum().reset_index()
            
            df_final = pd.merge(df_config, df_hores, on='Activitat_Join', how='left')
            df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
            
            df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
            df_final['Despeses'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
            df_final['Marge_Real'] = df_final['Ingressos_Previstos'] - df_final['Despeses']
            
            # FILTRATGE
            df_view = df_final.copy()
            if cat_filter != "TOTS":
                df_view = df_view[df_view['Categoria'] == cat_filter]

            # --- KPIS ---
            tot_ing = df_view['Ingressos_Previstos'].sum()
            tot_ben = df_view['Marge_Real'].sum()
            tot_students = df_view['Num_Alumnes'].sum()
            marge_pc = (tot_ben / tot_ing * 100) if tot_ing > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("👥 Alumnes", f"{tot_students:.0f}")
            k2.metric("Facturació", f"{tot_ing:,.0f} €")
            k3.metric("Marge %", f"{marge_pc:.1f} %")
            k4.metric("Benefici Net", f"{tot_ben:,.0f} €", delta=f"{tot_ben:,.0f} €")

            st.markdown("---")
            
            # --- SISTEMA DE PESTANYES VISUALS ---
            tab1, tab2 = st.tabs(["🗺️ Mapa Visual (Treemap)", "📊 Rànquing Comparatiu"])
            
            df_chart = df_view if cat_filter != "TOTS" else df_final

            with tab1:
                st.caption("La mida dels quadres indica el nombre d'alumnes. El color indica el departament.")
                if not df_chart.empty:
                    # TREEMAP: Molt millor per a moltes dades que el Sunburst
                    fig_tree = px.treemap(
                        df_chart, 
                        path=['Categoria', 'Activitat'], 
                        values='Num_Alumnes',
                        color='Categoria',
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        # Aquesta línia neteja el TOOLTIP (treu id, parent, labels...)
                        custom_data=['Marge_Real', 'Ingressos_Previstos']
                    )
                    
                    # Disseny del tooltip net i professional
                    fig_tree.update_traces(
                        hovertemplate="<b>%{label}</b><br>👥 Alumnes: %{value}<br>💰 Benefici: %{customdata[0]:,.0f} €<extra></extra>",
                        textinfo="label+value"
                    )

                    fig_tree.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', size=15),
                        margin=dict(t=0, l=0, r=0, b=0),
                        height=550
                    )
                    st.plotly_chart(fig_tree, use_container_width=True)

            with tab2:
                st.caption("Rànquing de rendibilitat per activitat.")
                if not df_chart.empty:
                    # BAR CHART INTERACTIU
                    df_sorted_bar = df_chart.sort_values('Marge_Real', ascending=True) # Per veure els millors a dalt
                    fig_bar = px.bar(
                        df_sorted_bar,
                        x='Marge_Real',
                        y='Activitat',
                        orientation='h',
                        text='Marge_Real',
                        color='Marge_Real',
                        color_continuous_scale=['#EF4444', '#10B981'], # Vermell a Verd
                        custom_data=['Num_Alumnes']
                    )
                    
                    # Neteja visual
                    fig_bar.update_traces(
                        texttemplate='%{text:.0f} €', 
                        textposition='outside',
                        hovertemplate="<b>%{y}</b><br>Benefici: %{x:.0f} €<br>Alumnes: %{customdata[0]}<extra></extra>"
                    )
                    
                    fig_bar.update_layout(
                        xaxis_title="Benefici (€)",
                        yaxis_title=None,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        showlegend=False,
                        height=max(400, len(df_chart)*30) # Alçada automàtica segons num activitats
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

            # --- LLISTAT DETALLAT ---
            st.markdown("### 📋 Detall Fitxes")
            
            if not df_view.empty:
                df_sorted = df_view.sort_values(by='Marge_Real', ascending=False)
                
                for index, row in df_sorted.iterrows():
                    ben = row['Marge_Real']
                    nom = row['Activitat']
                    icon = get_icon(row['Categoria'])
                    ing = row['Ingressos_Previstos']
                    
                    # Targeta
                    with st.expander(f"{icon} {nom}  |  Benefici: {ben:,.0f} €"):
                        col_a, col_b = st.columns([1,3])
                        with col_a:
                            st.metric("Alumnes", f"{row['Num_Alumnes']:.0f}")
                        with col_b:
                            if ing > 0:
                                eficiencia = max(0, min(1.0, ben / ing))
                                st.progress(eficiencia)
                                st.caption(f"Marge: {eficiencia*100:.1f}%")
                            
                            st.write(f"**Cost Nómina:** {row['Cost_Nomina']:.2f}€ | **Material:** {row['Cost_Material_Fix']:.2f}€")
            else:
                st.warning("No hi ha dades per mostrar.")

    except Exception as e:
        st.error(f"⚠️ Error de càrrega: {e}")
else:
    st.info("👈 Introdueixi la URL del full de càlcul per començar.")