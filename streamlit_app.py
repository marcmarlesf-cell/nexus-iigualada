import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import io
import google.generativeai as genai
from fpdf import FPDF

# --- CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Gestió Extraescolars", layout="wide", page_icon="🎓")

# --- ESTILS CSS (IPHONE & LIGHT MODE) ---
st.markdown("""
<style>
    div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.05);
        padding: 15px; border-radius: 15px; border: 1px solid rgba(128, 128, 128, 0.1);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; overflow-x: auto; white-space: nowrap; padding-bottom: 5px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 20px; padding: 6px 18px; border: 1px solid rgba(128, 128, 128, 0.1); font-weight: 500;
    }
    .status-dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
</style>
""", unsafe_allow_html=True)

# --- CAPÇALERA ---
c_head_1, c_head_2 = st.columns([3,1])
with c_head_1: st.title("Dashboard extraescolars - Marc Marlés")
with c_head_2: st.caption("v30.0 Final ERP Solution")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuració")
url_master = st.sidebar.text_input("URL Master Excel", type="password")
api_key = st.sidebar.text_input("Google API Key", type="password", help="Per a l'assistent d'IA")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIONS AUXILIARS ---
def netejar_num(val):
    try:
        if isinstance(val, (int, float)): return float(val)
        if pd.isna(val) or str(val).strip() == '': return 0.0
        s = str(val).strip().replace('€', '').replace(',', '.')
        return float(s)
    except: return 0.0

