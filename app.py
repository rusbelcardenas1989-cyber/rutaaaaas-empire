import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(layout="wide")
st.title("⚔️ Extractor Universal (Sin Filtros)")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_imagen_simple(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    results = reader.readtext(img)
    
    # Agrupamos por altura (Y) con mucha tolerancia (40 píxeles)
    filas = {}
    for (bbox, text, prob) in results:
        y = int(bbox[0][1])
        encontrado = False
        for y_base in filas:
            if abs(y_base - y) < 40:
                filas[y_base].append(text)
                encontrado = True
                break
        if not encontrado:
            filas[y] = [text]
            
    # Convertimos a formato tabla
    data = []
    for y in filas:
        row = filas[y]
        # Solo filas que tengan números
        if len(row) >= 3:
            data.append({"Fila": row})
    return data

files = st.file_uploader("Sube capturas", accept_multiple_files=True)
if files:
    for f in files:
        st.write(f"Resultados para {f.name}:")
        datos = procesar_imagen_simple(f)
        st.write(datos)
