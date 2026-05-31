import streamlit as st
import cv2
import numpy as np
import easyocr

# Configuración inicial
st.set_page_config(page_title="Extractor de Ciudades", layout="wide")
st.title("⚔️ Panel de Control - Extractor Posicional")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def extraer_datos_fila(bloques):
    # Ordenar bloques de izquierda a derecha según su posición X
    bloques.sort(key=lambda x: x[0][0][0])
    
    numeros = []
    nombres = []
    
    for _, texto in bloques:
        # Limpiamos caracteres no numéricos excepto los que forman parte del número (sin puntos)
        t_clean = str(texto).replace(".", "").replace(",", "").strip()
        if t_clean.isdigit():
            numeros.append(int(t_clean))
        elif len(t_clean) > 2:
            nombres.append(t_clean)
            
    # Asignación por posición literal
    # Posición 0: ID, Posición 1: Población, Posición 2: Edificios
    datos = {"ID": 0, "Nombre": " ".join(nombres), "Población": 0, "Edificios": 0}
    
    if len(numeros) >= 1: datos["ID"] = numeros[0]
    if len(numeros) >= 2: datos["Población"] = numeros[1]
    if len(numeros) >= 3: datos["Edificios"] = numeros[2]
    
    return datos

def procesar_imagen(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    resultados = reader.readtext(img)
    
    # Agrupar elementos por cercanía vertical (filas)
    filas = {}
    for r in resultados:
        y = int((r[0][0][1] + r[0][2][1]) / 2)
        agrupado = False
        for y_base in filas:
            if abs(y_base - y) < 20:
                filas[y_base].append((r[0], r[1]))
                agrupado = True
                break
        if not agrupado: filas[y] = [(r[0], r[1])]
            
    lista_ciudades = []
    for y in filas:
        # Ignorar encabezados
        if any("id" in str(b[1]).lower() for b in filas[y]): continue
        
        c = extraer_datos_fila(filas[y])
        if 0 < c["ID"] < 1000:
            lista_ciudades.append(c)
            
    return lista_ciudades

# UI
st.subheader("Subir Capturas")
files = st.file_uploader("Sube tus imágenes", accept_multiple_files=True)
if files:
    data_final = []
    for f in files:
        data_final.extend(procesar_imagen(f))
    st.dataframe(sorted(data_final, key=lambda x: x["ID"]))
