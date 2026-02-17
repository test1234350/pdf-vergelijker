import streamlit as st
import fitz
import pandas as pd
import io
import os
import re  # CRUCIAAL: Voegt de zoekfunctionaliteit toe
import difflib
from pdf2docx import Converter

st.set_page_config(page_title="Bedrijfs PDF Tool v3", layout="wide")

# Navigatie
st.sidebar.title("🛠️ PDF Gereedschap")
keuze = st.sidebar.radio("Wat wilt u doen?", ["Artikelzoeker & Korting", "PDF Vergelijker (Rood)", "PDF naar Word"])

# --- FUNCTIE 1: ARTIKELZOEKER & KORTING ---
if keuze == "Artikelzoeker & Korting":
    st.title("📦 Slimme Artikel & Korting Zoeker")
    st.write("Zoekt Art. Nr. en Kortingsgroep in Excel en haalt de korting uit de PDF.")
    
    EXCEL_FILE = "artikelen.xlsx" 

    if not os.path.exists(EXCEL_FILE):
        st.error(f"Bestand '{EXCEL_FILE}' niet gevonden in GitHub.")
    else:
        @st.cache_data
        def load_db(file):
            df = pd.read_excel(file)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        
        df_db = load_db(EXCEL_FILE)
        pdf_file = st.file_uploader("Upload PDF (bijv. Factuur)", type="pdf")

        if pdf_file and st.button("Start Analyse"):
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            gevonden_items = []

            # Doorloop elke pagina van de PDF
            for page in doc:
                text = page.get_text("text")
                
                for _, row in df_db.iterrows():
                    # We gebruiken Omschrijving 1 voor de match
                    omschrijving = str(row.get('Omschrijving 1', '')).strip()
                    if len(omschrijving) < 5: continue
                    
                    # Zoek de positie van de omschrijving in de PDF tekst
                    start_pos = text.lower().find(omschrijving.lower())
                    
                    if start_pos != -1:
                        # Pak de tekst die direct na de omschrijving komt (ongeveer 100 tekens)
                        # Hier staat meestal de prijs en korting
                        context = text[start_pos:start_pos + 150].replace('\n', ' ')
                        
                        # Zoek naar een percentage (bijv: 25% of 25,00%)
                        korting_match = re.search(r'(\d+[\d,.]*)\s*%', context)
                        gevonden_korting = korting_match.group(0) if korting_match else "Niet gevonden"

                        gevonden_items.append({
                            "Art. Nr.": row.get('Art. Nr.', 'N/B'),
                            "Omschrijving": omschrijving,
                            "Kortingsgroep": row.get('Kortingsgroep', 'N/B'),
                            "Korting uit PDF": gevonden_korting
                        })

            if gevonden_items:
                res_df = pd.DataFrame(gevonden_items).drop_duplicates(subset=["Art. Nr."])
                st.dataframe(res_df)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    res_df.to_excel(writer, index=False)
                st.download_button("Download Excel Resultaat", output.getvalue(), "artikel_kortingen.xlsx")
            else:
                st.warning("Geen matches gevonden tussen de PDF en de Excel-database.")

# --- FUNCTIE 2: VERGELIJKER ---
elif keuze == "PDF Vergelijker (Rood)":
    st.title("🔍 PDF Vergelijker")
    col1, col2 = st.columns(2)
    with col1: old_file = st.file_uploader("Oude PDF", type="pdf")
    with col2: new_file = st.file_uploader("Nieuwe PDF", type="pdf")
    if old_file and new_file and st.button("Vergelijk"):
        doc1 = fitz.open(stream=old_file.read(), filetype="pdf")
        doc2 = fitz.open(stream=new_file.read(), filetype="pdf")
        pool = set(l.strip() for p in doc1 for l in p.get_text().splitlines() if len(l.strip()) > 3)
        for page in doc2:
            marked = set()
            for line in page.get_text().splitlines():
                clean = line.strip()
                if clean and clean not in pool and clean not in marked:
                    for rect in page.search_for(clean):
                        annot = page.add_highlight_annot(rect)
                        annot.set_colors(stroke=(1, 0, 0))
                        annot.update()
                    marked.add(clean)
        st.download_button("Download Resultaat", doc2.write(), "verschillen.pdf")

# --- FUNCTIE 3: WORD CONVERTER ---
elif keuze == "PDF naar Word":
    st.title("📝 PDF naar Word Converter")
    word_file = st.file_uploader("Upload PDF", type="pdf")
    if word_file and st.button("Converteer"):
        with open("temp.pdf", "wb") as f: f.write(word_file.getbuffer())
        cv = Converter("temp.pdf")
        cv.convert("temp.docx")
        cv.close()
        with open("temp.docx", "rb") as f:
            st.download_button("Download Word", f, "document.docx")
        os.remove("temp.pdf")
        os.remove("temp.docx")
