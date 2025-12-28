import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Nexus Control V3", layout="wide", page_icon="🔐")

# Estils per veure bé els números en mode fosc
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    div[data-testid="stMetric"] {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #41424C;
    }
    div[data-testid="stMetric"] label { color: #FAFAFA !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #4ADE80 !important; }
    h1, h2, h3 { color: #FAFAFA; font-family: 'Arial', sans-serif; }
</style>
""", unsafe_allow_html=True)

st.title("🔐 Nexus Control: Sistema Centralitzat")
st.markdown("**Dr. Economia:** Llegint estructura MASTER_NEXUS (Configuració + Registre).")

# --- BARRA LATERAL ---
st.sidebar.header("🔗 Connexió Master")
# Posem un valor per defecte buit, però preparat
url_master = st.sidebar.text_input("URL del fitxer 'Nexus-iigualada'", help="Enganxi l'enllaç del Google Sheet aquí")

if st.sidebar.button("🔄 Actualitzar Dades"):
    st.cache_data.clear()

# --- CONNEXIÓ ---
conn = st.connection("gsheets", type=GSheetsConnection)

def netejar_numero(val):
    """Converteix textos amb € o comes a números decimals"""
    try:
        if pd.isna(val) or str(val).strip() == '': return 0.0
        # Primer traiem símbols, després canviem coma per punt
        s = str(val).replace('€','').replace('.','').replace(',','.').strip()
        return float(s)
    except:
        return 0.0

# --- LÒGICA PRINCIPAL ---
if url_master:
    try:
        # 1. LLEGIR CONFIGURACIÓ (Pestanya 1)
        # worksheet=0 és la primera pestanya
        df_config = conn.read(spreadsheet=url_master, worksheet=0)
        
        # Neteja de noms de columnes (treure espais invisibles)
        df_config.columns = df_config.columns.str.strip()
        
        # Assegurar columnes numèriques
        cols_num_config = ['Preu_Alumne', 'Num_Alumnes', 'Cost_Material_Fix', 'Preu_Hora_Monitor']
        for col in cols_num_config:
            if col in df_config.columns:
                df_config[col] = df_config[col].apply(netejar_numero)
        
        # Càlcul d'Ingressos Teòrics (Mensuals)
        df_config['Ingressos_Previstos'] = df_config['Preu_Alumne'] * df_config['Num_Alumnes']
        
        # 2. LLEGIR REGISTRE MENSUAL (Pestanya 2)
        # worksheet=1 és la segona pestanya
        df_registre = conn.read(spreadsheet=url_master, worksheet=1)
        df_registre.columns = df_registre.columns.str.strip()
        
        # Neteja Registre
        if 'Hores_Fetes' in df_registre.columns:
            df_registre['Hores_Fetes'] = df_registre['Hores_Fetes'].apply(netejar_numero)
        
        # Tractament de Dates
        df_registre['Data_DT'] = pd.to_datetime(df_registre['Data'], dayfirst=True, errors='coerce')
        df_registre['Mes_Any'] = df_registre['Data_DT'].dt.strftime('%Y-%m')
        
        # SELECTOR DE MES
        mesos_disponibles = df_registre['Mes_Any'].dropna().unique()
        
        if len(mesos_disponibles) > 0:
            mes_seleccionat = st.selectbox("📅 Seleccioni Mes a Analitzar", sorted(mesos_disponibles, reverse=True))
            
            # FILTRAR PER MES
            df_reg_mes = df_registre[df_registre['Mes_Any'] == mes_seleccionat].copy()
            
            # Agrupar hores per activitat (suma hores si n'hi ha més d'una entrada)
            df_hores_agrupades = df_reg_mes.groupby('Activitat')['Hores_Fetes'].sum().reset_index()
            
            # 3. CREUAMENT DE DADES (La Màgia)
            # Normalitzem noms (MAJÚSCULES i sense espais) per creuar bé
            df_config['Activitat_Join'] = df_config['Activitat'].astype(str).str.strip().str.upper()
            df_hores_agrupades['Activitat_Join'] = df_hores_agrupades['Activitat'].astype(str).str.strip().str.upper()
            
            # Unim: Agafem Totes les activitats de config, i hi afegim les hores si en tenen
            df_final = pd.merge(df_config, df_hores_agrupades, on='Activitat_Join', how='left')
            
            # Si no hi ha hores registrades, posem 0
            df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
            
            # CÀLCULS FINALS
            df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
            df_final['Despeses_Totals'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
            df_final['Marge_Real'] = df_final['Ingressos_Previstos'] - df_final['Despeses_Totals']
            
            # --- DASHBOARD VISUAL ---
            
            st.divider()
            
            # KPIs Globals
            k1, k2, k3, k4 = st.columns(4)
            total_ing = df_final['Ingressos_Previstos'].sum()
            total_nom = df_final['Cost_Nomina'].sum()
            total_mat = df_final['Cost_Material_Fix'].sum()
            total_res = df_final['Marge_Real'].sum()
            
            k1.metric("Ingressos Estimats", f"{total_ing:,.2f} €")
            k2.metric("Cost Nòmines", f"{total_nom:,.2f} €")
            k3.metric("Cost Material", f"{total_mat:,.2f} €")
            k4.metric("BENEFICI NET", f"{total_res:,.2f} €", delta="Bé" if total_res > 0 else "Revisar")
            
            # GRÀFIC PER CATEGORIES (La visió estratègica)
            st.subheader("📊 Rendiment per Categoria")
            
            if 'Categoria' in df_final.columns:
                df_cat = df_final.groupby('Categoria')[['Ingressos_Previstos', 'Marge_Real']].sum().reset_index()
                
                chart_cat = alt.Chart(df_cat).mark_bar().encode(
                    x=alt.X('Categoria', sort='-y', title=None),
                    y=alt.Y('Marge_Real', title='Benefici (€)'),
                    color=alt.condition(
                        alt.datum.Marge_Real > 0,
                        alt.value("#4ADE80"), # Verd
                        alt.value("#EF4444")  # Vermell
                    ),
                    tooltip=['Categoria', 'Ingressos_Previstos', 'Marge_Real']
                ).properties(height=300)
                st.altair_chart(chart_cat, use_container_width=True)
            
            # TAULA DETALLADA
            with st.expander("Veure Detall per Activitat (Desglossat)"):
                cols_show = ['Categoria', 'Activitat_x', 'Hores_Fetes', 'Cost_Nomina', 'Marge_Real']
                # Renombrem per fer-ho bonic
                df_show = df_final[cols_show].rename(columns={'Activitat_x': 'Activitat'})
                
                st.dataframe(df_show.style.format({
                    'Hores_Fetes': "{:.1f} h",
                    'Cost_Nomina': "{:.2f} €",
                    'Marge_Real': "{:.2f} €"
                }))
                
        else:
            st.warning("⚠️ No s'han trobat dades de mesos. Comprovi la columna 'Data' al Registre (ex: 01/12/2025).")

    except Exception as e:
        st.error(f"Error llegint el fitxer: {e}")
        st.info("Pista: Comprovi que l'enllaç és públic o accessible pel bot i que les pestanyes es diuen 'CONFIGURACIO' i 'REGISTRE_MENSUAL'.")

else:
    st.info("👈 Enganxi l'enllaç del seu nou Excel 'Nexus-iigualada' al menú de l'esquerra per començar.")