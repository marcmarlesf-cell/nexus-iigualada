import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Marc Marlés Control", layout="wide", page_icon="🎓")

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
    
    /* Briefing Box */
    .briefing-box {
        background-color: #1F2937;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #8B5CF6;
        margin-bottom: 25px;
    }
    .briefing-title { font-weight: bold; color: #E5E7EB; font-size: 1.1rem; margin-bottom: 5px; }
    .briefing-text { color: #D1D5DB; font-size: 1rem; }
    
    /* Filtres */
    div.row-widget.stRadio > div { flex-direction: row; align-items: stretch; }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] {
        background-color: #1F2937;
        padding: 10px 20px;
        border-radius: 8px;
        border: 1px solid #374151;
        margin-right: 10px;
    }
    
    /* Títols */
    h1 { color: #F9FAFB; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# --- CAPÇALERA ---
st.title("🎓 Marc Marlés - Extraescolars")

# --- BARRA LATERAL ---
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

def get_icon(categoria):
    """Assigna icones segons la categoria per fer-ho visual"""
    cat = str(categoria).upper().strip()
    if "ESPORTS" in cat: return "⚽"
    if "IDIOMES" in cat: return "🇬🇧"
    if "LUDIC" in cat: return "🎨"
    if "TECNOLOGIC" in cat: return "🤖"
    if "ARTISTIC" in cat: return "🎭"
    return "📝"

if url_master:
    try:
        # 1. CARREGAR CONFIGURACIÓ
        df_config = conn.read(spreadsheet=url_master, worksheet=0)
        df_config.columns = df_config.columns.str.strip()
        
        # Neteja de columnes
        cols_num = ['Preu_Alumne', 'Num_Alumnes', 'Cost_Material_Fix', 'Preu_Hora_Monitor']
        for col in cols_num:
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
            
            # --- ZONA DE CONTROL ---
            st.divider()
            col_ctrl_1, col_ctrl_2 = st.columns([1, 2])
            with col_ctrl_1:
                mes = st.selectbox("📅 Període:", mesos_ordenats)
            with col_ctrl_2:
                cat_filter = st.radio("🔍 Departament:", ["TOTS", "ESPORTS", "IDIOMES", "LUDIC"], horizontal=True)

            # --- CÀLCULS MOTOR ---
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

            # --- BRIEFING INTELLIGENT ---
            if not df_view.empty:
                top_act = df_view.loc[df_view['Marge_Real'].idxmax()]
                total_ben_view = df_view['Marge_Real'].sum()
                total_alumnes = df_view['Num_Alumnes'].sum()
                
                # Ràtio d'Or: Benefici per Alumne
                ratio_alumne = (total_ben_view / total_alumnes) if total_alumnes > 0 else 0
                
                st.markdown(f"""
                <div class="briefing-box">
                    <div class="briefing-title">🤖 Informe Director: {cat_filter} ({mes})</div>
                    <div class="briefing-text">
                        Gestionant <b>{total_alumnes:.0f} alumnes</b>, el benefici és de <b>{total_ben_view:,.0f} €</b>.<br>
                        Això suposa un rendiment net de <span style="color:#10B981; font-weight:bold">{ratio_alumne:.1f} € per alumne</span>.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # --- NOUS KPIS (4 Columnes Estratègiques) ---
            tot_ing = df_view['Ingressos_Previstos'].sum()
            tot_ben = df_view['Marge_Real'].sum()
            tot_students = df_view['Num_Alumnes'].sum()
            marge_pc = (tot_ben / tot_ing * 100) if tot_ing > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("👥 Alumnes Inscrits", f"{tot_students:.0f}")
            k2.metric("Ingressos Totals", f"{tot_ing:,.0f} €")
            k3.metric("Marge Comercial", f"{marge_pc:.1f} %")
            k4.metric("BENEFICI NET", f"{tot_ben:,.0f} €")

            st.markdown("---")
            
            # --- GRÀFICS ---
            if not df_view.empty:
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.caption("Rendibilitat Comparada")
                    c1 = alt.Chart(df_view).mark_bar(cornerRadius=5).encode(
                        x=alt.X('Activitat', sort='-y', title=None),
                        y=alt.Y('Marge_Real', title=None),
                        color=alt.condition(alt.datum.Marge_Real > 0, alt.value("#10B981"), alt.value("#EF4444")),
                        tooltip=['Activitat', 'Marge_Real', 'Num_Alumnes']
                    ).properties(height=250)
                    st.altair_chart(c1, use_container_width=True)

                with col_g2:
                    st.caption(f"Distribució d'Alumnes ({tot_students} totals)")
                    base = alt.Chart(df_view).encode(theta=alt.Theta("Num_Alumnes", stack=True))
                    pie = base.mark_arc(innerRadius=55).encode(
                        color=alt.Color("Activitat", legend=None),
                        order=alt.Order("Num_Alumnes", sort="descending"),
                        tooltip=["Activitat", "Num_Alumnes"]
                    ).properties(height=250)
                    st.altair_chart(pie, use_container_width=True)

                # --- TARGETES AMB ICONES ---
                st.subheader(f"📱 Detall: {cat_filter}")
                df_sorted = df_view.sort_values(by='Marge_Real', ascending=False)
                
                for index, row in df_sorted.iterrows():
                    ben = row['Marge_Real']
                    nom = row['Activitat']
                    ing = row['Ingressos_Previstos']
                    icon = get_icon(row['Categoria']) # Icona automàtica
                    alumnes = row['Num_Alumnes']
                    
                    with st.expander(f"{icon} {nom}  |  {ben:,.0f} €"):
                        c_1, c_2, c_3, c_4 = st.columns(4)
                        c_1.metric("Alumnes", f"{alumnes:.0f}")
                        c_2.metric("Facturació", f"{ing:.0f} €")
                        c_3.metric("Hores", f"{row['Hores_Fetes']:.1f} h")
                        # Semàfor de rendibilitat
                        if ben > 0:
                            c_4.markdown(f"<span style='color:#10B981; font-weight:bold; font-size:1.5rem'>+{ben:.0f} €</span>", unsafe_allow_html=True)
                        else:
                            c_4.markdown(f"<span style='color:#EF4444; font-weight:bold; font-size:1.5rem'>{ben:.0f} €</span>", unsafe_allow_html=True)
                        
                        if ing > 0:
                            st.caption("Barra d'eficiència:")
                            st.progress(max(0, min(1.0, ben / ing)))
            else:
                st.info(f"No hi ha activitats per a la categoria {cat_filter}.")
                
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👈 Connecti el Master Excel.")