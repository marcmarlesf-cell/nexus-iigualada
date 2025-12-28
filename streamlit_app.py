import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Marc Marlés Control", layout="wide", page_icon="👔")

# Estils CSS Premium
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    
    /* KPI Cards */
    div[data-testid="stMetric"] {
        background-color: #111827; 
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }
    
    /* El Briefing (Caixa lila) */
    .briefing-box {
        background-color: #1F2937;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #8B5CF6;
        margin-bottom: 25px;
    }
    .briefing-title { font-weight: bold; color: #E5E7EB; font-size: 1.1rem; margin-bottom: 5px; }
    .briefing-text { color: #D1D5DB; font-size: 1rem; }
    
    /* Estil personalitzat per als botons de filtre (Radio Buttons) */
    div.row-widget.stRadio > div { flex-direction: row; align-items: stretch; }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] {
        background-color: #1F2937;
        padding: 10px 20px;
        border-radius: 8px;
        border: 1px solid #374151;
        margin-right: 10px;
        transition: all 0.2s;
    }
    /* Targetes */
    .activity-card { border-radius: 10px; margin-bottom: 10px; border: 1px solid #374151; }
    
    h1 { color: #F9FAFB; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# --- CAPÇALERA PERSONALITZADA ---
st.title("👔 Marc Marlés - Extraescolars")

# --- BARRA LATERAL (Només tècnica) ---
st.sidebar.header("⚙️ Connexió")
url_master = st.sidebar.text_input("URL Master Excel", help="Enllaç Google Sheet")
if st.sidebar.button("🔄 Refrescar Dades"):
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

if url_master:
    try:
        # 1. CARREGAR DADES
        df_config = conn.read(spreadsheet=url_master, worksheet=0)
        df_config.columns = df_config.columns.str.strip()
        for col in ['Preu_Alumne', 'Num_Alumnes', 'Cost_Material_Fix', 'Preu_Hora_Monitor']:
            if col in df_config.columns: df_config[col] = df_config[col].apply(netejar_numero)
        
        df_config['Ingressos_Previstos'] = df_config['Preu_Alumne'] * df_config['Num_Alumnes']
        df_config['Activitat_Join'] = df_config['Activitat'].astype(str).str.strip().str.upper()

        # 2. CARREGAR REGISTRE
        df_registre = conn.read(spreadsheet=url_master, worksheet=1)
        df_registre.columns = df_registre.columns.str.strip()
        if 'Hores_Fetes' in df_registre.columns: df_registre['Hores_Fetes'] = df_registre['Hores_Fetes'].apply(netejar_numero)
        
        df_registre['Data_DT'] = pd.to_datetime(df_registre['Data'], dayfirst=True, errors='coerce')
        df_registre['Mes_Any'] = df_registre['Data_DT'].dt.strftime('%Y-%m')
        df_registre['Activitat_Join'] = df_registre['Activitat'].astype(str).str.strip().str.upper()

        mesos = df_registre['Mes_Any'].dropna().unique()
        
        if len(mesos) > 0:
            mesos_ordenats = sorted(mesos, reverse=True)
            
            # --- ZONA DE CONTROL (FILTRES VISUALS) ---
            st.divider()
            
            # Columnes per alinear Mes (esquerra) i Filtre (dreta)
            col_ctrl_1, col_ctrl_2 = st.columns([1, 2])
            
            with col_ctrl_1:
                mes = st.selectbox("📅 Període:", mesos_ordenats)
            
            with col_ctrl_2:
                # NOU FILTRE VISUAL (Estil botons horitzontals)
                cat_filter = st.radio(
                    "🔍 Departament:",
                    ["TOTS", "ESPORTS", "IDIOMES", "LUDIC"],
                    horizontal=True,
                    label_visibility="visible"
                )

            # --- CÀLCULS ---
            df_reg_mes = df_registre[df_registre['Mes_Any'] == mes].copy()
            df_hores = df_reg_mes.groupby('Activitat_Join')['Hores_Fetes'].sum().reset_index()
            
            df_final = pd.merge(df_config, df_hores, on='Activitat_Join', how='left')
            df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
            
            df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
            df_final['Despeses'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
            df_final['Marge_Real'] = df_final['Ingressos_Previstos'] - df_final['Despeses']
            
            # Filtrar segons la selecció visual
            df_view = df_final.copy()
            if cat_filter != "TOTS":
                df_view = df_view[df_view['Categoria'] == cat_filter]

            # --- BRIEFING (NOMÉS SI HI HA DADES) ---
            if not df_view.empty:
                top_act = df_view.loc[df_view['Marge_Real'].idxmax()]
                total_ben_view = df_view['Marge_Real'].sum()
                
                st.markdown(f"""
                <div class="briefing-box">
                    <div class="briefing-title">🤖 Resum Executiu: {cat_filter} ({mes})</div>
                    <div class="briefing-text">
                        En aquest període i categoria, el benefici és de <b>{total_ben_view:,.0f} €</b>.
                        L'activitat més destacada és <span style="color:#10B981; font-weight:bold">{top_act['Activitat']}</span>.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # --- KPI GLOBAL (DEL FILTRE SELECCIONAT) ---
            tot_ing = df_view['Ingressos_Previstos'].sum()
            tot_des = df_view['Despeses'].sum()
            tot_ben = df_view['Marge_Real'].sum()
            marge_pc = (tot_ben / tot_ing * 100) if tot_ing > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Ingressos", f"{tot_ing:,.0f} €")
            k2.metric("Despeses", f"{tot_des:,.0f} €")
            k3.metric("BENEFICI", f"{tot_ben:,.0f} €")
            k4.metric("Marge %", f"{marge_pc:.1f} %")

            st.markdown("---")
            
            # --- VISUALITZACIÓ ---
            if not df_view.empty:
                col_g1, col_g2 = st.columns(2)
                df_cat_view = df_view.groupby('Categoria')[['Ingressos_Previstos', 'Marge_Real']].sum().reset_index()

                with col_g1:
                    st.caption("Rendibilitat Comparada")
                    c1 = alt.Chart(df_view).mark_bar(cornerRadius=5).encode(
                        x=alt.X('Activitat', sort='-y', title=None),
                        y=alt.Y('Marge_Real', title=None),
                        color=alt.condition(alt.datum.Marge_Real > 0, alt.value("#10B981"), alt.value("#EF4444")),
                        tooltip=['Activitat', 'Marge_Real']
                    ).properties(height=250)
                    st.altair_chart(c1, use_container_width=True)

                with col_g2:
                    st.caption("Pes Facturació")
                    c2 = alt.Chart(df_view).mark_arc(innerRadius=55).encode(
                        theta=alt.Theta(field="Ingressos_Previstos", type="quantitative"),
                        color=alt.Color(field="Activitat", legend=None),
                        tooltip=['Activitat', 'Ingressos_Previstos']
                    ).properties(height=250)
                    st.altair_chart(c2, use