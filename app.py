import streamlit as st
import fitz
import pandas as pd
import io
import os
import re
import difflib
from pdf2docx import Converter

st.set_page_config(page_title="Bedrijfs PDF Tool v4", layout="wide")

# Navigatie
st.sidebar.title("🛠️ PDF Gereedschap")
keuze = st.sidebar.radio("Wat wilt u doen?", ["Artikelzoeker & Korting", "PDF Vergelijker (Rood)", "PDF naar Word"])

# --- FUNCTIE 1: MERK-GERICHTE ARTIKELZOEKER ---
if keuze == "Artikelzoeker & Korting":
    st.title("🛡️ Merk-Gerichte Artikelzoeker")
    st.info("De app herkent eerst het merk in de PDF en filtert daarna de database.")
    
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
        pdf_file = st.file_uploader("Upload PDF", type="pdf")

        if pdf_file and st.button("Start Merk-Check & Scan"):
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            
            # STAP 1: PDF Tekst verzamelen en opschonen (FIX: Alles op één regel)
            pdf_pages_text =
            full_text_clean = " ".join(" ".join(pdf_pages_text).split()).lower()

            # STAP 2: Welke merken staan in de PDF?
            if 'Merknaam' in df_db.columns:
                alle_merken = df_db['Merknaam'].dropna().unique()
                gevonden_merken = [str(m) for m in alle_merken if str(m).lower() in full_text_clean]
                
                if gevonden_merken:
                    st.success(f"Gevonden merk(en) in PDF: {', '.join(gevonden_merken)}")
                    df_filtered = df_db[df_db['Merknaam'].astype(str).isin(gevonden_merken)]
                else:
                    st.warning("Geen specifiek merk herkend. Ik scan de volledige database.")
                    df_filtered = df_db
            else:
                st.warning("Kolom 'Merknaam' niet gevonden. Ik scan de volledige database.")
                df_filtered = df_db

            # STAP 3: Artikelen matchen
            gevonden_items = []
            for _, row in df_filtered.iterrows():
                art_nr = str(row.get('Art. Nr.', '')).strip().lower()
                oms1 = str(row.get('Omschrijving 1', '')).strip().lower()
                oms2 = str(row.get('Omschrijving 2', '')).strip().lower()

                match_found = False
                match_term = ""

                if art_nr and len(art_nr) >= 3 and art_nr in full_text_clean:
                    match_found, match_term = True, art_nr
                elif oms1 and len(oms1) > 5 and oms1 in full_text_clean:
                    match_found, match_term = True, oms1
                elif oms2 and len(oms2) > 5 and oms2 in full_text_clean:
                    match_found, match_term = True, oms2

                if match_found:
                    # STAP 4: Korting zoeken nabij de match
                    start_pos = full_text_clean.find(match_term)
                    context = full_text_clean[start_pos:start_pos + 150]
                    korting_match = re.search(r'(\d+[\d,.]*)\s*%', context)
                    gevonden_korting = korting_match.group(0) if korting_match else "N/B"

                    gevonden_items.append({
                        "Merk": row.get('Merknaam', 'N/B'),
                        "Art. Nr.": row.get('Art. Nr.', 'N/B'),
                        "Kortingsgroep": row.get('Kortingsgroep', 'N/B'),
                        "Korting uit PDF": gevonden_korting,
                        "Omschrijving": row.get('Omschrijving 1', 'N/B')
                    })

            if gevonden_items:
                res_df = pd.DataFrame(gevonden_items).drop_duplicates(subset=["Art. Nr."])
                st.write(f"✅ Match voltooid: {len(res_df)} artikelen gevonden.")
                st.dataframe(res_df)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    res_df.to_excel(writer, index=False)
                st.download_button("Download Resultaat Excel", output.getvalue(), "match_resultaat.xlsx")
            else:
                st.warning("Geen artikelen gevonden die matchen.")

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
