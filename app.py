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

# --- FUNCTIE 1: DEEP SCAN ARTIKELZOEKER ---
if keuze == "Artikelzoeker & Korting":
    st.title("🔬 Deep Scan: PDF naar Excel Matcher")
    st.info("Scant Art. Nr., Omschrijving 1/2 en Zoeknaam voor maximale match.")
    
    EXCEL_FILE = "artikelen.xlsx" 

    if not os.path.exists(EXCEL_FILE):
        st.error(f"Bestand '{EXCEL_FILE}' niet gevonden.")
    else:
        @st.cache_data
        def load_db(file):
            df = pd.read_excel(file)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        
        df_db = load_db(EXCEL_FILE)
        pdf_file = st.file_uploader("Upload PDF", type="pdf")

        if pdf_file and st.button("Start Deep Scan"):
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            
            # STAP 1: FIX - Haal alle tekst op en voeg samen tot één grote string
            pdf_pages_text = []
            for page in doc:
                page_text = page.get_text("text")
                if page_text:
                    pdf_pages_text.append(page_text)
            
            # Maak de tekst 'schoon' (geen enters, alles kleine letters)
            full_text_raw = " ".join(pdf_pages_text)
            full_text_clean = " ".join(full_text_raw.split()).lower()

            gevonden_items = []

            # STAP 2: Doorloop de database en match op meerdere velden
            for _, row in df_db.iterrows():
                # Haal waarden op en zet ze om naar kleine letters voor matching
                art_nr = str(row.get('Art. Nr.', '')).strip().lower()
                oms1 = str(row.get('Omschrijving 1', '')).strip().lower()
                oms2 = str(row.get('Omschrijving 2', '')).strip().lower()
                zoeknaam = str(row.get('Zoeknaam', '')).strip().lower()

                match_found = False
                match_term = ""

                # Zoek op Art. Nr. (minimaal 3 tekens), dan Omschrijvingen, dan Zoeknaam
                if art_nr and len(art_nr) >= 3 and art_nr in full_text_clean:
                    match_found, match_term = True, art_nr
                elif oms1 and len(oms1) > 4 and oms1 in full_text_clean:
                    match_found, match_term = True, oms1
                elif oms2 and len(oms2) > 4 and oms2 in full_text_clean:
                    match_found, match_term = True, oms2
                elif zoeknaam and len(zoeknaam) > 3 and zoeknaam in full_text_clean:
                    match_found, match_term = True, zoeknaam

                if match_found:
                    # STAP 3: Zoek korting in de buurt van de gevonden term
                    start_pos = full_text_clean.find(match_term)
                    # We kijken 150 tekens verder voor de korting
                    context = full_text_clean[start_pos:start_pos + 150]
                    
                    # Zoek naar percentage (bijv 25% of 25,00%)
                    korting_match = re.search(r'(\d+[\d,.]*)\s*%', context)
                    gevonden_korting = korting_match.group(0) if korting_match else "N/B"

                    gevonden_items.append({
                        "Art. Nr.": row.get('Art. Nr.', 'N/B'),
                        "Omschrijving 1": row.get('Omschrijving 1', 'N/B'),
                        "Kortingsgroep": row.get('Kortingsgroep', 'N/B'),
                        "Korting uit PDF": gevonden_korting
                    })

            if gevonden_items:
                res_df = pd.DataFrame(gevonden_items).drop_duplicates(subset=["Art. Nr."])
                st.write(f"✅ Succes: {len(res_df)} artikelen gevonden.")
                st.dataframe(res_df)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    res_df.to_excel(writer, index=False)
                st.download_button("Download Resultaat Excel", output.getvalue(), "deep_scan_resultaat.xlsx")
            else:
                st.warning("Geen matches gevonden. Controleer of de PDF doorzoekbaar is.")


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

