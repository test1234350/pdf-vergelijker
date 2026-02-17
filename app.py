import streamlit as st
import fitz
import pandas as pd
import io
import os
import difflib
from pdf2docx import Converter

st.set_page_config(page_title="Bedrijfs PDF Tool v2", layout="wide")

# Navigatie
st.sidebar.title("🛠️ PDF Gereedschap")
keuze = st.sidebar.radio("Wat wilt u doen?", ["Artikelzoeker (Excel)", "PDF Vergelijker (Rood)", "PDF naar Word"])

# --- FUNCTIE 1: ARTIKELZOEKER ---
if keuze == "Artikelzoeker (Excel)":
    st.title("📦 Artikelzoeker & Excel Generator")
    
    EXCEL_FILE = "artikelen.xlsx" 

    if not os.path.exists(EXCEL_FILE):
        st.error(f"Fout: Bestand '{EXCEL_FILE}' niet gevonden.")
    else:
        @st.cache_data
        def load_db(file):
            df = pd.read_excel(file)
            # Maak kolomnamen schoon (spaties weg)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        
        df_db = load_db(EXCEL_FILE)

        pdf_file = st.file_uploader("Upload PDF om artikelen te matchen", type="pdf")

        if pdf_file and st.button("Start Analyse"):
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            full_pdf_text = " ".join([page.get_text() for page in doc]).replace("\n", " ").lower()
            
            gevonden_items = []
            
            # We zoeken nu in Omschrijving 1 EN Omschrijving 2
            for _, row in df_db.iterrows():
                # Pak de teksten uit de kolommen van je afbeelding
                omschrijving_1 = str(row.get('Omschrijving 1', '')).strip()
                omschrijving_2 = str(row.get('Omschrijving 2', '')).strip()
                art_nr = str(row.get('Art. Nr.', 'N/B')).strip()
                korting = str(row.get('Kortingsgroep', 'N/B')).strip()

                # Check of omschrijving 1 OF 2 in de PDF voorkomt
                match_1 = len(omschrijving_1) > 4 and omschrijving_1.lower() in full_pdf_text
                match_2 = len(omschrijving_2) > 4 and omschrijving_2.lower() in full_pdf_text

                if match_1 or match_2:
                    gevonden_items.append({
                        "Art. Nr.": art_nr,
                        "Kortingsgroep": korting,
                        "Gevonden tekst": omschrijving_1 if match_1 else omschrijving_2
                    })
            
            if gevonden_items:
                res_df = pd.DataFrame(gevonden_items).drop_duplicates()
                st.dataframe(res_df)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    res_df.to_excel(writer, index=False)
                st.download_button("Download Resultaat Excel", output.getvalue(), "match_resultaat.xlsx")
            else:
                st.warning("Geen van de omschrijvingen uit de Excel zijn gevonden in deze PDF.")


# --- FUNCTIE 2: VERGELIJKER (JOUW CODE) ---
elif keuze == "PDF Vergelijker (Rood)":
    st.title("🔍 PDF Vergelijker")
    col1, col2 = st.columns(2)
    with col1: old_file = st.file_uploader("Oude PDF", type="pdf")
    with col2: new_file = st.file_uploader("Nieuwe PDF", type="pdf")

    if old_file and new_file and st.button("Vergelijk"):
        doc1 = fitz.open(stream=old_file.read(), filetype="pdf")
        doc2 = fitz.open(stream=new_file.read(), filetype="pdf")
        pool = set(l.strip() for p in doc1 for l in p.get_text().splitlines() if len(l.strip()) > 3)
        
        diff_count = 0
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
                    diff_count += 1
        
        st.download_button("Download Resultaat", doc2.write(), "verschillen.pdf")

# --- FUNCTIE 3: PDF NAAR WORD ---
elif keuze == "PDF naar Word":
    st.title("📝 PDF naar Word Converter")
    word_upload = st.file_uploader("Upload PDF", type="pdf")
    if word_upload and st.button("Converteer"):
        with open("temp.pdf", "wb") as f: f.write(word_upload.getbuffer())
        cv = Converter("temp.pdf")
        cv.convert("temp.docx")
        cv.close()
        with open("temp.docx", "rb") as f:
            st.download_button("Download Word-bestand", f, "document.docx")
        os.remove("temp.pdf")
        os.remove("temp.docx")


