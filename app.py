import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(layout="wide")
st.title("⚔️ Extractor por proximidad espacial")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def extraer_filas(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    # Detectamos todo el texto
    results = reader.readtext(img)
    
    # 1. Agrupar por línea (coordenada Y)
    filas = {}
    for (bbox, text, prob) in results:
        y = int(bbox[0][1])
        # Buscamos si ya existe una fila similar
        encontrado = False
        for y_base in filas.keys():
            if abs(y_base - y) < 20: # Margen de error vertical
                filas[y_base].append((bbox[0][0], text))
                encontrado = True
                break
        if not encontrado:
            filas[y] = [(bbox[0][0], text)]
            
    # 2. Ordenar cada fila por X
    datos_finales = []
    for y in filas:
        fila = sorted(filas[y], key=lambda x: x[0])
        # Intentamos extraer: [ID, Nombre, Población, Edificios]
        # El nombre puede tener espacios, así que lo reconstruimos
        texto_fila = [x[1] for x in fila]
        datos_finales.append(texto_fila)
        
    return datos_finales

files = st.file_uploader("Sube capturas", accept_multiple_files=True)
if files:
    for f in files:
        data = extraer_filas(f)
        st.write(data)
