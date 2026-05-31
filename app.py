import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Modo Posicional", layout="wide")

st.title("⚔️ Panel de Control - Extractor Estricto")

if "mis_ciudades" not in st.session_state:
    st.session_state["mis_ciudades"] = {}
if "ciudades_amigos" not in st.session_state:
    st.session_state["ciudades_amigos"] = {}

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_fila_posicional(bloques):
    # Ordenar bloques por posición X (izquierda a derecha)
    bloques.sort(key=lambda x: x[0][0][0])
    
    numeros = []
    nombre_partes = []
    
    for bbox, texto in bloques:
        texto_clean = texto.replace(".", "").replace(",", "").strip()
        if texto_clean.isdigit():
            numeros.append(int(texto_clean))
        elif len(texto_clean) > 2:
            nombre_partes.append(texto_clean)
            
    # Asignación Posicional Estricta
    datos = {"ID": 0, "Nombre": " ".join(nombre_partes), "Población": 0, "Edificios": 0}
    
    if len(numeros) >= 1:
        datos["ID"] = numeros[0] # El de la izquierda es ID
    
    # Si detectamos varios números, el ÚLTIMO siempre es Edificios
    if len(numeros) >= 2:
        ultimo_valor = numeros[-1]
        if ultimo_valor <= 330:
            datos["Edificios"] = ultimo_valor
            # Si hay números en medio, el resto es Población
            if len(numeros) > 2:
                datos["Población"] = numeros[1]
            elif len(numeros) == 2:
                # Caso especial: solo hay dos números (ID y Edificios)
                # Población quedaría en 0 (correcto si no se leyó o está ausente)
                pass
        else:
            # Si el último no es <= 330, asumimos que es Población
            datos["Población"] = ultimo_valor
            
    return datos

def procesar_imagen(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    resultados = reader.readtext(img)
    
    filas = {}
    for (bbox, texto, prob) in resultados:
        y = int((bbox[0][1] + bbox[2][1]) / 2)
        agrupado = False
        for y_base in filas:
            if abs(y_base - y) < 20:
                filas[y_base].append((bbox, texto))
                agrupado = True
                break
        if not agrupado:
            filas[y] = [(bbox, texto)]
            
    ciudades = {}
    for y in filas:
        # Filtrar encabezados
        if any("id" in b[1].lower() for b in filas[y]): continue
            
        ciudad = procesar_fila_posicional(filas[y])
        if 0 < ciudad
