import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA (EXECUTIVE STYLE) ---
st.set_page_config(page_title="Nexus Executive V5", layout="wide", page_icon="💎")

# Estils CSS per a un look Premium
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    div[data-testid="stMetric"] {
        background-color: #1F2937;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #6366F1;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label { color: #E5E7EB !important; font-size: 0.9rem; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #F3F4F6 !important; font-weight: bold; }
    h1, h2, h3 { color: #F9FAFB; font-family: 'Helvetica Neue', sans-serif; }
    .big-font { font-size:20px !important; color: #6366F1; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("💎 Nexus Executive: Quadre de Comandament")
st.markdown("**CEO Dashboard:** Visió estratègica i control financer total.")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Connexió de Dades")
url_master = st.sidebar.text_input("URL Master Excel", help="Enganxi l'enllaç del full Nexus-iigualada")

if st.sidebar.button("🔄 Refrescar Sistema"):
    st.cache_data.clear()

# --- FUNCIONS AUXILIARS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def netejar_numero(val):
    """Neteja intel·ligent de decimals (Versió V4 provada)"""
    try:
        if isinstance(val, (int, float)): return float(val)
        if pd.isna(val) or str(val).strip() == '': return 0.0
        s = str(val).strip().replace('€', '')
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

@st.cache_data
def convert_df(df):
    """Converteix el DataFrame a CSV per descarregar"""
    return df.to_csv(index=False).encode('utf-8')

# --- MOTOR PRINCIPAL ---
if url_master:
    try:
        # 1. CARREGAR DADES MESTRES
        df_config = conn.read(spreadsheet=url_master, worksheet=0)
        df_config.columns = df_config.columns.str.strip()
        
        # Neteja numèrica Config
        for col in ['Preu_Alumne', 'Num_Alumnes', 'Cost_Material_Fix', 'Preu_Hora_Monitor']:
            if col in df_config.columns:
                df_config[col] = df_config[col].apply(netejar_numero)
        
        df_config['Ingressos_Previstos'] = df_config['Preu_Alumne'] * df_config['Num_Alumnes']
        df_config['Activitat_Join'] = df_config['Activitat'].astype(str).str.strip().str.upper()

        # 2. CARREGAR REGISTRE HISTÒRIC
        df_registre = conn.read(spreadsheet=url_master, worksheet=1)
        df_registre.columns = df_registre.columns.str.strip()
        
        if 'Hores_Fetes' in df_registre.columns:
            df_registre['Hores_Fetes'] = df_registre['Hores_Fetes'].apply(netejar_numero)
        
        df_registre['Data_DT'] = pd.to_datetime(df_registre['Data'], dayfirst=True, errors='coerce')
        df_registre['Mes_Any'] = df_registre['Data_DT'].dt.strftime('%Y-%m')
        
        # Preparar dades per al JOIN
        df_registre['Activitat_Join'] = df_registre['Activitat'].astype(str).str.strip().str.upper()
        
        # ---------------------------------------------------------
        # A. CÀLCUL HISTÒRIC COMPLET (Per al gràfic final)
        # ---------------------------------------------------------
        # Unim tot el registre amb la configuració per tenir dades de tots els mesos
        df_full_history = pd.merge(df_registre, df_config, on='Activitat_Join', how='left', suffixes=('_reg', '_cfg'))
        
        # Càlculs fila a fila per a l'històric
        df_full_history['Cost_Nomina'] = df_full_history['Hores_Fetes'] * df_full_history['Preu_Hora_Monitor']
        # Nota: El cost material és fix mensual, aquí assumim que s'aplica si hi ha activitat
        df_full_history['Cost_Material'] = df_full_history['Cost_Material_Fix'] 
        df_full_history['Despeses'] = df_full_history['Cost_Nomina'] + df_full_history['Cost_Material']
        df_full_history['Marge'] = df_full_history['Ingressos_Previstos'] - df_full_history['Despeses']
        
        # Agrupem per MES per fer el gràfic evolutiu
        df_evo = df_full_history.groupby('Mes_Any')[['Ingressos_Previstos', 'Despeses', 'Marge']].sum().reset_index()

        # ---------------------------------------------------------
        # B. DASHBOARD DEL MES SELECCIONAT
        # ---------------------------------------------------------
        mesos_disponibles = df_registre['Mes_Any'].dropna().unique()
        
        if len(mesos_disponibles) > 0:
            st.divider()
            col_sel, col_blank = st.columns([1, 3])
            with col_sel:
                mes_seleccionat = st.selectbox("📅 Analitzar Mes:", sorted(mesos_disponibles, reverse=True))
            
            # FILTRAR MES ACTUAL
            df_reg_mes = df_registre[df_registre['Mes_Any'] == mes_seleccionat].copy()
            df_hores_agrupades = df_reg_mes.groupby('Activitat_Join')['Hores_Fetes'].sum().reset_index()
            
            # JOIN FINAL MES ACTUAL
            df_final = pd.merge(df_config, df_hores_agrupades, on='Activitat_Join', how='left')
            df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
            
            # CÀLCULS FINALS
            df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
            df_final['Despeses_Totals'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
            df_final['Marge_Real'] = df_final['Ingressos_Previstos'] - df_final['Despeses_Totals']
            
            # Càlcul de rendibilitat % (evitant dividir per zero)
            df_final['Rendibilitat_Percent'] = df_final.apply(
                lambda x: (x['Marge_Real'] / x['Ingressos_Previstos'] * 100) if x['Ingressos_Previstos'] > 0 else 0, axis=1
            )

            # --- KPIS PRINCIPALS ---
            total_ing = df_final['Ingressos_Previstos'].sum()
            total_desp = df_final['Despeses_Totals'].sum()
            total_benefici = df_final['Marge_Real'].sum()
            marge_mig_percent = (total_benefici / total_ing * 100) if total_ing > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Ingressos", f"{total_ing:,.2f} €", delta="Mensual")
            k2.metric("Despeses Totals", f"{total_desp:,.2f} €", delta="-Costos")
            k3.metric("BENEFICI NET", f"{total_benefici:,.2f} €", delta="Resultat")
            k4.metric("Marge Comercial %", f"{marge_mig_percent:.1f} %", delta="Eficiència")

            # --- GRÀFICS SUPERIORS ---
            g1, g2 = st.columns([2, 1])
            
            with g1:
                st.subheader(f"📊 Rendibilitat per Categoria ({mes_seleccionat})")
                if 'Categoria' in df_final.columns:
                    df_cat = df_final.groupby('Categoria')[['Marge_Real', 'Ingressos_Previstos']].sum().reset_index()
                    chart_cat = alt.Chart(df_cat).mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(
                        x=alt.X('Categoria', sort='-y', title=None),
                        y=alt.Y('Marge_Real', title='Benefici Net (€)'),
                        color=alt.condition(
                            alt.datum.Marge_Real > 0, alt.value("#10B981"), alt.value("#EF4444")
                        ),
                        tooltip=['Categoria', 'Marge_Real', 'Ingressos_Previstos']
                    ).properties(height=350)
                    st.altair_chart(chart_cat, use_container_width=True)

            with g2:
                st.subheader("🏆 Top 5 Activitats")
                # Ordenem per benefici i agafem les 5 primeres
                top_5 = df_final.sort_values(by='Marge_Real', ascending=False).head(5)
                # Creem una mini taula visual
                st.dataframe(
                    top_5[['Activitat', 'Marge_Real']], 
                    column_config={
                        "Activitat": "Activitat Estrella",
                        "Marge_Real": st.column_config.NumberColumn("Benefici", format="%.2f €")
                    },
                    hide_index=True,
                    use_container_width=True
                )

            # --- TAULA DETALLADA I DESCÀRREGA ---
            with st.expander("📂 Veure Informe Detallat i Descarregar"):
                # Botó de descàrrega
                csv = convert_df(df_final)
                st.download_button(
                    label="📥 Descarregar Informe (CSV Excel)",
                    data=csv,
                    file_name=f'Informe_Nexus_{mes_seleccionat}.csv',
                    mime='text/csv',
                )
                
                # Taula visual
                cols_show = ['Categoria', 'Activitat', 'Ingressos_Previstos', 'Hores_Fetes', 'Cost_Nomina', 'Marge_Real', 'Rendibilitat_Percent']
                st.dataframe(df_final[cols_show].style.format({
                    'Ingressos_Previstos': "{:.2f} €",
                    'Hores_Fetes': "{:.1f} h",
                    'Cost_Nomina': "{:.2f} €",
                    'Marge_Real': "{:.2f} €",
                    'Rendibilitat_Percent': "{:.1f} %"
                }).background_gradient(subset=['Marge_Real'], cmap="RdYlGn", vmin=-100, vmax=500))

            # ---------------------------------------------------------
            # C. SOTERRANI: EVOLUCIÓ HISTÒRICA (A baix de tot)
            # ---------------------------------------------------------
            st.markdown("---")
            st.subheader("📈 Evolució Històrica del Negoci")
            st.caption("Tendència acumulada de tots els mesos registrats")
            
            chart_evo = alt.Chart(df_evo).mark_line(point=True, strokeWidth=4).encode(
                x=alt.X('Mes_Any', title='Mes'),
                y=alt.Y('Marge', title='Benefici (€)'),
                color=alt.value("#6366F1"),
                tooltip=['Mes_Any', 'Ingressos_Previstos', 'Marge']
            ).properties(height=300)
            
            # Afegim una àrea ombrejada sota la línia per fer-ho més maco
            chart_area = chart_evo.mark_area(opacity=0.3).encode(
                color=alt.value("#6366F1")
            )
            
            st.altair_chart(chart_area + chart_evo, use_container_width=True)

        else:
            st.warning("⚠️ No s'han trobat dades temporals vàlides. Revisi el Registre.")

    except Exception as e:
        st.error(f"Error del Sistema: {e}")
        st.info("Verifiqui la connexió amb el Google Sheet.")

else:
    st.info("👈 Connecti el cervell (Excel Master) per arrencar Nexus Executive.")