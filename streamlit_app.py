import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import io

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Dashboard Extraescolars", layout="wide", page_icon="🎓")

# --- ESTILS CSS (PREMIUM & NET) ---
st.markdown("""
<style>
    /* Neteja general */
    div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
    
    /* Targetes KPI */
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.05);
        padding: 15px; 
        border-radius: 15px; 
        border: 1px solid rgba(128, 128, 128, 0.1);
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    
    /* Tabs elegants (Scrollable en mòbil) */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px; 
        overflow-x: auto; 
        white-space: nowrap; 
        padding-bottom: 5px; /* Espai per scroll bar invisible */
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 20px;
        padding: 6px 18px;
        border: 1px solid rgba(128, 128, 128, 0.1);
        font-weight: 500;
    }
    
    /* Badges */
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; margin-right: 5px; color: white;}
    .badge-star { background-color: #059669; }
    .badge-warn { background-color: #D97706; }
    .badge-danger { background-color: #DC2626; }
    .badge-seed { background-color: #4B5563; }

</style>
""", unsafe_allow_html=True)

# --- CAPÇALERA ---
c_head_1, c_head_2 = st.columns([3,1])
with c_head_1: st.title("Dashboard extraescolars - Marc Marlés")
with c_head_2: st.caption("v27.0 Tabbed Organization")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Gestió")
url_master = st.sidebar.text_input("URL Master Excel")
if st.sidebar.button("🔄 Actualitzar", use_container_width=True):
    st.cache_data.clear()

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIONS ---
def netejar_numero(val):
    try:
        if isinstance(val, (int, float)): return float(val)
        if pd.isna(val) or str(val).strip() == '': return 0.0
        s = str(val).strip().replace('€', '')
        if ',' in s: s = s.replace('.', '').replace(',', '.')
        return float(s)
    except: return 0.0

def get_icon(categoria):
    cat = str(categoria).upper().strip()
    return "⚽" if "ESPORTS" in cat else "🇬🇧" if "IDIOMES" in cat else "🎨" if "LUDIC" in cat else "🤖" if "TECNOLOGIC" in cat else "🎭" if "ARTISTIC" in cat else "📝"

def get_smart_tags(row):
    tags = []
    marge_pct = (row['Marge_Real'] / row['Ingressos_Reals'] * 100) if row['Ingressos_Reals'] > 0 else 0
    alumnes = row['Num_Alumnes_Final']
    if marge_pct < 0: tags.append('<span class="badge badge-danger">🔻 Dèficit</span>')
    elif marge_pct < 15: tags.append(f'<span class="badge badge-warn">🟠 Ajustat ({marge_pct:.0f}%)</span>')
    elif marge_pct > 40 and alumnes > 8: tags.append('<span class="badge badge-star">💎 Premium</span>')
    if alumnes > 0 and alumnes < 6: tags.append('<span class="badge badge-seed">🌱 Potencial</span>')
    return " ".join(tags)

