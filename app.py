import streamlit as st
import fitz
import pandas as pd
import io
import os
import re
from pdf2docx import Converter

st.set_page_config(page_title="Bedrijfs PDF Tool", layout="wide")

st.sidebar.title("🛠️ PDF Gereedschap")
keuze = st.sidebar.radio("Menu", ["Artikelzoeker & Korting", "PDF Vergelijker (Rood)", "PDF naar Word"])

# --- FUNCTIE 1: ARTIKELZOEKER ---
if keuze == "Artikelzoeker & Korting":
    st.title("🛡️ Merk-Gerichte Artikelzoeker")
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

        if pdf_file and st.button("Start Scan"):
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            
            # De bewuste regel, nu extra veilig geschreven:
            pdf_pages_text =
            full_text_clean = " ".join(" ".join(pdf_pages_text).split()).lower()

            if 'Merknaam' in df_db.columns:
                alle_merken = df_db['Merknaam'].dropna().unique()
                gevonden_merken = [str(m) for m in alle_merken if str(m).lower() in full_text_clean]
                if gevonden_merken:
                    st.success(f"Gevonden merk(en): {', '.join(gevonden_merken)}")
                    df_filtered = df_db[df_db['Merknaam'].astype(str).isin(gevonden_merken)]
                else:
                    st.warning("Geen merk herkend, scan volledige database.")
                    df_filtered = df_db
            else:
                df_filtered = df_db

            gevonden_items = []
            for _, row in df_filtered.iterrows():
                art_nr = str(row.get('Art. Nr.', '')).strip().lower()
                oms1 = str(row.get('Omschrijving 1', '')).strip().lower()
                
                match_found = False
                match_term = ""

                if art_nr and len(art_nr) >= 3 and art_nr in full_text_clean:
                    match_found, match_term = True, art_nr
                elif oms1 and len(oms1) > 5 and oms1 in full_text_clean:
                    match_found, match_term = True, oms1

                if match_found:
                    start_pos = full_text_clean.find(match_term)
                    context = full_text_clean[start_pos:start_pos + 150]
                    k_match = re.search(r'(\d+[\d,.]*)\s*%', context)
                    gevonden_korting = k_match.group(0) if k_match else "N/B"

                    gevonden_items.append({
                        "Merk": row.get('Merknaam', 'N/B'),
                        "Art. Nr.": row.get('Art. Nr.', 'N/B'),
                        "Kortingsgroep": row.get('Kortingsgroep', 'N/B'),
                        "Korting uit PDF": gevonden_korting,
                        "Omschrijving": row.get('Omschrijving 1', 'N/B')
                    })

            if gevonden_items:
                res_df = pd.DataFrame(gevonden_items).drop_duplicates(subset=["Art. Nr."])
                st.dataframe(res_df)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    res_df.to_excel(writer, index=False)
                st.download_button("Download Excel", output.getvalue(), "resultaat.xlsx")
            else:
                st.warning("Geen matches gevonden.")

# --- FUNCTIE 2: VERGELIJKER ---
elif keuze == "PDF Vergelijker (Rood)":
    st.title("🔍 PDF Vergelijker")
    f1 = st.file_uploader("Oud", type="pdf")
    f2 = st.file_uploader("Nieuw", type="pdf")
    if f1 and f2 and st.button("Vergelijk"):
        d1, d2 = fitz.open(stream=f1.read(), filetype="pdf"), fitz.open(stream=f2.read(), filetype="pdf")
        p1 = set(l.strip() for p in d1 for l in p.get_text().splitlines() if len(l.strip()) > 3)
        for page in d2:
            m = set()
            for line in page.get_text().splitlines():
                c = line.strip()
                if c and c not in p1 and c not in m:
                    for r in page.search_for(c):
                        a = page.add_highlight_annot(r)
                        a.set_colors(stroke=(1, 0, 0))
                        a.update()
                    m.add(c)
        st.download_button("Download", d2.write(), "diff.pdf")

# --- FUNCTIE 3: WORD ---
elif keuze == "PDF naar Word":
    st.title("📝 PDF naar Word")
    wf = st.file_uploader("PDF", type="pdf")
    if wf and st.button("Converteer"):
        with open("t.pdf", "wb") as f: f.write(wf.getbuffer())
        c = Converter("t.pdf")
        c.convert("t.docx")
        c.close()
        with open("t.docx", "rb") as f: st.download_button("Download", f, "doc.docx")
        os.remove("t.pdf")
        os.remove("t.docx")
