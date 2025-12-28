import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Nexus Visual V6", layout="wide", page_icon="💎")

# Estils Premium
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    div[data-testid="stMetric"] {
        background-color: #1F2937;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #10B981;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label { color: #9CA3AF !important; font-size: 0.9rem; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #F3F4F6 !important; font-weight: bold; }
    h1, h2, h3 { color: #F9FAFB; font-family: 'Helvetica Neue', sans-serif; }
</style>
""", unsafe_allow_html=True)

st.title("💎 Nexus Executive: Visió 360º")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Connexió")
url_master = st.sidebar.text_input("URL Master Excel", help="Enllaç Google Sheet")
if st.sidebar.button("🔄 Refrescar"):
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

        # Càlcul Històric (per al gràfic final)
        df_hist = pd.merge(df_registre, df_config, on='Activitat_Join', how='left')
        df_hist['Cost_Total'] = (df_hist['Hores_Fetes'] * df_hist['Preu_Hora_Monitor']) + df_hist['Cost_Material_Fix']
        df_hist['Marge'] = df_hist['Ingressos_Previstos'] - df_hist['Cost_Total']
        df_evo = df_hist.groupby('Mes_Any')[['Ingressos_Previstos', 'Marge']].sum().reset_index()

        # DASHBOARD MES ACTUAL
        mesos = df_registre['Mes_Any'].dropna().unique()
        if len(mesos) > 0:
            st.divider()
            col_sel, _ = st.columns([1, 3])
            with col_sel:
                mes = st.selectbox("📅 Mes a Analitzar:", sorted(mesos, reverse=True))
            
            # Càlculs Mes
            df_reg_mes = df_registre[df_registre['Mes_Any'] == mes].copy()
            df_hores = df_reg_mes.groupby('Activitat_Join')['Hores_Fetes'].sum().reset_index()
            
            df_final = pd.merge(df_config, df_hores, on='Activitat_Join', how='left')
            df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
            
            df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
            df_final['Despeses'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
            df_final['Marge_Real'] = df_final['Ingressos_Previstos'] - df_final['Despeses']
            
            # --- KPIS ---
            tot_ing = df_final['Ingressos_Previstos'].sum()
            tot_ben = df_final['Marge_Real'].sum()
            marge_pc = (tot_ben / tot_ing * 100) if tot_ing > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Ingressos", f"{tot_ing:,.2f} €")
            k2.metric("Despeses", f"{df_final['Despeses'].sum():,.2f} €")
            k3.metric("BENEFICI NET", f"{tot_ben:,.2f} €")
            k4.metric("Marge Comercial", f"{marge_pc:.1f} %")

            # --- VISUALS NOUS ---
            st.subheader("📊 Anàlisi Visual")
            col_g1, col_g2 = st.columns(2)
            
            df_cat = df_final.groupby('Categoria')[['Ingressos_Previstos', 'Marge_Real']].sum().reset_index()

            with col_g1:
                st.markdown("**Rendibilitat per Categoria** (Barres)")
                c1 = alt.Chart(df_cat).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Categoria', sort='-y', title=None),
                    y=alt.Y('Marge_Real', title='Benefici €'),
                    color=alt.condition(alt.datum.Marge_Real > 0, alt.value("#10B981"), alt.value("#EF4444")),
                    tooltip=['Categoria', 'Marge_Real']
                ).properties(height=300)
                st.altair_chart(c1, use_container_width=True)

            with col_g2:
                st.markdown("**Origen dels Ingressos** (Donut)")
                c2 = alt.Chart(df_cat).mark_arc(innerRadius=60).encode(
                    theta=alt.Theta(field="Ingressos_Previstos", type="quantitative"),
                    color=alt.Color(field="Categoria", type="nominal", legend=alt.Legend(title="Categoria")),
                    tooltip=['Categoria', 'Ingressos_Previstos']
                ).properties(height=300)
                st.altair_chart(c2, use_container_width=True)

            # --- TAULA HEATMAP (SENSE BOTÓ) ---
            st.markdown("---")
            st.subheader("📋 Detall Operatiu (Mapa de Calor)")
            
            cols = ['Categoria', 'Activitat', 'Ingressos_Previstos', 'Hores_Fetes', 'Marge_Real']
            # Apliquem el gradient de color (Necessita matplotlib, que hem afegit al requirements)
            st.dataframe(
                df_final[cols].style
                .format({'Ingressos_Previstos': "{:.0f} €", 'Hores_Fetes': "{:.1f} h", 'Marge_Real': "{:.0f} €"})
                .background_gradient(subset=['Marge_Real'], cmap="RdYlGn", vmin=0)
            )

            # --- HISTÒRIC ---
            st.markdown("---")
            st.caption("📈 Tendència Històrica")
            c_evo = alt.Chart(df_evo).mark_area(opacity=0.3, color='#6366F1').encode(
                x='Mes_Any', y='Marge'
            ) + alt.Chart(df_evo).mark_line(color='#6366F1').encode(
                x='Mes_Any', y='Marge', tooltip=['Mes_Any', 'Marge']
            )
            st.altair_chart(c_evo, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👈 Connecti el Master Excel.")