def generar_informe_pdf(data_resum, mes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"INFORME EXTRAESCOLARS - {mes}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    for k, v in data_resum.items():
        pdf.cell(200, 10, txt=f"{k}: {v}", ln=True)
    return pdf.output(dest="S").encode("latin-1")

# --- MOTOR DE DADES ---
def fetch_data(url):
    try:
        # Carreguem les 4 pestanyes noves
        df_act = conn.read(spreadsheet=url, worksheet=0) # ACTIVITATS
        df_alu = conn.read(spreadsheet=url, worksheet=1) # ALUMNES
        df_mon = conn.read(spreadsheet=url, worksheet=2) # MONITORS
        df_reg = conn.read(spreadsheet=url, worksheet=3) # REGISTRE_HORES
        return df_act, df_alu, df_mon, df_reg
    except: return None, None, None, None

# --- APP PRINCIPAL ---
if url_master:
    df_act_orig, df_alu_orig, df_mon_orig, df_reg_orig = fetch_data(url_master)
    
    if df_act_orig is not None:
        # PESTANYES DE L'APP
        t_dash, t_gestio, t_ia = st.tabs(["📊 Dashboard Directiu", "📝 Gestió (Altes/Baixes/Hores)", "🤖 Assistent IA"])

        # --- PROCESSAMENT DE DADES ---
        # 1. Comptar alumnes actius per activitat
        df_alu_actius = df_alu_orig[df_alu_orig['Estat'].str.upper() == 'ACTIU'] if not df_alu_orig.empty else pd.DataFrame()
        count_alu = df_alu_actius.groupby('Activitat').size().reset_index(name='Num_Alumnes_Actius') if not df_alu_actius.empty else pd.DataFrame(columns=['Activitat', 'Num_Alumnes_Actius'])

        # 2. Càlcul financer per activitat (Mes actual)
        df_resum = df_act_orig.copy()
        for c in ['Preu_Quota', 'Cost_Material_Fix']:
            if c in df_resum.columns: df_resum[c] = df_resum[c].apply(netejar_num)
        
        df_resum = pd.merge(df_resum, count_alu, on='Activitat', how='left').fillna(0)
        
        # Integrar hores i preu monitor
        if not df_reg_orig.empty:
            # Seleccionem el mes més recent per defecte
            mesos = sorted(df_reg_orig['Mes'].unique(), reverse=True)
            mes_sel = st.sidebar.selectbox("Mes de l'informe:", mesos) if mesos else "Sense dades"
            df_reg_mes = df_reg_orig[df_reg_orig['Mes'] == mes_sel]
            df_hores = df_reg_mes.groupby('Activitat')['Hores_Fetes'].sum().reset_index()
            df_resum = pd.merge(df_resum, df_hores, on='Activitat', how='left').fillna(0)
        else:
            mes_sel = "N/A"
            df_resum['Hores_Fetes'] = 0

        df_mon_preu = df_mon_orig.groupby('Activitat')['Preu_Hora'].mean().reset_index() if not df_mon_orig.empty else pd.DataFrame(columns=['Activitat', 'Preu_Hora'])
        df_resum = pd.merge(df_resum, df_mon_preu, on='Activitat', how='left').fillna(0)

        # MÈTRIQUES FINALS
        df_resum['Ingressos'] = df_resum['Preu_Quota'] * df_resum['Num_Alumnes_Actius']
        df_resum['Costos'] = (df_resum['Hores_Fetes'] * df_resum['Preu_Hora']) + (df_resum['Cost_Material_Fix'] * df_resum['Num_Alumnes_Actius'])
        df_resum['Marge'] = df_resum['Ingressos'] - df_resum['Costos']

        # --- TAB: DASHBOARD DIRECTIU ---
        with t_dash:
            m1, m2, m3, m4 = st.columns(4)
            tot_alu = df_resum['Num_Alumnes_Actius'].sum()
            tot_ing = df_resum['Ingressos'].sum()
            tot_mar = df_resum['Marge'].sum()
            
            m1.metric("👥 Alumnes Actius", f"{tot_alu:.0f}")
            m2.metric("💶 Facturació Teòrica", f"{tot_ing:,.0f} €")
            m3.metric("💰 EBITDA Mensual", f"{tot_mar:,.0f} €")
            m4.metric("📊 % Marge Global", f"{(tot_mar/tot_ing*100 if tot_ing > 0 else 0):.1f}%")

            st.divider()
            
            # SEMÀFOR D'EFICIÈNCIA
            st.subheader("🚦 Estat de les Activitats")
            for _, r in df_resum.iterrows():
                m_pct = (r['Marge'] / r['Ingressos'] * 100) if r['Ingressos'] > 0 else -100
                color = "#10B981" if m_pct > 25 else "#F59E0B" if m_pct > 0 else "#EF4444"
                label = "RENDIBLE" if m_pct > 25 else "ALTA ATENCIÓ" if m_pct > 0 else "DÈFICIT"
                
                with st.expander(f"{r['Activitat']} | {r['Marge']:.0f} €"):
                    st.markdown(f"<span class='status-dot' style='background-color:{color};'></span> **{label}** (Marge: {m_pct:.1f}%)", unsafe_allow_html=True)
                    st.write(f"Alumnes: {r['Num_Alumnes_Actius']:.0f} | Ingressos: {r['Ingressos']:.0f}€ | Costos: {r['Costos']:.0f}€")

            # BOTÓ PDF
            st.sidebar.divider()
            if st.sidebar.button("📄 Generar Informe PDF"):
                resum_data = {
                    "Mes": mes_sel,
                    "Total Alumnes": f"{tot_alu:.0f}",
                    "Facturació": f"{tot_ing:,.0f} €",
                    "Benefici Net": f"{tot_mar:,.0f} €"
                }
                pdf_bytes = generar_informe_pdf(resum_data, mes_sel)
                st.sidebar.download_button("⬇️ Baixar PDF", data=pdf_bytes, file_name=f"Informe_{mes_sel}.pdf")

        # --- TAB: GESTIÓ (ALTES/BAIXES) ---
        with t_gestio:
            st.info("Podeu fer altes o baixes directament aquí. No cal obrir l'Excel.")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("👥 Llistat d'Alumnes")
                edited_alu = st.data_editor(df_alu_orig, num_rows="dynamic", use_container_width=True, key="edit_alu")
                if st.button("💾 Guardar Canvis Alumnes"):
                    conn.update(worksheet=1, data=edited_alu)
                    st.success("Dades d'alumnes actualitzades!"); st.cache_data.clear(); st.rerun()

            with col_b:
                st.subheader("⏱️ Registre d'Hores Monitors")
                edited_reg = st.data_editor(df_reg_orig, num_rows="dynamic", use_container_width=True, key="edit_reg")
                if st.button("💾 Guardar Hores"):
                    conn.update(worksheet=3, data=edited_reg)
                    st.success("Hores guardades!"); st.cache_data.clear(); st.rerun()

            st.divider()
            st.subheader("⚙️ Configuració d'Activitats i Monitors")
            col_c, col_d = st.columns(2)
            with col_c:
                edited_act = st.data_editor(df_act_orig, num_rows="dynamic", use_container_width=True)
                if st.button("💾 Guardar Activitats"):
                    conn.update(worksheet=0, data=edited_act); st.cache_data.clear(); st.rerun()
            with col_d:
                edited_mon = st.data_editor(df_mon_orig, num_rows="dynamic", use_container_width=True)
                if st.button("💾 Guardar Monitors"):
                    conn.update(worksheet=2, data=edited_mon); st.cache_data.clear(); st.rerun()

        # --- TAB: ASSISTENT IA ---
        with t_ia:
            st.subheader("🤖 Assistent Executiu")
            ordre = st.text_input("Com puc ajudar-vos?", placeholder="Ex: 'Quina és l'activitat que perd més diners?'")
            if ordre and api_key:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                # Enviem el context de les dades a l'IA
                context = df_resum[['Activitat', 'Num_Alumnes_Actius', 'Marge']].to_string()
                prompt = f"Actua com un consultor financer escolar. Basat en aquestes dades: {context}. Respon a l'usuari en català: {ordre}"
                response = model.generate_content(prompt)
                st.write(response.text)

    else:
        st.error("No s'ha pogut llegir l'Excel. Verifiqueu les pestanyes i l'URL.")
else:
    st.info("👈 Connecteu el vostre Excel a la barra lateral.")