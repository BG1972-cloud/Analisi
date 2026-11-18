import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
from fpdf import FPDF

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Laboratorio Analisi Olio - ITA", layout="wide")

# --- GESTIONE DATABASE SQLITE ---
def init_db():
    conn = sqlite3.connect("laboratorio_olio.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS campioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codice_campione TEXT UNIQUE,
            data_accettazione TEXT,
            cliente TEXT,
            azienda TEXT,
            cultivar TEXT,
            lotto TEXT,
            stato_analisi TEXT DEFAULT 'In attesa',
            acidita REAL,
            perossidi REAL,
            polifenoli REAL,
            k232 REAL,
            k270 REAL,
            deltaK REAL,
            classificazione TEXT
        )
    ''')
    conn.commit()
    conn.close()

def classifica_olio(acidita, perossidi, k232, k270, deltaK):
    # Parametri standard UE per Olio Extravergine e Vergine
    if acidita <= 0.8 and perossidi <= 20 and k232 <= 2.50 and k270 <= 0.22 and deltaK <= 0.01:
        return "Olio Extravergine di Oliva (EVO)"
    elif acidita <= 2.0 and perossidi <= 20 and k232 <= 2.60 and k270 <= 0.25 and deltaK > 0.01:
        return "Olio di Oliva Vergine"
    else:
        return "Olio Lampante (Non commestibile)"

def genera_pdf_certificato(dati):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "ITT MONTANI sez. AGRARIA - LABORATORIO CHIMICO", ln=True, align="C")
    pdf.set_font("Arial", "I", 12)
    pdf.cell(0, 10, "Certificato di Analisi Olio di Oliva", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Codice Campione: {dati['codice_campione']}   |   Data: {dati['data_accettazione']}", ln=True)
    pdf.cell(0, 8, f"Cliente: {dati['cliente']} ({dati['azienda']})", ln=True)
    pdf.cell(0, 8, f"Cultivar: {dati['cultivar']}   |   Lotto: {dati['lotto']}", ln=True)
    pdf.ln(8)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Risultati Analitici:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"- Acidita' libera (% acido oleico): {dati['acidita']} %  (Limite EVO <= 0.80%)", ln=True)
    pdf.cell(0, 8, f"- Numero di Perossidi (meq O2/kg): {dati['perossidi']}  (Limite EVO <= 20.0)", ln=True)
    pdf.cell(0, 8, f"- Polifenoli Totali (mg/kg): {dati['polifenoli']}", ln=True)
    pdf.cell(0, 8, f"- Spettrofotometria K232: {dati['k232']}  (Limite EVO <= 2.50)", ln=True)
    pdf.cell(0, 8, f"- Spettrofotometria K270: {dati['k270']}  (Limite EVO <= 0.22)", ln=True)
    pdf.cell(0, 8, f"- DELTA K: {dati['deltaK']}  (Limite EVO <= 0.01)", ln=True)
    pdf.ln(10)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"ESITO CLASSIFICAZIONE: {dati['classificazione']}", ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

# Inizializza il database all'avvio
init_db()

# --- INTERFACCIA UTENTE ---
st.title("🫒 ITT MONTANI - Gestionale Laboratorio Analisi Olio")
st.markdown("Sistema didattico per l'accettazione campioni, analisi chimiche e statistica.")

menu = st.sidebar.radio(
    "Navigazione",
    ["1. Accettazione Cliente", "2. Inserimento Analisi", "3. Certificati e Resoconti", "4. Statistiche"]
)

# --- SEZIONE 1: ACCETTAZIONE ---
if menu == "1. Accettazione Cliente":
    st.header("Registrazione Nuovo Campione")
    with st.form("form_accettazione", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            codice = st.text_input("Codice Univoco Campione (es. OLIO-2026-01)")
            cliente = st.text_input("Nome e Cognome Cliente")
            azienda = st.text_input("Azienda Agricola / Frantoio")
        with col2:
            data_acc = st.date_input("Data di conferimento", value=date.today())
            cultivar = st.selectbox("Cultivar prevalente", ["Leccino", "Piantone di Mogliano", "Piantone di Falerone", "Frantoio", "Coratina", "Moraiolo", "Carboncella", "Blend / Altro"])
            lotto = st.text_input("Identificativo Lotto / Cisterna")
        
        submitted = st.form_submit_button("Salva Campione")
        if submitted:
            if codice and cliente:
                try:
                    conn = sqlite3.connect("laboratorio_olio.db")
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO campioni (codice_campione, data_accettazione, cliente, azienda, cultivar, lotto)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (codice, str(data_acc), cliente, azienda, cultivar, lotto))
                    conn.commit()
                    conn.close()
                    st.success(f"Campione {codice} registrato correttamente!")
                except sqlite3.IntegrityError:
                    st.error("Errore: Questo codice campione esiste già.")
            else:
                st.warning("Inserisci almeno il Codice Campione e il nome del Cliente.")

# --- SEZIONE 2: INSERIMENTO ANALISI ---
elif menu == "2. Inserimento Analisi":
    st.header("Inserimento Dati di Laboratorio")
    conn = sqlite3.connect("laboratorio_olio.db")
    df_attesa = pd.read_sql_query("SELECT codice_campione, cliente, cultivar FROM campioni WHERE stato_analisi = 'In attesa'", conn)
    conn.close()

    if df_attesa.empty:
        st.info("Non ci sono campioni in attesa di analisi.")
    else:
        def reset_campi_analisi():
          st.session_state["input_acidita"] = 0.0
          st.session_state["input_perossidi"] = 0.0
          st.session_state["input_polifenoli"] = 0.0
          st.session_state["input_k232"] = 0.0
          st.session_state["input_k270"] = 0.0
          st.session_state["input_deltaK"] = 0.0

        scelta = st.selectbox("Seleziona il campione da analizzare", df_attesa["codice_campione"], on_change=reset_campi_analisi)
        dati_campione = df_attesa[df_attesa["codice_campione"] == scelta].iloc[0]
        st.write(f"**Cliente:** {dati_campione['cliente']} | **Cultivar:** {dati_campione['cultivar']}")

        with st.form("form_analisi"):
            col1, col2 = st.columns(2)
            with col1:
                acidita = st.number_input("Acidità libera (% acido oleico)", min_value=0.0, max_value=10.0, step=0.01, format="%.2f", key="input_acidita")
                perossidi = st.number_input("Numero di perossidi (meq O2/kg)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", key="input_perossidi")
                polifenoli = st.number_input("Polifenoli totali (mg/kg)", min_value=0.0, max_value=2000.0, step=1.0, key="input_polifenoli")
            with col2:
                k232 = st.number_input("Assorbanza K232", min_value=0.0, max_value=5.0, step=0.01, format="%.2f", key="input_k232")
                k270 = st.number_input("Assorbanza K270", min_value=0.0, max_value=2.0, step=0.01, format="%.2f", key="input_k270")
                deltaK = st.number_input("DELTA K", min_value=0.0, max_value=2.0, step=0.01, format="%.2f", key="input_deltaK")
            
            salva_analisi = st.form_submit_button("Registra Risultati Analisi")
            if salva_analisi:
                esito = classifica_olio(acidita, perossidi, k232, k270, deltaK)
                conn = sqlite3.connect("laboratorio_olio.db")
                c = conn.cursor()
                c.execute('''
                    UPDATE campioni 
                    SET acidita=?, perossidi=?, polifenoli=?, k232=?, k270=?, deltaK=?, classificazione=?, stato_analisi='Completato'
                    WHERE codice_campione=?
                ''', (acidita, perossidi, polifenoli, k232, k270, deltaK, esito, scelta))
                conn.commit()
                conn.close()
                st.success(f"Analisi salvata! Classificazione automatica: **{esito}**")


# --- SEZIONE 3: MODIFICA ANALISI ---
elif menu == "3. Modifica Analisi":
    st.header("Modifica Dati di Laboratorio")
    conn = sqlite3.connect("laboratorio_olio.db")
    df_attesa = pd.read_sql_query("SELECT codice_campione, cliente, cultivar FROM campioni WHERE stato_analisi = 'In attesa'", conn)
    conn.close()

    if df_attesa.empty:
        st.info("Non ci sono campioni in attesa di analisi.")
    
        


# --- SEZIONE 4: CERTIFICATI E RESOCONTI ---
elif menu == "4. Certificati e Resoconti":
    st.header("Archivio Campioni e Stampa Certificati")
    conn = sqlite3.connect("laboratorio_olio.db")
    df_tutti = pd.read_sql_query("SELECT * FROM campioni", conn)
    conn.close()

    st.subheader("Resoconto Generale Raccolta Dati")
    st.dataframe(df_tutti, use_container_width=True)

    # Pulsante esportazione CSV per Excel
    csv = df_tutti.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Scarica Resoconto Completo (CSV / Excel)",
        data=csv,
        file_name="resoconto_laboratorio_olio.csv",
        mime="text/csv"
    )

    st.divider()
    st.subheader("Stampa Certificato Singolo Campione")
    df_completati = df_tutti[df_tutti["stato_analisi"] == "Completato"]
    if df_completati.empty:
        st.info("Nessuna analisi completata disponibile per la stampa.")
    else:
        cod_stampa = st.selectbox("Scegli il campione per generare il PDF", df_completati["codice_campione"])
        riga_dati = df_completati[df_completati["codice_campione"] == cod_stampa].iloc[0]
        pdf_bytes = genera_pdf_certificato(riga_dati)
        st.download_button(
            label="🖨️ Scarica Certificato PDF",
            data=pdf_bytes,
            file_name=f"Certificato_{cod_stampa}.pdf",
            mime="application/pdf"
        )

# --- SEZIONE 5: STATISTICHE ---
elif menu == "5. Statistiche":
    st.header("Analisi Statistica dei Campioni")
    conn = sqlite3.connect("laboratorio_olio.db")
    df_stat = pd.read_sql_query("SELECT * FROM campioni WHERE stato_analisi = 'Completato'", conn)
    conn.close()

    if len(df_stat) < 2:
        st.warning("Inserisci almeno 2 campioni analizzati per visualizzare le statistiche.")
    else:
        st.subheader("Indici Statistici Descrittivi")
        parametri = ["acidita", "perossidi", "polifenoli", "k232", "k270", "deltaK"]
        st.dataframe(df_stat[parametri].describe().round(2), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Distribuzione Classificazione")
            conteggio_classi = df_stat["classificazione"].value_counts()
            st.bar_chart(conteggio_classi)
        with col2:
            st.subheader("Acidità Media per Cultivar")
            media_cultivar = df_stat.groupby("cultivar")["acidita"].mean()
            st.bar_chart(media_cultivar)
