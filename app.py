import streamlit as st
import fitz
import os

st.set_page_config(page_title="PDF Vergelijker", layout="centered")
st.title("📄 PDF Vergelijker")
st.write("Sleep twee PDF's hieronder om de verschillen **rood** te markeren.")

col1, col2 = st.columns(2)
with col1:
    old_file = st.file_uploader("Oude PDF (Referentie)", type="pdf")
with col2:
    new_file = st.file_uploader("Nieuwe PDF (Controle)", type="pdf")

if old_file and new_file:
    if st.button("Start Vergelijking"):
        doc1 = fitz.open(stream=old_file.read(), filetype="pdf")
        doc2 = fitz.open(stream=new_file.read(), filetype="pdf")

        old_text_pool = set(l.strip() for p in doc1 for l in p.get_text().splitlines() if len(l.strip()) > 3)

        diff_count = 0
        for page in doc2:
            marked = set()
            for line in page.get_text().splitlines():
                clean = line.strip()
                if clean and clean not in old_text_pool and clean not in marked:
                    for rect in page.search_for(clean):
                        annot = page.add_highlight_annot(rect)
                        annot.set_colors(stroke=(1, 0, 0))
                        annot.update()
                    marked.add(clean)
                    diff_count += 1

        out_pdf = doc2.write()
        st.success(f"Klaar! {diff_count} verschillen gevonden.")
        st.download_button("Download Resultaat (PDF)", out_pdf, "verschillen.pdf", "application/pdf")
