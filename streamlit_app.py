import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Marc Marlés Control", layout="wide", page_icon="🎓")

# --- ESTILS CSS PREMIUM ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0E1117; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
    
    div[data-testid="stMetric"] {
        background-color: #1F2937; padding: 15px; border-radius: 12px; 
        border: 1px solid #374151; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    h1, h2, h3, p, label, .briefing-title { color: #E5E7EB !important; font-family: 'Segoe UI', sans-serif; }
    
    .stTabs [data-baseweb="tab"] { background-color: #111827; border-radius: 6px; color: #9CA3AF; border: 1px solid #374151; }
    .stTabs [aria-selected="true"] { background-color: #7C3AED !important; color: white !important; }
    
    .streamlit-expanderHeader { background-color: #1F2937 !important; color: white !important; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- CAPÇALERA ---
c_head_1, c_head_2 = st.columns([3,1])
with c_head_1: st.title("🎓 Marc Marlés - Estratègia")
with c_head_2: st.caption("v14.0 Smart Hunter")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Connexió")
url_master = st.sidebar.text_input("URL Master Excel", help="Només l'enllaç del Google Sheet.")
if st.sidebar.button("🔄 Refrescar", use_container_width=True):
    st.cache_data.clear()

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIONS AUXILIARS ---
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
    return "⚽" if "ESPORTS" in cat else "🇬🇧" if "IDIOMES" in cat else "🎨" if "LUDIC" in cat else "🤖" if "TECNOLOGIC" in cat else "🎭" if "ARTISTIC" in cat else "📝"

# --- MOTOR DE CERCA INTEL·LIGENT ---
def carregar_dades_smart(url):
    """
    Busca automàticament les pestanyes correctes basant-se en el contingut
    de les capçaleres, ignorant pestanyes de nòmines o càlculs.
    """
    df_conf = None
    df_reg = None
    log_missatges = []

    # Iterem sobre les primeres 5 pestanyes (per si la bona no és la primera)
    for i in range(5):
        try:
            df_temp = conn.read(spreadsheet=url, worksheet=i)
            cols = list(df_temp.columns)
            
            # 1. IDENTIFICAR CONFIGURACIÓ
            # Busquem les columnes exactes de la teva captura: 'Preu_Alumne' i 'Num_Alumnes'
            if 'Preu_Alumne' in cols and 'Num_Alumnes' in cols:
                df_conf = df_temp
                # Assegurar tipus numèrics
                for c in ['Preu_Alumne', 'Num_Alumnes', 'Cost_Material_Fix', 'Preu_Hora_Monitor']:
                    if c in df_conf.columns: df_conf[c] = df_conf[c].apply(netejar_numero)
                
                # Càlculs base
                df_conf['Ingressos_Previstos'] = df_conf['Preu_Alumne'] * df_conf['Num_Alumnes']
                df_conf['Activitat_Join'] = df_conf['Activitat'].astype(str).str.strip().str.upper()
            
            # 2. IDENTIFICAR REGISTRE
            # Busquem les columnes exactes de la teva captura: 'Hores_Fetes' i 'Data'
            elif 'Hores_Fetes' in cols and 'Data' in cols:
                df_reg = df_temp
                # Neteja
                df_reg['Hores_Fetes'] = df_reg['Hores_Fetes'].apply(netejar_numero)
                df_reg['Data_DT'] = pd.to_datetime(df_reg['Data'], dayfirst=True, errors='coerce')
                df_reg['Mes_Any'] = df_reg['Data_DT'].dt.strftime('%Y-%m')
                df_reg['Activitat_Join'] = df_reg['Activitat'].astype(str).str.strip().str.upper()

        except Exception as e:
            pass # Si una pestanya falla o està buida, continuem buscant

        # Si ja hem trobat les dues, parem de buscar per anar ràpid
        if df_conf is not None and df_reg is not None:
            break
            
    return df_conf, df_reg

# --- APP PRINCIPAL ---
if url_master:
    try:
        # Cridem al "Hunter"
        df_config, df_registre = carregar_dades_smart(url_master)

        # VALIDACIÓ: Si no trobem la configuració, no podem fer res
        if df_config is None:
            st.error("❌ No he trobat la pestanya 'CONFIGURACIO'.")
            st.info("Assegura't que el Excel té una pestanya amb les columnes: 'Preu_Alumne' i 'Num_Alumnes'.")
            st.stop()

        # PREPARACIÓ DE DADES
        mes = "Global"
        df_final = df_config.copy()

        # Si tenim registre, creem el selector de mesos
        if df_registre is not None:
            mesos = sorted(df_registre['Mes_Any'].dropna().unique(), reverse=True)
            
            st.divider()
            c1, c2 = st.columns([1, 4])
            
            if len(mesos) > 0:
                with c1: mes = st.selectbox("📅 Període:", mesos)
                # Filtrem per mes
                df_reg_mes = df_registre[df_registre['Mes_Any'] == mes].copy()
                # Agrupem hores
                df_hores = df_reg_mes.groupby('Activitat_Join')['Hores_Fetes'].sum().reset_index()
                # Fusionem amb la config
                df_final = pd.merge(df_config, df_hores, on='Activitat_Join', how='left')
                df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
            else:
                with c1: st.info("Sense dades temporals")
                df_final['Hores_Fetes'] = 0
        else:
            # Si no troba registre, assumeix 0 hores però mostra la config
            st.warning("⚠️ No trobo la pestanya 'REGISTRE_MENSUAL'. Mostrant només dades teòriques.")
            df_final['Hores_Fetes'] = 0

        # FILTRES
        with c2:
            if 'Categoria' in df_config.columns:
                cats = ["TOTS"] + sorted(list(df_config['Categoria'].unique()))
                cat_filter = st.radio("Departament:", cats, horizontal=True)
            else:
                cat_filter = "TOTS"

        # CÀLCULS ECONÒMICS FINALS
        df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
        
        # Gestió robusta de despeses
        if 'Cost_Material_Fix' in df_final.columns:
            df_final['Despeses'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
        else:
            df_final['Despeses'] = df_final['Cost_Nomina']

        df_final['Marge_Real'] = df_final['Ingressos_Previstos'] - df_final['Despeses']

        # APLICAR FILTRES DE VISUALITZACIÓ
        df_view = df_final.copy()
        if cat_filter != "TOTS" and 'Categoria' in df_view.columns:
            df_view = df_view[df_view['Categoria'] == cat_filter]

        # --- KPI DASHBOARD ---
        tot_ing = df_view['Ingressos_Previstos'].sum()
        tot_ben = df_view['Marge_Real'].sum()
        tot_stu = df_view['Num_Alumnes'].sum()
        marge_pct = (tot_ben / tot_ing * 100) if tot_ing > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("👥 Alumnes", f"{tot_stu:.0f}")
        k2.metric("Facturació", f"{tot_ing:,.0f} €")
        k3.metric("Marge %", f"{marge_pct:.1f} %")
        k4.metric("Benefici Net", f"{tot_ben:,.0f} €", delta=f"{tot_ben:,.0f} €")

        st.markdown("---")

        # --- PESTANYES VISUALS ---
        tab1, tab2, tab3 = st.tabs(["📊 Rànquing", "🎯 Matriu Estratègica", "📈 Tendència"])

        with tab1: # RANKING (BAR CHART)
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

        with tab2: # MATRIU (SCATTER)
            if not df_view.empty:
                fig_m = px.scatter(df_view, x="Num_Alumnes", y="Marge_Real",
                                   color="Categoria" if "Categoria" in df_view.columns else None,
                                   size="Ingressos_Previstos", hover_name="Activitat", text="Activitat")
                fig_m.add_hline(y=0, line_dash="dash", line_color="white", annotation_text="Punt d'equilibri")
                fig_m.update_traces(textposition='top center')
                fig_m.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='white'), height=500, showlegend=False,
                                    xaxis=dict(showgrid=True, gridcolor='#374151', title="Volum Alumnes"),
                                    yaxis=dict(showgrid=True, gridcolor='#374151', title="Benefici Net (€)"))
                st.plotly_chart(fig_m, use_container_width=True)

        with tab3: # TENDÈNCIA (LINE)
            if df_registre is not None:
                try:
                    df_trend = df_registre.groupby('Mes_Any')['Hores_Fetes'].sum().reset_index()
                    fig_l = px.line(df_trend, x='Mes_Any', y='Hores_Fetes', markers=True, title="Evolució Hores Monitors")
                    fig_l.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                        font=dict(color='white'), yaxis_title="Hores", height=400)
                    fig_l.update_traces(line_color='#8B5CF6', line_width=4)
                    st.plotly_chart(fig_l, use_container_width=True)
                except:
                    st.info("Falten dades històriques per fer la gràfica.")
            else:
                st.info("No s'ha detectat full de registre per mostrar tendències.")

        # --- DETALL FINAL ---
        st.subheader("📋 Fitxes Detall")
        if not df_view.empty:
            for i, row in df_view.sort_values('Marge_Real', ascending=False).iterrows():
                icon = get_icon(row['Categoria']) if 'Categoria' in row else "📝"
                with st.expander(f"{icon} {row['Activitat']} | {row['Marge_Real']:,.0f} €"):
                    c_a, c_b = st.columns(2)
                    c_a.write(f"**Ingressos:** {row['Ingressos_Previstos']:.0f}€ ({row['Num_Alumnes']:.0f} alumnes)")
                    c_b.write(f"**Costos:** {row['Despeses']:.0f}€ ({row['Hores_Fetes']:.1f} hores)")

    except Exception as e:
        st.error(f"⚠️ Error inesperat: {e}")
else:
    st.info("👈 Introdueixi la URL del full de càlcul per començar.")