# --- MOTOR DADES ---
def carregar_dades_smart(url):
    df_conf = None
    df_reg = None
    for i in range(5):
        try:
            df_temp = conn.read(spreadsheet=url, worksheet=i)
            cols = list(df_temp.columns)
            if 'Preu_Alumne' in cols and ('Num_Alumnes' in cols or 'Alumnes' in cols):
                df_conf = df_temp
                col_alumnes = 'Num_Alumnes' if 'Num_Alumnes' in df_conf.columns else 'Alumnes'
                df_conf = df_conf.rename(columns={col_alumnes: 'Num_Alumnes_Base'})
                for c in ['Preu_Alumne', 'Num_Alumnes_Base', 'Cost_Material_Fix', 'Preu_Hora_Monitor']:
                    if c in df_conf.columns: df_conf[c] = df_conf[c].apply(netejar_numero)
                df_conf['Activitat_Join'] = df_conf['Activitat'].astype(str).str.strip().str.upper()
            elif ('Hores_Fetes' in cols or 'Hores' in cols) and 'Data' in cols:
                df_reg = df_temp
                if 'Hores' in df_reg.columns and 'Hores_Fetes' not in df_reg.columns:
                    df_reg = df_reg.rename(columns={'Hores': 'Hores_Fetes'})
                df_reg['Hores_Fetes'] = df_reg['Hores_Fetes'].apply(netejar_numero)
                col_var_alumnes = None
                for c in df_reg.columns:
                    if 'ALUMNE' in c.upper() and ('MES' in c.upper() or 'REAL' in c.upper() or 'ACTUAL' in c.upper()):
                        col_var_alumnes = c
                        break
                if col_var_alumnes:
                    df_reg['Alumnes_Input'] = df_reg[col_var_alumnes].apply(netejar_numero)
                else: df_reg['Alumnes_Input'] = pd.NA
                df_reg['Data_DT'] = pd.to_datetime(df_reg['Data'], dayfirst=True, errors='coerce')
                df_reg['Mes_Any'] = df_reg['Data_DT'].dt.strftime('%Y-%m')
                df_reg['Activitat_Join'] = df_reg['Activitat'].astype(str).str.strip().str.upper()
        except: pass
        if df_conf is not None and df_reg is not None: break
    return df_conf, df_reg

