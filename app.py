import streamlit as st
import fitz
from pdf2docx import Converter
import os

# Pagina instellingen
st.set_page_config(page_title="Bedrijfs PDF Tool", layout="wide")

# Zijmenu voor navigatie
st.sidebar.title("🛠️ PDF Gereedschap")
keuze = st.sidebar.radio("Wat wilt u doen?", ["PDF Vergelijker (Rood)", "PDF naar Word"])

# --- FUNCTIE 1: JOUW SPECIFIEKE PDF VERGELIJKER (ROOD) ---
if keuze == "PDF Vergelijker (Rood)":
    st.title("🔍 PDF Vergelijker")
    st.write("Alle tekst in de nieuwe PDF die niet in de oude staat, wordt **rood** gemarkeerd.")
    
    col1, col2 = st.columns(2)
    with col1:
        old_file = st.file_uploader("Oude PDF (Referentie)", type="pdf")
    with col2:
        new_file = st.file_uploader("Nieuwe PDF (Controle)", type="pdf")

    if old_file and new_file:
        if st.button("Start Vergelijking"):
            # Open PDF's vanuit geheugen
            doc1 = fitz.open(stream=old_file.read(), filetype="pdf")
            doc2 = fitz.open(stream=new_file.read(), filetype="pdf")
            
            # Stap 1: Verzamel alle unieke tekst uit de oude PDF
            old_text_pool = set()
            for page in doc1:
                for line in page.get_text().splitlines():
                    clean = line.strip()
                    if len(clean) > 3:
                        old_text_pool.add(clean)

            # Stap 2: Markeer verschillen in de nieuwe PDF
            diff_count = 0
            for page in doc2:
                marked_on_this_page = set()
                page_lines = page.get_text().splitlines()
                
                for line in page_lines:
                    clean_line = line.strip()
                    
                    if clean_line and clean_line not in old_text_pool:
                        if clean_line not in marked_on_this_page:
                            # Zoek locatie en markeer rood (1, 0, 0)
                            for rect in page.search_for(clean_line):
                                annot = page.add_highlight_annot(rect)
                                annot.set_colors(stroke=(1, 0, 0)) 
                                annot.update()
                            marked_on_this_page.add(clean_line)
                            diff_count += 1

            # Resultaat opslaan voor download
            out_pdf = doc2.write()
            doc1.close()
            doc2.close()
            
            st.success(f"Klaar! {diff_count} verschillen rood gemarkeerd.")
            st.download_button("Download Resultaat PDF", out_pdf, "verschillen_rood.pdf", "application/pdf")

# --- FUNCTIE 2: PDF NAAR WORD ---
elif keuze == "PDF naar Word":
    st.title("📝 PDF naar Word Converter")
    st.write("Zet een PDF-bestand om naar een bewerkbaar Word-document (.docx).")
    
    word_upload = st.file_uploader("Upload PDF voor conversie", type="pdf")
    
    if word_upload:
        if st.button("Converteer naar Word"):
            # Tijdelijk bestand opslaan voor de converter
            with open("temp.pdf", "wb") as f:
                f.write(word_upload.getbuffer())
            
            docx_file = "document.docx"
            with st.spinner("Bezig met converteren..."):
                # Gebruik de [pdf2docx bibliotheek](https://dreadm.github.io)
                cv = Converter("temp.pdf")
                cv.convert(docx_file)
                cv.close()
            
            with open(docx_file, "rb") as f:
                st.download_button("Download Word-bestand", f, "geconverteerd.docx", 
                                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
            # Opruimen
            os.remove("temp.pdf")
            os.remove(docx_file)

st.sidebar.markdown("---")
st.sidebar.caption("Versie 1.2 - Intern gebruik")
