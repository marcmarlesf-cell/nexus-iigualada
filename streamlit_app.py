import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Nexus CEO V8", layout="wide", page_icon="👔")

# Estils CSS "Boardroom"
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    
    /* KPI Cards Premium */
    div[data-testid="stMetric"] {
        background-color: #111827; /* Més fosc, més elegant */
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }
    
    /* El Briefing (La caixa intel·ligent) */
    .briefing-box {
        background-color: #1F2937;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #8B5CF6; /* Lila tecnològic */
        margin-bottom: 20px;
    }
    .briefing-title { font-weight: bold; color: #E5E7EB; font-size: 1.1rem; margin-bottom: 5px; }
    .briefing-text { color: #D1D5DB; font-size: 1rem; }
    
    /* Targetes d'Activitat */
    .activity-card { border-radius: 10px; margin-bottom: 10px; border: 1px solid #374151; }
    .good-profit { border-left: 5px solid #10B981; }
    .bad-profit { border-left: 5px solid #EF4444; }
    
    h1, h2, h3 { color: #F9FAFB; font-family: 'Helvetica Neue', sans-serif; }
</style>
""", unsafe_allow_html=True)

st.title("👔 Nexus Executive: Boardroom")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Centre de Dades")
url_master = st.sidebar.text_input("URL Master Excel", help="Enllaç Google Sheet")

# FILTRE DE CATEGORIA (NOU!)
cat_filter = st.sidebar.selectbox("📂 Filtrar per Departament", ["TOTS", "ESPORTS", "IDIOMES", "LUDIC", "ARTISTIC", "TECNOLOGIC"])

if st.sidebar.button("🔄 Refrescar Sistema"):
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

        # DASHBOARD
        mesos = df_registre['Mes_Any'].dropna().unique()
        if len(mesos) > 0:
            mesos_ordenats = sorted(mesos, reverse=True)
            
            # Selector de mes a la part principal per més visibilitat
            col_titol, col_sel = st.columns([3, 1])
            with col_sel:
                mes = st.selectbox("📅 Període:", mesos_ordenats)
            
            # --- LÒGICA DEL MES ACTUAL ---
            df_reg_mes = df_registre[df_registre['Mes_Any'] == mes].copy()
            df_hores = df_reg_mes.groupby('Activitat_Join')['Hores_Fetes'].sum().reset_index()
            
            df_final = pd.merge(df_config, df_hores, on='Activitat_Join', how='left')
            df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
            
            df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
            df_final['Despeses'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
            df_final['Marge_Real'] = df_final['Ingressos_Previstos'] - df_final['Despeses']

            # --- LÒGICA DEL MES ANTERIOR (PER CALCULAR DELTA) ---
            delta_ben = None
            if len(mesos_ordenats) > 1:
                idx_actual = mesos_ordenats.index(mes)
                if idx_actual + 1 < len(mesos_ordenats):
                    mes_prev = mesos_ordenats[idx_actual + 1]
                    # Calculem ràpid el total del mes anterior
                    df_prev = df_registre[df_registre['Mes_Any'] == mes_prev]
                    df_h_prev = df_prev.groupby('Activitat_Join')['Hores_Fetes'].sum().reset_index()
                    df_f_prev = pd.merge(df_config, df_h_prev, on='Activitat_Join', how='left').fillna(0)
                    df_f_prev['Cost'] = (df_f_prev['Hores_Fetes'] * df_f_prev['Preu_Hora_Monitor']) + df_f_prev['Cost_Material_Fix']
                    df_f_prev['Marge'] = df_f_prev['Ingressos_Previstos'] - df_f_prev['Cost']
                    delta_ben = df_final['Marge_Real'].sum() - df_f_prev['Marge'].sum()

            # --- INTEL·LIGÈNCIA ARTIFICIAL (NEXUS AI BRIEFING) ---
            # Calculem insights automàtics
            top_act = df_final.loc[df_final['Marge_Real'].idxmax()]
            worst_act = df_final.loc[df_final['Marge_Real'].idxmin()]
            total_ben = df_final['Marge_Real'].sum()
            
            st.markdown(f"""
            <div class="briefing-box">
                <div class="briefing-title">🤖 Nexus AI Briefing ({mes})</div>
                <div class="briefing-text">
                    • <b>Estat General:</b> El negoci genera <b>{total_ben:,.0f} €</b> de benefici net aquest mes.<br>
                    • <b>L'Estrella:</b> <span style="color:#10B981">{top_act['Activitat']}</span> lidera amb {top_act['Marge_Real']:,.0f} €.<br>
                    • <b>Atenció:</b> <span style="color:#EF4444">{worst_act['Activitat']}</span> és l'activitat amb pitjor rendiment ({worst_act['Marge_Real']:,.0f} €).
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- KPI CARDS (Amb Delta) ---
            tot_ing = df_final['Ingressos_Previstos'].sum()
            marge_pc = (total_ben / tot_ing * 100) if tot_ing > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Ingressos", f"{tot_ing:,.0f} €")
            k2.metric("Despeses Totals", f"{df_final['Despeses'].sum():,.0f} €")
            
            # El KPI de Benefici mostra la fletxa si tenim dades prèvies
            k3.metric("BENEFICI NET", f"{total_ben:,.0f} €", 
                      delta=f"{delta_ben:,.0f} € vs mes anterior" if delta_ben is not None else None)
            
            k4.metric("Marge Comercial", f"{marge_pc:.1f} %")

            # --- FILTRATGE DINÀMIC ---
            df_view = df_final.copy()
            if cat_filter != "TOTS":
                df_view = df_view[df_view['Categoria'] == cat_filter]

            # --- GRÀFICS ---
            st.markdown("---")
            if not df_view.empty:
                col_g1, col_g2 = st.columns(2)
                
                # Agrupem pel gràfic
                df_cat_view = df_view.groupby('Categoria')[['Ingressos_Previstos', 'Marge_Real']].sum().reset_index()

                with col_g1:
                    st.caption(f"Rendibilitat ({cat_filter})")
                    c1 = alt.Chart(df_cat_view).mark_bar(cornerRadius=5).encode(
                        x=alt.X('Categoria', sort='-y', title=None),
                        y=alt.Y('Marge_Real', title=None),
                        color=alt.condition(alt.datum.Marge_Real > 0, alt.value("#10B981"), alt.value("#EF4444")),
                        tooltip=['Categoria', 'Marge_Real']
                    ).properties(height=250)
                    st.altair_chart(c1, use_container_width=True)

                with col_g2:
                    st.caption("Pes dels Ingressos")
                    c2 = alt.Chart(df_cat_view).mark_arc(innerRadius=55).encode(
                        theta=alt.Theta(field="Ingressos_Previstos", type="quantitative"),
                        color=alt.Color(field="Categoria", legend=None),
                        tooltip=['Categoria', 'Ingressos_Previstos']
                    ).properties(height=250)
                    st.altair_chart(c2, use_container_width=True)

                # --- TARGETES MOBILE ---
                st.subheader(f"📱 Detall Operatiu: {cat_filter}")
                
                # Ordenem
                df_sorted = df_view.sort_values(by='Marge_Real', ascending=False)
                
                for index, row in df_sorted.iterrows():
                    ben = row['Marge_Real']
                    nom = row['Activitat']
                    ing = row['Ingressos_Previstos']
                    hor = row['Hores_Fetes']
                    
                    with st.expander(f"{nom}  |  {ben:,.0f} €"):
                        c_1, c_2, c_3 = st.columns(3)
                        c_1.metric("Facturació", f"{ing:.0f} €")
                        c_2.metric("Hores", f"{hor:.1f} h")
                        c_3.metric("Costos", f"{row['Despeses']:.0f} €")
                        
                        if ing > 0:
                            ratio = max(0, min(1.0, ben / ing))
                            st.progress(ratio)
                        else:
                            st.info("Sense facturació prevista")
            else:
                st.warning(f"No hi ha activitats per a la categoria: {cat_filter}")

    except Exception as e:
        st.error(f"Error de sistema: {e}")
else:
    st.info("👈 Connecti el Master Excel.")