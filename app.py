import streamlit as st
import fitz
import difflib

st.set_page_config(page_title="PDF Vergelijker Pro", layout="wide")
st.title("📄 PDF Artikelen Vergelijker")
st.write("Nieuw artikel = **Geel** | Gewijzigde prijs/tekst = **Rood**")

col1, col2 = st.columns(2)
with col1:
    old_file = st.file_uploader("Oude PDF", type="pdf")
with col2:
    new_file = st.file_uploader("Nieuwe PDF", type="pdf")

if old_file and new_file:
    if st.button("Start Analyse"):
        doc1 = fitz.open(stream=old_file.read(), filetype="pdf")
        doc2 = fitz.open(stream=new_file.read(), filetype="pdf")
        
        # Extraheer tekst regels
        text1 = [l.strip() for p in doc1 for l in p.get_text().splitlines() if len(l.strip()) > 3]
        text2 = [l.strip() for p in doc2 for l in p.get_text().splitlines() if len(l.strip()) > 3]

        # Gebruik difflib om te bepalen wat nieuw (+) of gewijzigd is
        d = difflib.Differ()
        diff = list(d.compare(text1, text2))

        # Groepeer wijzigingen voor markering
        added_lines = [line[2:] for line in diff if line.startswith('+ ')]
        
        for page in doc2:
            marked = set()
            for line in added_lines:
                if line not in marked:
                    # Check of deze nieuwe regel erg lijkt op een oude regel (wijziging)
                    # of dat hij compleet nieuw is
                    is_modification = any(difflib.SequenceMatcher(None, line, old_l).ratio() > 0.6 for old_l in text1)
                    
                    color = (1, 0, 0) if is_modification else (1, 1, 0) # Rood vs Geel
                    
                    for rect in page.search_for(line):
                        annot = page.add_highlight_annot(rect)
                        annot.set_colors(stroke=color)
                        annot.update()
                    marked.add(line)

        out_pdf = doc2.write()
        st.success("Analyse voltooid!")
        st.download_button("Download Resultaat", out_pdf, "verschil_analyse.pdf", "application/pdf")
