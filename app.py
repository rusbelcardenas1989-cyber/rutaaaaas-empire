import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(layout="wide")
st.title("⚔️ Extractor de Rejilla Estricta")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_imagen_rejilla(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    # Aumentamos el detalle de detección
    results = reader.readtext(img)
    
    # Definimos zonas X aproximadas según tu imagen (ajustables)
    # Col 1: ID, Col 2: Nombre, Col 3: Población, Col 4: Edificios
    columnas = { "ID": [], "Nombre": [], "Pob": [], "Edif": [] }
    
    for (bbox, text, prob) in results:
        x = bbox[0][0]
        # Clasificamos según la coordenada X (basado en el ancho total de 1222.png)
        # Estos valores son una estimación de la posición horizontal
        if x < 100: columnas["ID"].append(text)
        elif 100 <= x < 350: columnas["Nombre"].append(text)
        elif 350 <= x < 650: columnas["Pob"].append(text)
        elif x >= 650: columnas["Edif"].append(text)
        
    return columnas

# UI
files = st.file_uploader("Sube capturas", accept_multiple_files=True)
if files:
    for f in files:
        cols = procesar_imagen_rejilla(f)
        st.write("Datos detectados por columna (puedes verificar si los datos coinciden):")
        st.json(cols)
