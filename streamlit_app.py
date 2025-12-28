import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Nexus Extraescolars PRO", layout="wide", page_icon="🔐")

# Estils CSS corregits per veure bé els números en mode fosc
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

st.title("🔐 Nexus Control: Connexió Segura")
st.markdown("**Dr. Economia:** Sistema actiu. Dades en temps real.")

# --- BARRA LATERAL ---
st.sidebar.header("🔗 Enllaços Google Sheets")
url_ing = st.sidebar.text_input("URL Ingressos (Full sencer)")
url_hor = st.sidebar.text_input("URL Hores (Full sencer)")

if st.sidebar.button("🔄 Actualitzar Dades Ara"):
    st.cache_data.clear()

# --- CONNEXIÓ ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def get_data_from_sheet(url, use_header=True):
    try:
        if not use_header:
            return conn.read(spreadsheet=url, usecols=list(range(20)), header=None)
        else:
            return conn.read(spreadsheet=url)
    except Exception:
        return None

# --- LÒGICA PRINCIPAL ---
if url_ing and url_hor:
    
    # 1. LLEGIR INGRESSOS
    df_ing_raw = get_data_from_sheet(url_ing, use_header=False)
    
    if df_ing_raw is not None:
        try:
            # Files clau (ajustades per Pandas)
            row_names = 6       
            row_material = 11   
            row_price = 13      
            row_students = 15   
            
            activities_data = []
            
            for col in range(1, len(df_ing_raw.columns)):
                act_name = str(df_ing_raw.iloc[row_names, col])
                
                if act_name != "nan" and act_name.strip() != "":
                    try:
                        def clean_num(val):
                            s = str(val).replace('€','').replace('.','').replace(',','.').strip()
                            try:
                                return float(s)
                            except:
                                return 0.0

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
                        pass
            
            df_revenue = pd.DataFrame(activities_data)
            
            # 2. LLEGIR HORES
            df_cost_raw = get_data_from_sheet(url_hor, use_header=True)
            
            if df_cost_raw is not None:
                df_cost = df_cost_raw.iloc[:, [0, 2, 5]].copy()
                df_cost.columns = ['Data', 'Activitat_Cost', 'Cost_Nomina']
                
                df_cost['Cost_Nomina'] = df_cost['Cost_Nomina'].astype(str).str.replace('€','').str.replace('.','').str.replace(',','.').astype(float)
                df_cost['Data_DT'] = pd.to_datetime(df_cost['Data'], dayfirst=True, errors='coerce')
                df_cost['Mes_Any'] = df_cost['Data_DT'].dt.strftime('%Y-%m')
                
                all_months = df_cost['Mes_Any'].dropna().unique()
                if len(all_months) > 0:
                    selected_month = st.selectbox("📅 Seleccioni Mes a Analitzar", sorted(all_months, reverse=True))
                    
                    df_cost_filtered = df_cost[df_cost['Mes_Any'] == selected_month]
                    df_cost_grouped = df_cost_filtered.groupby('Activitat_Cost')['Cost_Nomina'].sum().reset_index()
                    df_cost_grouped['Activitat_Join'] = df_cost_grouped['Activitat_Cost'].str.strip().str.upper()

                    # 3. CREUAMENT
                    df_final = pd.merge(df_revenue, df_cost_grouped, left_on='Activitat', right_on='Activitat_Join', how='left')
                    df_final['Cost_Nomina'] = df_final['Cost_Nomina'].fillna(0)
                    
                    df_final['Despeses_Totals'] = df_final['Cost_Nomina'] + df_final['Cost_Material']
                    df_final['Marge_Real'] = df_final['Ingressos_Teorics'] - df_final['Despeses_Totals']
                    
                    # --- DASHBOARD ---
                    st.divider()
                    
                    # KPIs
                    k1, k2, k3, k4 = st.columns(4)
                    total_marge = df_final['Marge_Real'].sum()
                    k1.metric("Ingressos", f"{df_final['Ingressos_Teorics'].sum():,.2f} €")
                    k2.metric("Nòmines", f"{df_final['Cost_Nomina'].sum():,.2f} €")
                    k3.metric("Material", f"{df_final['Cost_Material'].sum():,.2f} €")
                    k4.metric("Resultat", f"{total_marge:,.2f} €", delta="Bé" if total_marge > 0 else "Revisar")

                    # Gràfic
                    st.subheader(f"Rendibilitat per Activitat - {selected_month}")
                    chart = alt.Chart(df_final).mark_bar().encode(
                        x=alt.X('Activitat', sort='-y'),
                        y=alt.Y('Marge_Real', title='Benefici (€)'),
                        color=alt.condition(
                            alt.datum.Marge_Real > 0,
                            alt.value("#4ADE80"), # Verd
                            alt.value("#EF4444")  # Vermell
                        ),
                        tooltip=['Activitat', 'Ingressos_Teorics', 'Cost_Nomina', 'Marge_Real']
                    ).properties(height=400)
                    st.altair_chart(chart, use_container_width=True)
                    
                    # Taula (CORREGIDA)
                    with st.expander("Veure detall numèric"):
                        # Especifiquem format només per a columnes numèriques per evitar l'error
                        cols_to_show = ['Activitat', 'Ingressos_Teorics', 'Cost_Nomina', 'Cost_Material', 'Marge_Real']
                        format_dict = {
                            'Ingressos_Teorics': "{:.2f} €",
                            'Cost_Nomina': "{:.2f} €",
                            'Cost_Material': "{:.2f} €",
                            'Marge_Real': "{:.2f} €"
                        }
                        st.dataframe(df_final[cols_to_show].style.format(format_dict))
                else:
                    st.warning("No hi ha dades de dates vàlides.")
            else:
                st.error("Error llegint el full d'Hores.")
        except Exception as e:
            st.error(f"Error intern: {e}")
    else:
        st.error("Error llegint Ingressos.")
else:
    st.info("👈 Introdueixi els enllaços a l'esquerra per començar.")