# --- APP ---
if url_master:
    try:
        df_config, df_registre = carregar_dades_smart(url_master)
        if df_config is None: st.stop()

        # PREPARACIÓ
        df_final = df_config.copy()
        if 'Num_Alumnes_Base' not in df_final.columns: df_final['Num_Alumnes_Base'] = 0
        total_tresoreria_acumulada = 0
        df_historic_global = pd.DataFrame()

        if df_registre is not None:
            df_registre = df_registre.sort_values('Data_DT', ascending=True)
            df_registre['Alumnes_Reals'] = df_registre.groupby('Activitat_Join')['Alumnes_Input'].ffill()
            df_registre = pd.merge(df_registre, df_config[['Activitat_Join', 'Num_Alumnes_Base']], on='Activitat_Join', how='left')
            df_registre['Alumnes_Reals'] = df_registre['Alumnes_Reals'].fillna(df_registre['Num_Alumnes_Base'])
            
            df_hist_calc = pd.merge(df_registre, df_config[['Activitat_Join', 'Preu_Alumne', 'Preu_Hora_Monitor', 'Cost_Material_Fix']], on='Activitat_Join', how='left')
            df_hist_calc['Cost'] = (df_hist_calc['Hores_Fetes'] * df_hist_calc['Preu_Hora_Monitor']) + df_hist_calc['Cost_Material_Fix']
            df_hist_calc['Ingres'] = df_hist_calc['Preu_Alumne'] * df_hist_calc['Alumnes_Reals']
            df_hist_calc['Ben'] = df_hist_calc['Ingres'] - df_hist_calc['Cost']
            total_tresoreria_acumulada = df_hist_calc['Ben'].sum()
            df_historic_global = df_hist_calc.groupby('Mes_Any')['Ben'].sum().reset_index()

        # CONTROLS
        st.divider()
        c1, c2, c3 = st.columns([1, 1.5, 2.5])
        
        alumnes_mes_anterior = {}
        df_view = df_final.copy()
        
        if df_registre is not None:
            mesos = sorted(df_registre['Mes_Any'].dropna().unique(), reverse=True)
            if len(mesos) > 0:
                with c1: mes = st.selectbox("📅 Període:", mesos)
                
                idx = mesos.index(mes)
                if idx + 1 < len(mesos):
                    prev_m = mesos[idx+1]
                    df_prev = df_registre[df_registre['Mes_Any'] == prev_m]
                    alumnes_mes_anterior = df_prev.groupby('Activitat_Join')['Alumnes_Reals'].max().to_dict()

                df_reg_mes = df_registre[df_registre['Mes_Any'] == mes].copy()
                df_agrupat = df_reg_mes.groupby('Activitat_Join').agg({'Hores_Fetes':'sum', 'Alumnes_Reals':'max'}).reset_index()
                df_final = pd.merge(df_config, df_agrupat, on='Activitat_Join', how='left')
                df_final['Hores_Fetes'] = df_final['Hores_Fetes'].fillna(0)
                df_final['Num_Alumnes_Final'] = df_final['Alumnes_Reals'].fillna(df_final['Num_Alumnes_Base'])
            else:
                df_final['Hores_Fetes'] = 0
                df_final['Num_Alumnes_Final'] = df_final['Num_Alumnes_Base']
        else:
            df_final['Hores_Fetes'] = 0
            df_final['Num_Alumnes_Final'] = df_final['Num_Alumnes_Base']

        with c2:
            cats = ["TOTS"] + sorted(list(df_config['Categoria'].unique())) if 'Categoria' in df_config else ["TOTS"]
            cat_filter = st.selectbox("Departament:", cats)
        
        with c3:
            search_term = st.text_input("🔍 Buscar Activitat", placeholder="Ex: Futbol...")

        df_final['Ingressos_Reals'] = df_final['Preu_Alumne'] * df_final['Num_Alumnes_Final']
        df_final['Cost_Nomina'] = df_final['Hores_Fetes'] * df_final['Preu_Hora_Monitor']
        despesa_extra = df_final['Cost_Material_Fix'] if 'Cost_Material_Fix' in df_final else 0
        df_final['Despeses'] = df_final['Cost_Nomina'] + despesa_extra
        df_final['Marge_Real'] = df_final['Ingressos_Reals'] - df_final['Despeses']
        df_final['Benefici_Unitari'] = df_final.apply(lambda x: x['Marge_Real'] / x['Num_Alumnes_Final'] if x['Num_Alumnes_Final'] > 0 else 0, axis=1)

        # FILTRES
        df_view = df_final.copy()
        if cat_filter != "TOTS" and 'Categoria' in df_view.columns:
            df_view = df_view[df_view['Categoria'] == cat_filter]
        
        if search_term:
            df_view = df_view[df_view['Activitat'].str.contains(search_term, case=False, na=False)]

        # EXPORT
        with st.sidebar:
            st.divider()
            st.subheader("📥 Dades")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_view.to_excel(writer, sheet_name='Informe', index=False)
            st.download_button("Baixar Excel", data=buffer, file_name=f"Report_{mes}.xlsx", mime="application/vnd.ms-excel", use_container_width=True)

        # KPIS
        tot_ing = df_view['Ingressos_Reals'].sum()
        tot_ben = df_view['Marge_Real'].sum()
        tot_stu = df_view['Num_Alumnes_Final'].sum()
        marge_pct = (tot_ben / tot_ing * 100) if tot_ing > 0 else 0
        
        tresoreria_show = total_tresoreria_acumulada
        if cat_filter != "TOTS" and df_registre is not None:
             df_hist_filt = pd.merge(df_registre, df_config[['Activitat_Join', 'Categoria']], on='Activitat_Join', how='left')
             df_hist_filt = df_hist_filt[df_hist_filt['Categoria'] == cat_filter]
             df_h2 = pd.merge(df_hist_filt, df_config[['Activitat_Join', 'Preu_Alumne', 'Preu_Hora_Monitor', 'Cost_Material_Fix']], on='Activitat_Join', how='left')
             tresoreria_show = ((df_h2['Preu_Alumne'] * df_h2['Alumnes_Reals']) - ((df_h2['Hores_Fetes'] * df_h2['Preu_Hora_Monitor']) + df_h2['Cost_Material_Fix'])).sum()

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("👥 Alumnes", f"{tot_stu:.0f}")
        k2.metric("💶 Facturació", f"{tot_ing:,.0f} €")
        k3.metric("📊 Marge", f"{marge_pct:.1f} %")
        k4.metric("💰 EBITDA", f"{tot_ben:,.0f} €")
        k5.metric("🏦 Tresoreria", f"{tresoreria_show:,.0f} €", help="Total Històric")

        st.markdown("---")

        # --- ESTRUCTURA DE PESTANYES COMPLETA ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Rànquing", 
            "🍰 Distribució", 
            "🎯 Matriu BCG", 
            "📈 Evolució", 
            "📋 Fitxes Detall"
        ])
        
        with tab1: # RÀNQUING
            if not df_view.empty:
                df_sorted = df_view.sort_values('Marge_Real', ascending=True)
                fig = px.bar(df_sorted, x='Marge_Real', y='Activitat', orientation='h', text='Marge_Real', 
                             color='Marge_Real', color_continuous_scale=['#EF4444', '#10B981'])
                fig.update_traces(texttemplate='%{text:.0f} €', textposition='outside')
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                  xaxis_title=None, yaxis_title=None, xaxis=dict(showgrid=False),
                                  height=max(400, len(df_view)*35))
                st.plotly_chart(fig, use_container_width=True)

        with tab2: # DONUT (DISTRIBUCIÓ)
            if not df_view.empty and 'Categoria' in df_view.columns:
                fig_pie = px.pie(df_view, values='Ingressos_Reals', names='Categoria', hole=0.6,
                                 color_discrete_sequence=px.colors.qualitative.Prism)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Necessites tenir la columna 'Categoria' a l'Excel per veure aquest gràfic.")

        with tab3: # MATRIU
            if not df_view.empty:
                fig_m = px.scatter(df_view, x="Num_Alumnes_Final", y="Marge_Real", color="Categoria" if "Categoria" in df_view else None,
                                   size="Ingressos_Reals", hover_name="Activitat", text="Activitat")
                fig_m.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_m.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500, showlegend=False,
                                    xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', title="Alumnes"),
                                    yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', title="Benefici (€)"))
                st.plotly_chart(fig_m, use_container_width=True)

        with tab4: # EVOLUCIÓ
            if not df_historic_global.empty:
                fig_ben = go.Figure()
                fig_ben.add_trace(go.Scatter(x=df_historic_global['Mes_Any'], y=df_historic_global['Ben'], 
                                             mode='lines+markers', name='Real', 
                                             line=dict(color='#10B981', width=4, shape='spline')))
                fig_ben.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                      yaxis_title="Benefici (€)", height=400,
                                      xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.1)'))
                st.plotly_chart(fig_ben, use_container_width=True)
            else:
                st.info("Falten dades històriques.")

        with tab5: # FITXES
            if not df_view.empty:
                for i, row in df_view.sort_values('Marge_Real', ascending=False).iterrows():
                    icon = get_icon(row['Categoria']) if 'Categoria' in row else "📝"
                    alumnes = row['Num_Alumnes_Final']
                    tags_html = get_smart_tags(row)
                    
                    with st.expander(f"{icon} {row['Activitat']} | {row['Marge_Real']:,.0f} €", expanded=False):
                        st.markdown(tags_html, unsafe_allow_html=True)
                        st.write("")
                        c_a, c_b = st.columns(2)
                        with c_a:
                            st.write(f"**Alumnes:** {alumnes:.0f}")
                            st.write(f"**Unitari:** {row['Benefici_Unitari']:.1f} €")
                        with c_b:
                            st.write(f"**Ing:** {row['Ingressos_Reals']:.0f} €")
                            st.write(f"**Cost:** {row['Despeses']:.0f} €")
                        
                        ratio = max(0.0, min(1.0, row['Marge_Real']/row['Ingressos_Reals'])) if row['Ingressos_Reals'] > 0 else 0
                        st.progress(ratio)

    except Exception as e:
        st.error(f"⚠️: {e}")
else:
    st.info("👈 Connecta l'Excel.")