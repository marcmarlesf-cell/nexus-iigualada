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
    
    .stProgress > div > div > div > div { background-color: #3B82F6; }
</style>
""", unsafe_allow_html=True)

# --- CAPÇALERA ---
c_head_1, c_head_2 = st.columns([3,1])
with c_head_1: st.title("🎓 Control de Gestió (MBA)")
with c_head_2: st.caption("v19.0 Override Puntual")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Connexió de Dades")
url_master = st.sidebar.text_input("URL Master Excel", help="Enllaç al Google Sheet.")
if st.sidebar.button("🔄 Actualitzar Dades", use_container_width=True):
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
    df_conf = None
    df_reg = None
    
    for i in range(5):
        try:
            df_temp = conn.read(spreadsheet=url, worksheet=i)
            cols = list(df_temp.columns)
            
            # Identificar CONFIGURACIÓ
            if 'Preu_Alumne' in cols and ('Num_Alumnes' in cols or 'Alumnes' in cols):
                df_conf = df_temp
                col_alumnes = 'Num_Alumnes' if 'Num_Alumnes' in df_conf.columns else 'Alumnes'
                df_conf = df_conf.rename(columns={col_alumnes: 'Num_Alumnes_Base'})
                
                for c in ['Preu_Alumne', 'Num_Alumnes_Base', 'Cost_Material_Fix', 'Preu_Hora_Monitor']:
                    if c in df_conf.columns: df_conf[c] = df_conf[c].apply(netejar_numero)
                
                df_conf['Activitat_Join'] = df_conf['Activitat'].astype(str).str.strip().str.upper()
            
            # Identificar REGISTRE
            elif ('Hores_Fetes' in cols or 'Hores' in cols) and 'Data' in cols:
                df_reg = df_temp
                if 'Hores' in df_reg.columns and 'Hores_Fetes' not in df_reg.columns:
                    df_reg = df_reg.rename(columns={'Hores': 'Hores_Fetes'})
                
                df_reg['Hores_Fetes'] = df_reg['Hores_Fetes'].apply(netejar_numero)
                
                # Detectar columna d'alumnes reals (MANUAL)
                col_var_alumnes = None
                for c in df_reg.columns:
                    if 'ALUMNE' in c.upper() and ('MES' in c.upper() or 'REAL' in c.upper() or 'ACTUAL' in c.upper()):
                        col_var_alumnes = c
                        break
                
                if col_var_alumnes:
                    df_reg['Alumnes_Input'] = df_reg[col_var_alumnes].apply(netejar_numero)
                    # A V19 NO convertim 0 a NA, volem que 0 o buit sigui ignorat després
                else:
                    df_reg['Alumnes_Input'] = 0.0

                df_reg['Data_DT'] = pd.to_datetime(df_reg['Data'], dayfirst=True, errors='coerce')
                df_reg['Mes_Any'] = df_reg['Data_DT'].dt.strftime('%Y-%m')
                df_reg['Activitat_Join'] = df_reg['Activitat'].astype(str).str.strip().str.upper()

        except Exception:
            pass
        
        if df_conf is not None and df_reg is not None:
            break
            
    return df_conf, df_reg

# --- APP PRINCIPAL ---
if url_master:
    try:
        df_config, df_registre = carregar_dades_smart(url_master)

        if df_config is None:
            st.error("❌ No he trobat la pestanya de Configuració.")
            st.stop()

        # PREPARACIÓ GLOBAL
        mes = "Global"
        df_final = df_config.copy()
        if 'Num_Alumnes_Base' not in df_final.columns: df_final['Num_Alumnes_Base'] = 0

        # --- SELECTOR DE MESOS ---
        st.divider()
        c1, c2 = st.columns([1, 4])
        
        if df_registre is not None:
            mesos = sorted(df_registre['Mes_Any'].dropna().unique(), reverse=True)
            if len(mesos) > 0:
                with c1: mes = st.selectbox("📅 Període d'Anàlisi:", mesos)
                
                # --- DADES DEL MES ACTUAL ---
                df_reg_mes = df_registre[df_registre['Mes_Any'] == mes].copy()
                
                # Agrupem: Hores es sumen, Alumnes Input agafem el màxim que hagi posat
                df_agrupat = df_reg_mes.groupby('Activitat_Join').agg({
                    'Hores_Fetes': 'sum',
                    'Alumnes_Input': 'max' 
                }).reset_index()
                
                df_final = pd.merge(df_config, df_agrupat, on='Activitat_Join', how='left')
                df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
                
                # --- LÒGICA V19: PRIORITAT DIRECTA ---
                # Si hi ha dada al registre (>0), la fem servir.
                # Si està buida o és 0, fem servir la BASE de la configuració.
                # (Sense memòria de mesos anteriors)
                df_final['Num_Alumnes_Final'] = df_final.apply(
                    lambda x: x['Alumnes_Input'] if pd.notna(x['Alumnes_Input']) and x['Alumnes_Input'] > 0 
                    else x['Num_Alumnes_Base'], axis=1
                )
                
            else:
                with c1: st.info("Sense dades temporals")
                df_final['Hores_Fetes'] = 0
                df_final['Num_Alumnes_Final'] = df_final['Num_Alumnes_Base']
        else:
            df_final['Hores_Fetes'] = 0
            df_final['Num_Alumnes_Final'] = df_final['Num_Alumnes_Base']

        # Filtre Departament
        with c2:
            if 'Categoria' in df_config.columns:
                cats = ["TOTS"] + sorted(list(df_config['Categoria'].unique()))
                cat_filter = st.radio("Unitat de Negoci:", cats, horizontal=True)
            else:
                cat_filter = "TOTS"

        # CÀLCULS FINANCERS
        df_final['Ingressos_Reals'] = df_final['Preu_Alumne'] * df_final['Num_Alumnes_Final']
        df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
        if 'Cost_Material_Fix' in df_final.columns:
            df_final['Despeses'] = df_final['Cost_Nomina'] + df_final['Cost_Material_Fix']
        else:
            df_final['Despeses'] = df_final['Cost_Nomina']
        df_final['Marge_Real'] = df_final['Ingressos_Reals'] - df_final['Despeses']

        # FILTRES VISUALS
        df_view = df_final.copy()
        if cat_filter != "TOTS" and 'Categoria' in df_view.columns:
            df_view = df_view[df_view['Categoria'] == cat_filter]

        # --- KPI DASHBOARD ---
        tot_ing = df_view['Ingressos_Reals'].sum()
        tot_ben = df_view['Marge_Real'].sum()
        tot_stu = df_view['Num_Alumnes_Final'].sum()
        marge_pct = (tot_ben / tot_ing * 100) if tot_ing > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("👥 Alumnes Actius", f"{tot_stu:.0f}")
        k2.metric("💶 Volum de Negoci", f"{tot_ing:,.0f} €")
        k3.metric("📊 Marge Comercial", f"{marge_pct:.1f} %")
        k4.metric("💰 Benefici Operatiu", f"{tot_ben:,.0f} €", delta=f"{tot_ben:,.0f} €")

        st.markdown("---")

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["📊 Rànquing", "🎯 Matriu BCG", "📈 Evolució"])

        with tab1: # RÀNQUING
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

        with tab2: # MATRIU
            if not df_view.empty:
                fig_m = px.scatter(df_view, x="Num_Alumnes_Final", y="Marge_Real",
                                   color="Categoria" if "Categoria" in df_view.columns else None,
                                   size="Ingressos_Reals", hover_name="Activitat", text="Activitat")
                fig_m.add_hline(y=0, line_dash="dash", line_color="white")
                fig_m.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='white'), height=500, showlegend=False,
                                    xaxis=dict(showgrid=True, gridcolor='#374151', title="Alumnes"),
                                    yaxis=dict(showgrid=True, gridcolor='#374151', title="Benefici (€)"))
                st.plotly_chart(fig_m, use_container_width=True)

        with tab3: # TENDÈNCIA
            if df_registre is not None and len(mesos) > 0:
                # Per la tendència, també apliquem la lògica V19 (sense memòria)
                df_trend_full = pd.merge(df_registre, df_config[['Activitat_Join', 'Preu_Alumne', 'Preu_Hora_Monitor', 'Cost_Material_Fix', 'Num_Alumnes_Base']], on='Activitat_Join', how='left')
                
                # Lògica V19 aplicada a l'històric
                df_trend_full['Alumnes_Calc'] = df_trend_full.apply(
                    lambda x: x['Alumnes_Input'] if pd.notna(x['Alumnes_Input']) and x['Alumnes_Input'] > 0 
                    else x['Num_Alumnes_Base'], axis=1
                )

                df_trend_full['Cost_Total'] = (df_trend_full['Hores_Fetes'] * df_trend_full['Preu_Hora_Monitor']) + df_trend_full['Cost_Material_Fix']
                df_trend_full['Ingressos_Calc'] = df_trend_full['Preu_Alumne'] * df_trend_full['Alumnes_Calc']
                df_trend_full['Benefici_Mes'] = df_trend_full['Ingressos_Calc'] - df_trend_full['Cost_Total']
                
                df_trend_final = df_trend_full.groupby('Mes_Any')['Benefici_Mes'].sum().reset_index()
                
                fig_ben = px.line(df_trend_final, x='Mes_Any', y='Benefici_Mes', markers=True, title="Resultat Operatiu (Mes a Mes)")
                fig_ben.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='white'), yaxis_title="EBITDA (€)", height=400)
                fig_ben.update_traces(line_color='#10B981', line_width=4, fill='tozeroy')
                st.plotly_chart(fig_ben, use_container_width=True)

        # --- DETALL ---
        st.subheader("📋 Fitxes Operatives")
        if not df_view.empty:
            for i, row in df_view.sort_values('Marge_Real', ascending=False).iterrows():
                icon = get_icon(row['Categoria']) if 'Categoria' in row else "📝"
                
                alumnes_act = row['Num_Alumnes_Final']
                
                with st.expander(f"{icon} {row['Activitat']} | {row['Marge_Real']:,.0f} €", expanded=False):
                    c_a, c_b = st.columns([1,3])
                    with c_a:
                        # Indiquem si és la dada Real (Input) o la Base (Config)
                        origen = " (Manual)" if row['Alumnes_Input'] > 0 else " (Base)"
                        st.metric("Alumnes", f"{alumnes_act:.0f}{origen}")
                        st.metric("Hores", f"{row['Hores_Fetes']:.1f} h")
                    with c_b:
                        col_in, col_out = st.columns(2)
                        col_in.write(f"**Ingressos:** {row['Ingressos_Reals']:.0f} €")
                        col_out.write(f"**Costos:** {row['Despeses']:.0f} €")
                        
                        st.write("Rendibilitat:")
                        if row['Ingressos_Reals'] > 0:
                            ratio = max(0.0, min(1.0, row['Marge_Real'] / row['Ingressos_Reals']))
                            st.progress(ratio)
                        else:
                            st.progress(0)

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
else:
    st.info("👈 Introdueixi la URL del full de càlcul per començar.")