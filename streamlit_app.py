import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Nexus Extraescolars PRO", layout="wide", page_icon="🔐")

st.markdown("""
<style>
    .main { background-color: #F0F2F6; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1E3A8A; font-family: 'Arial', sans-serif; }
    .stSuccess { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🔐 Nexus Control: Connexió Segura")
st.markdown("**Dr. Economia:** Sistema connectat via API xifrada. Dades protegides.")

# --- BARRA LATERAL: ENTRADA D'ENLLAÇOS ---
st.sidebar.header("🔗 Enllaços Google Sheets")
st.sidebar.info("Copiï l'URL normal del navegador dels seus fulls de càlcul.")
st.sidebar.caption("Recordi: Ha d'haver compartit els fulls amb el correu del 'nexus-bot' (del fitxer JSON).")

# Inputs per als enllaços (URL normal del navegador)
url_ing = st.sidebar.text_input("URL Ingressos (Full sencer)")
url_hor = st.sidebar.text_input("URL Hores (Full sencer)")

if st.sidebar.button("🔄 Actualitzar Dades Ara"):
    st.cache_data.clear()

# --- CONNEXIÓ ---
# Aquí és on l'app utilitza la clau secreta que configurarà després al Dashboard
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓ DE CÀRREGA DE DADES ---
@st.cache_data(ttl=600)
def get_data_from_sheet(url, use_header=True):
    try:
        if not use_header:
             # Per al full complex d'ingressos, llegim sense capçalera per buscar files manualment
            return conn.read(spreadsheet=url, usecols=list(range(20)), header=None)
        else:
            # Per al full d'hores, llegim normal amb capçaleres
            return conn.read(spreadsheet=url)
    except Exception as e:
        return None

# --- LÒGICA PRINCIPAL ---
if url_ing and url_hor:
    
    # 1. LLEGIR INGRESSOS (Estructura complexa horitzontal)
    df_ing_raw = get_data_from_sheet(url_ing, use_header=False)
    
    if df_ing_raw is not None:
        try:
            # --- MAPA DE FILES (Segons la imatge del Excel Ingressos) ---
            # Pandas comença a comptar des de 0, per tant restem 1 al número de fila de l'Excel
            row_names = 6       # Fila 7 Excel (Noms activitats)
            row_material = 11   # Fila 12 Excel (Cost material)
            row_price = 13      # Fila 14 Excel (Preu)
            row_students = 15   # Fila 16 Excel (Alumnes Reals)
            
            activities_data = []
            
            # Recorrem les columnes buscant activitats
            for col in range(1, len(df_ing_raw.columns)):
                act_name = str(df_ing_raw.iloc[row_names, col])
                
                # Si trobem un nom vàlid
                if act_name != "nan" and act_name.strip() != "":
                    try:
                        # Neteja de símbols d'euro i comes per convertir a número
                        def clean_num(val):
                            s = str(val).replace('€','').replace('.','').replace(',','.').strip()
                            return float(s) if s not in ['nan', '', '-'] else 0.0

                        price = clean_num(df_ing_raw.iloc[row_price, col])
                        students = clean_num(df_ing_raw.iloc[row_students, col])
                        material_cost = clean_num(df_ing_raw.iloc[row_material, col])
                        
                        clean_name = act_name.strip().upper()
                        
                        activities_data.append({
                            'Activitat': clean_name,
                            'Preu': price,
                            'Alumnes': students,
                            'Cost_Material': material_cost,
                            'Ingressos_Teorics': price * students
                        })
                    except:
                        pass # Saltem columnes que donin error
            
            df_revenue = pd.DataFrame(activities_data)
            
            # 2. LLEGIR HORES (Nòmines Monitors)
            df_cost_raw = get_data_from_sheet(url_hor, use_header=True)
            
            if df_cost_raw is not None:
                # Selecció columnes segons posició (més segur que per nom si canvien)
                # Assumim: Col 0=Data, Col 2=Activitat, Col 5=Total a Pagar (segons la imatge)
                df_cost = df_cost_raw.iloc[:, [0, 2, 5]].copy()
                df_cost.columns = ['Data', 'Activitat_Cost', 'Cost_Nomina']
                
                # Neteja
                df_cost['Cost_Nomina'] = df_cost['Cost_Nomina'].astype(str).str.replace('€','').str.replace('.','').str.replace(',','.').astype(float)
                df_cost['Data_DT'] = pd.to_datetime(df_cost['Data'], dayfirst=True, errors='coerce')
                df_cost['Mes_Any'] = df_cost['Data_DT'].dt.strftime('%Y-%m')
                
                # --- SELECTOR DE MES ---
                all_months = df_cost['Mes_Any'].dropna().unique()
                if len(all_months) > 0:
                    selected_month = st.selectbox("📅 Seleccioni Mes a Analitzar", sorted(all_months, reverse=True))
                    
                    # FILTRAT
                    df_cost_filtered = df_cost[df_cost['Mes_Any'] == selected_month]
                    df_cost_grouped = df_cost_filtered.groupby('Activitat_Cost')['Cost_Nomina'].sum().reset_index()
                    df_cost_grouped['Activitat_Join'] = df_cost_grouped['Activitat_Cost'].str.strip().str.upper()

                    # 3. CREUAMENT FINAL DE DADES
                    df_final = pd.merge(df_revenue, df_cost_grouped, left_on='Activitat', right_on='Activitat_Join', how='left')
                    df_final['Cost_Nomina'] = df_final['Cost_Nomina'].fillna(0)
                    
                    # CÀLCULS FINALS (Amb Material)
                    # Marge = Ingressos - (Nòmina + Material)
                    df_final['Despeses_Totals'] = df_final['Cost_Nomina'] + df_final['Cost_Material']
                    df_final['Marge_Real'] = df_final['Ingressos_Teorics'] - df_final['Despeses_Totals']
                    
                    # --- DASHBOARD VISUAL ---
                    st.divider()
                    
                    # KPIs Superiors
                    k1, k2, k3, k4 = st.columns(4)
                    total_marge = df_final['Marge_Real'].sum()
                    k1.metric("Ingressos Totals", f"{df_final['Ingressos_Teorics'].sum():,.2f} €")
                    k2.metric("Cost Nòmines", f"{df_final['Cost_Nomina'].sum():,.2f} €", delta_color="inverse")
                    k3.metric("Cost Material", f"{df_final['Cost_Material'].sum():,.2f} €", delta_color="inverse")
                    k4.metric("Benefici Net", f"{total_marge:,.2f} €", 
                              delta="Rendible" if total_marge > 0 else "Pèrdues")

                    # Gràfic de barres
                    st.subheader(f"Rendibilitat Real - {selected_month}")
                    chart = alt.Chart(df_final).mark_bar().encode(
                        x=alt.X('Activitat', sort='-y'),
                        y=alt.Y('Marge_Real', title='Benefici Real (€)'),
                        color=alt.condition(
                            alt.datum.Marge_Real > 0,
                            alt.value("#10B981"), # Verd
                            alt.value("#EF4444")  # Vermell
                        ),
                        tooltip=['Activitat', 'Ingressos_Teorics', 'Cost_Nomina', 'Cost_Material', 'Marge_Real']
                    ).properties(height=400)
                    st.altair_chart(chart, use_container_width=True)
                    
                    # Taula detallada
                    with st.expander("Veure detall numèric complet (Desglossat)"):
                        st.dataframe(df_final[['Activitat', 'Ingressos_Teorics', 'Cost_Nomina', 'Cost_Material', 'Marge_Real']]
                                     .style.format("{:.2f} €"))
                else:
                    st.warning("No s'han trobat dades de dates vàlides al full d'hores.")

            else:
                st.error("Error llegint el full d'hores. Comprovi que el 'nexus-bot' tingui permís d'editor.")
        except Exception as e:
            st.error(f"Error processant les dades: {e}")
            st.info("Pista: Comprovi que els enllaços són correctes i que l'estructura dels excels no ha canviat dràsticament.")
    else:
        st.error("Error llegint el full d'ingressos. Comprovi que ha compartit el full amb el 'nexus-bot' i que l'enllaç és correcte.")

else:
    st.info("👋 **Benvingut Senyor.**")
    st.markdown("""
    Per començar:
    1. Copiï l'URL del navegador del seu full **Ingressos**.
    2. Copiï l'URL del navegador del seu full **Registre d'Hores**.
    3. Enganxi'ls a la barra lateral esquerra.
    """)