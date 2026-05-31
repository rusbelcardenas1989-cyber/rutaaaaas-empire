import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor Definitivo", layout="wide")
st.title("⚔️ Extractor Directo (Posicional)")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_fila_literal(bloques):
    # Ordenar bloques por posición X (de izquierda a derecha)
    bloques.sort(key=lambda x: x[0][0][0])
    
    numeros = []
    nombres = []
    
    for _, texto in bloques:
        # Limpiamos el texto para detectar números (quitamos puntos de miles)
        t = str(texto).replace(".", "").replace(",", "").strip()
        if t.isdigit():
            numeros.append(int(t))
        elif len(t) > 2:
            nombres.append(t)
            
    # Asignación POSICIONAL pura:
    # 0 = ID, 1 = Población, 2 = Edificios
    datos = {"ID": 0, "Nombre": " ".join(nombres), "Población": 0, "Edificios": 0}
    
    if len(numeros) >= 1: datos["ID"] = numeros[0]
    if len(numeros) >= 2: datos["Población"] = numeros[1]
    if len(numeros) >= 3: datos["Edificios"] = numeros[2]
    # Si solo hay 2 números, asumimos el último es Edificios si es chico
    elif len(numeros) == 2 and numeros[1] <= 330:
        datos["Edificios"] = numeros[1]
        datos["Población"] = 0 
        
    return datos

def procesar_imagen(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    res_ocr = reader.readtext(img)
    
    # Agrupar por filas (coordenada Y)
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
        c = procesar_fila_literal(filas[y])
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
