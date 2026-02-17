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

# --- FUNCTIE 1: ARTIKELZOEKER MET KORTINGSEXTRACE ---
if keuze == "Artikelzoeker (Excel)":
    st.title("📦 Slimme Artikel & Korting Zoeker")
    
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
        pdf_file = st.file_uploader("Upload PDF (bijv. een factuur)", type="pdf")

        if pdf_file and st.button("Start Slimme Analyse"):
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            gevonden_items = []

            for page in doc:
                text = page.get_text("text") # Behoudt een beetje de structuur
                
                for _, row in df_db.iterrows():
                    omschrijving = str(row.get('Omschrijving 1', '')).strip()
                    if len(omschrijving) < 5: continue
                    
                    # Zoek waar de omschrijving staat in de tekst
                    start_index = text.lower().find(omschrijving.lower())
                    
                    if start_index != -1:
                        # Pak een stuk tekst na de omschrijving om de korting te zoeken (ca. 50 tekens)
                        context_tekst = text[start_index:start_index + 100]
                        
                        # Zoek naar patronen zoals "20%", "20,00%" of "Korting: 15"
                        korting_match = re.search(r'(\d+[\d,.]*)\s*%', context_tekst)
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
                st.download_button("Download Resultaat Excel", output.getvalue(), "artikel_kortingen.xlsx")
            else:
                st.warning("Geen matches gevonden.")


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



