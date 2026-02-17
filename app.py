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

# --- FUNCTIE 1: FULL SCAN MATCHER ---
if keuze == "Full Scan Matcher":
    st.title("🔬 Global PDF & Excel Matcher")
    st.info("Deze tool zoekt naar ELKE waarde uit de Excel in de VOLLEDIGE PDF.")
    
    EXCEL_FILE = "artikelen.xlsx" 

    if not os.path.exists(EXCEL_FILE):
        st.error(f"Bestand '{EXCEL_FILE}' niet gevonden. Upload dit eerst naar de server.")
    else:
        @st.cache_data
        def load_full_db(file):
            df = pd.read_excel(file)
            # Verwijder lege rijen/kolommen en zet alles om naar string
            df = df.fillna("").astype(str)
            return df
        
        df_db = load_full_db(EXCEL_FILE)
        pdf_file = st.file_uploader("Upload PDF voor globale scan", type="pdf")

        if pdf_file and st.button("Start Volledige Analyse"):
            with st.spinner("De PDF wordt van voor naar achteren doorzocht..."):
                # PDF Tekst extractie (Volledige PDF in geheugen)
                doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                full_pdf_text = ""
                for page in doc:
                    full_pdf_text += page.get_text("text") + " "
                
                # Normalisatie voor betere matching
                full_text_clean = " ".join(full_pdf_text.split()).lower()
                
                gevonden_items = []

                # Loop door elke rij in de Excel
                for index, row in df_db.iterrows():
                    # Combineer alle cellen in deze rij tot één grote zoekterm
                    rij_content = " ".join(row.values).lower()
                    
                    # We zoeken op elk individueel woord/getal uit de Excel-rij (mits > 3 tekens)
                    # om de kans op een hit in de PDF te maximaliseren
                    search_terms = [t.strip() for t in row.values if len(t.strip()) > 3]
                    
                    match_found = False
                    matched_on = ""

                    for term in search_terms:
                        if term.lower() in full_text_clean:
                            match_found = True
                            matched_on = term
                            break
                    
                    if match_found:
                        # Zoek korting (%) in de buurt van de match
                        start_pos = full_text_clean.find(matched_on.lower())
                        context = full_text_clean[max(0, start_pos-50) : start_pos + 150]
                        
                        korting_match = re.search(r'(\d+[\d,.]*)\s*%', context)
                        gevonden_korting = korting_match.group(0) if korting_match else "Niet gevonden"

                        # Voeg de hele originele rij toe aan de resultaten + de gevonden korting
                        result_row = row.to_dict()
                        result_row["Gevonden Term"] = matched_on
                        result_row["Korting uit PDF"] = gevonden_korting
                        gevonden_items.append(result_row)

                if gevonden_items:
                    res_df = pd.DataFrame(gevonden_items)
                    st.success(f"Klaar! {len(res_df)} matches gevonden op basis van de volledige Excel-inhoud.")
                    st.dataframe(res_df, use_container_width=True)
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        res_df.to_excel(writer, index=False)
                    st.download_button("📥 Download Uitgebreid Resultaat", output.getvalue(), "match_resultaat_full.xlsx")
                else:
                    st.warning("Geen enkele match gevonden tussen de Excel-data en de PDF-tekst.")



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



