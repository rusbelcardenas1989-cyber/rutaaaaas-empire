import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Edificios", layout="wide")
st.title("⚔️ Extractor con Detección Robusta")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_fila_mejorada(bloques):
    # Ordenar bloques por X
    bloques.sort(key=lambda x: x[0][0][0])
    
    numeros = []
    nombres = []
    
    for _, texto in bloques:
        # Limpieza más agresiva para detectar el número
        t = str(texto).replace(".", "").replace(",", "").strip()
        if t.isdigit():
            numeros.append((int(t), _[0][0])) # Guardamos el número y su X
        elif len(t) > 2:
            nombres.append(t)
            
    datos = {"ID": 0, "Nombre": " ".join(nombres), "Población": 0, "Edificios": 0}
    
    if len(numeros) >= 1: 
        datos["ID"] = numeros[0][0]
    
    # Lógica de asignación por valor y posición
    for val, x in numeros[1:]:
        if 1000 <= val <= 99999:
            datos["Población"] = val
        elif 1 <= val <= 330:
            datos["Edificios"] = val
            
    return datos

def procesar_imagen(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    res_ocr = reader.readtext(img)
    
    filas = {}
    for r in res_ocr:
        y = int((r[0][0][1] + r[0][2][1]) / 2)
        agrupado = False
        for y_base in filas:
            if abs(y_base - y) < 25:
                filas[y_base].append((r[0], r[1]))
                agrupado = True
                break
        if not agrupado: filas[y] = [(r[0], r[1])]
            
    ciudades = {}
    for y in filas:
        if any("id" in str(b[1]).lower() for b in filas[y]): continue
        c = procesar_fila_mejorada(filas[y])
        if 0 < c["ID"] < 1000: ciudades[c["ID"]] = c
    return ciudades

# Interfaz
col1, col2 = st.columns(2)
with col1:
    files = st.file_uploader("Sube capturas", accept_multiple_files=True)
    if files:
        data = {}
        for f in files: data.update(procesar_imagen(f))
        st.dataframe(sorted(list(data.values()), key=lambda x: x["ID"]))
