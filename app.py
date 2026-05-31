import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(layout="wide")
st.title("⚔️ Extractor por Columnas (Sin Filas)")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def extraer_todo_por_columna(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    results = reader.readtext(img)
    
    # Clasificamos todo por su posición X
    ids = []
    nombres = []
    pobs = []
    edifs = []
    
    # Ordenamos resultados por posición X para identificar columnas
    results.sort(key=lambda x: x[0][0][0])
    
    for (bbox, text, prob) in results:
        t = str(text).replace(".", "").replace(",", "").strip()
        x = bbox[0][0]
        
        # Filtramos encabezados
        if any(w in t.lower() for w in ["id", "nombre", "pob", "edi"]): continue
        
        # Clasificación por posición X aproximada (ajusta estos rangos según tu imagen)
        if 50 < x < 150 and t.isdigit(): ids.append(int(t))
        elif 150 < x < 400 and len(t) > 2: nombres.append(t)
        elif 500 < x < 700 and t.isdigit(): pobs.append(int(t))
        elif x > 700 and t.isdigit(): edifs.append(int(t))

    return ids, nombres, pobs, edifs

# Interfaz
files = st.file_uploader("Sube capturas", accept_multiple_files=True)
if files:
    all_data = []
    for f in files:
        ids, noms, pobs, edifs = extraer_todo_por_columna(f)
        # Combinamos las listas detectadas
        for i in range(len(ids)):
            all_data.append({
                "ID": ids[i] if i < len(ids) else 0,
                "Nombre": noms[i] if i < len(noms) else "-",
                "Población": pobs[i] if i < len(pobs) else 0,
                "Edificios": edifs[i] if i < len(edifs) else 0
            })
    st.dataframe(all_data)
