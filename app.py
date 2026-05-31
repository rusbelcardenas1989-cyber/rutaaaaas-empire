import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(layout="wide")
st.title("⚔️ Extractor Base - Estructura Correcta")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_fila_base(bloques):
    # Ordenamos por X para respetar el orden ID -> Nombre -> Población -> Edificios
    bloques.sort(key=lambda x: x[0][0][0])
    
    # Extraemos elementos sin filtros restrictivos
    elementos = [b[1] for b in bloques]
    
    # Asignación simple: el código no "juzga" si el número es correcto o no
    datos = {"ID": 0, "Nombre": "", "Población": 0, "Edificios": 0}
    
    # Ajustar según la detección
    if len(elementos) >= 1: datos["ID"] = elementos[0]
    if len(elementos) >= 2: datos["Nombre"] = elementos[1]
    if len(elementos) >= 3: datos["Población"] = elementos[2]
    if len(elementos) >= 4: datos["Edificios"] = elementos[3]
    
    return datos

def procesar_imagen(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    results = reader.readtext(img)
    
    filas = {}
    for (bbox, text, prob) in results:
        y = int(bbox[0][1])
        encontrado = False
        for y_base in filas.keys():
            if abs(y_base - y) < 20:
                filas[y_base].append((bbox[0][0], text))
                encontrado = True
                break
        if not encontrado:
            filas[y] = [(bbox[0][0], text)]
            
    lista_datos = []
    for y in filas:
        fila = sorted(filas[y], key=lambda x: x[0])
        # Solo procesamos si parece una fila con datos (más de 2 elementos)
        if len(fila) >= 2:
            lista_datos.append(procesar_fila_base(fila))
            
    return lista_datos

files = st.file_uploader("Sube capturas", accept_multiple_files=True)
if files:
    data_final = []
    for f in files:
        data_final.extend(procesar_imagen(f))
    st.table(data_final)
