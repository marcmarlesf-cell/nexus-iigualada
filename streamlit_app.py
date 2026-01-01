import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Marc Marlés Control", layout="wide", page_icon="🎓")

# --- ESTILS CSS PREMIUM & FIX BUGS ---
st.markdown("""
<style>
    /* 1. Fons fosc net */
    [data-testid="stAppViewContainer"] { background-color: #0E1117; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }

    /* 2. AMAGAR TEXT 'PRESS ENTER TO APPLY' */
    div[data-testid="InputInstructions"] > span:nth-child(1) {
        display: none;
    }
    
    /* 3. KPI Cards */
    div[data-testid="stMetric"] {
        background-color: #1F2937; 
        padding: 15px; border-radius: 12px; border: 1px solid #374151;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* 4. Tipografia */
    h1, h2, h3, p, label, .briefing-title { color: #E5E7EB !important; font-family: 'Segoe UI', sans-serif; }
    
    /* 5. Pestanyes */
    .stTabs [data-baseweb="tab"] { background-color: #111827; border-radius: 6px; color: #9CA3AF; padding: 8px 16px; border: 1px solid #374151; }
    .stTabs [aria-selected="true"] { background-color: #7C3AED !important; color: white !important; }
    
    /* Expander */
    .streamlit-expanderHeader { background-color: #1F2937 !important; color: white !important; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- CAPÇALERA ---
col_head_1, col_head_2 = st.columns([3,1])
with col_head_1:
    st.title("🎓 Marc Marlés - Estratègia")
with col_head_2:
    st.caption("v12.1 Auto-Fix")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuració")
url_master = st.sidebar.text_input("URL Master Excel", help="Enganxi l'enllaç aquí")
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

# Funció per normalitzar columnes (La Clau del Fix)
def normalitzar_cols(df):
    # Treu espais del principi/final i substitueix espais interns per guions baixos
    df.columns = df.columns.str.strip().str.replace(' ', '_')
    return df

if url_master:
    try:
        # --- CÀRREGA DE DADES ---
        # 1. Full de Configuració (Activitats, Preus...)
        df_config = conn.read(spreadsheet=url_master, worksheet=0)
        df_config = normalitzar_cols(df_config) # <--- AUTO CORRECCIÓ AQUÍ
        
        # Validació de seguretat per saber què està passant
        required_cols = ['Activitat', 'Preu_Alumne', 'Num_Alumnes']
        missing = [c for c in required_cols if c not in df_config.columns]
        
        if missing:
            st.error(f"⚠️ NO TROBO LES COLUMNES: {missing}")
            st.warning(f"🧐 Les columnes que he llegit del Excel són: {list(df_config.columns)}")
            st.info("Solució: Canviï el nom a l'Excel o asseguri's que no tenen accents estranys.")
            st.stop() # Aturem per no petar

        cols_num = ['Preu_Alumne', 'Num_Alumnes', 'Cost_Material_Fix', 'Preu_Hora_Monitor']
        for col in cols_num:
            if col in df_config.columns: df_config[col] = df_config[col].apply(netejar_numero)
        
        df_config['Ingressos_Previstos'] = df_config['Preu_Alumne'] * df_config['Num_Alumnes']
        df_config['Activitat_Join'] = df_config['Activitat'].astype(str).str.strip().str.upper()

        # 2. Full de Registre (Hores fetes...)
        df_registre = conn.read(spreadsheet=url_master, worksheet=1)
        df_registre = normalitzar_cols(df_registre) # <--- AUTO CORRECCIÓ TAMBÉ AQUÍ
        
        if 'Hores_Fetes' in df_registre.columns: df_registre['Hores_Fetes'] = df_registre['Hores_Fetes'].apply(netejar_numero)
        
        df_registre['Data_DT'] = pd.to_datetime(df_registre['Data'], dayfirst=True, errors='coerce')
        df_registre['Mes_Any'] = df_registre['Data_DT'].dt.strftime('%Y-%m')
        df_registre['Activitat_Join'] = df_registre['Activitat'].astype(str).str.strip().str.upper()

        mesos = df_registre['Mes_Any'].dropna().unique()
        
        if len(mesos) > 0:
            mesos_ordenats = sorted(mesos, reverse=True)
            
            # --- ZONA DE CONTROL ---
            st.divider()
            c1, c2 = st.columns([1, 4])
            with c1: mes = st.selectbox("📅 Període:", mesos_ordenats)
            with c2: 
                # Protecció per si no existeix la columna Categoria
                if 'Categoria' in df_config.columns:
                    cats = ["TOTS"] + sorted(list(df_config['Categoria'].unique()))
                    cat_filter = st.radio("Departament:", cats, horizontal=True)
                else:
                    cat_filter = "TOTS"

            # --- MOTOR ---
            df_reg_mes = df_registre[df_registre['Mes_Any'] == mes].copy()
            df_hores = df_reg_mes.groupby('Activitat_Join')['Hores_Fetes'].sum().reset_index()
            
            df_final = pd.merge(df_config, df_hores, on='Activitat_Join', how='left')
            df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
            
            df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
            
            # Càlcul de despeses (robustesa si falta Cost Material)
            if 'Cost_Material_Fix' in df_final.columns:
                df_final['Despeses'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
            else:
                df_final['Despeses'] = df_final['Cost_Nomina']

            df_final['Marge_Real'] = df_final['Ingressos_Previstos'] - df_final['Despeses']
            
            # FILTRATGE
            df_view = df_final.copy()
            if cat_filter != "TOTS" and 'Categoria' in df_view.columns:
                df_view = df_view[df_view['Categoria'] == cat_filter]

            # --- DASHBOARD ---
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
            
            tab1, tab2, tab3 = st.tabs(["📊 Rànquing", "🎯 Matriu Estratègica", "📈 Tendència"])
            
            # TAB 1: BARRES
            with tab1:
                if not df_view.empty:
                    df_sorted = df_view.sort_values('Marge_Real', ascending=True)
                    fig = px.bar(df_sorted, x='Marge_Real', y='Activitat', orientation='h', 
                                 text='Marge_Real', color='Marge_Real', 
                                 color_continuous_scale=['#EF4444', '#10B981'])
                    fig.update_traces(texttemplate='%{text:.0f} €', textposition='outside')
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                      font=dict(color='white'), xaxis_title=None, yaxis_title=None,
                                      height=max(400, len(df_view)*35))
                    st.plotly_chart(fig, use_container_width=True)

            # TAB 2: MATRIU (SOLUCIONAT EL ERROR POSSIBLE)
            with tab2:
                if not df_view.empty:
                    fig_m = px.scatter(df_view, x="Num_Alumnes", y="Marge_Real", 
                                       color="Categoria" if "Categoria" in df_view.columns else None,
                                       size="Ingressos_Previstos", hover_name="Activitat", text="Activitat")
                    fig_m.add_hline(y=0, line_dash="dash", line_color="white")
                    fig_m.update_traces(textposition='top center')
                    fig_m.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                        font=dict(color='white'), height=500, showlegend=False,
                                        xaxis=dict(showgrid=True, gridcolor='#374151'),
                                        yaxis=dict(showgrid=True, gridcolor='#374151'))
                    st.plotly_chart(fig_m, use_container_width=True)

            # TAB 3: TENDÈNCIA
            with tab3:
                try:
                    df_trend = df_registre.groupby('Mes_Any')['Hores_Fetes'].sum().reset_index()
                    fig_l = px.line(df_trend, x='Mes_Any', y='Hores_Fetes', markers=True)
                    fig_l.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                        font=dict(color='white'), yaxis_title="Hores", height=400)
                    fig_l.update_traces(line_color='#8B5CF6', line_width=4)
                    st.plotly_chart(fig_l, use_container_width=True)
                except:
                    st.caption("No hi ha prou dades temporals.")
                    
            # DETALL
            st.subheader("📋 Fitxes Detall")
            if not df_view.empty:
                for i, row in df_view.sort_values('Marge_Real', ascending=False).iterrows():
                    icon = get_icon(row['Categoria']) if 'Categoria' in row else "📝"
                    with st.expander(f"{icon} {row['Activitat']} | {row['Marge_Real']:,.0f} €"):
                        st.write(f"Alumnes: {row['Num_Alumnes']:.0f} | Ingressos: {row['Ingressos_Previstos']:.0f}€")

    except Exception as e:
        st.error(f"⚠️ ERROR TÈCNIC: {e}")
        st.info("Consell: Revisa que al teu Excel les columnes es diguin: 'Activitat', 'Preu_Alumne' (o 'Preu Alumne'), 'Num_Alumnes'.")

else:
    st.info("👈 Introdueixi la URL del full de càlcul per començar.")