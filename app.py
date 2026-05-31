import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Final Pro", layout="wide")

st.title("⚔️ Panel de Control - Optimización y Precisión Total")
st.write("Sube tus capturas. Sistema corregido para asegurar la detección exacta de ID, Nombre, Población y Edificios.")

# Almacenamiento en memoria para persistencia
if "mis_ciudades" not in st.session_state:
    st.session_state["mis_ciudades"] = {}
if "ciudades_amigos" not in st.session_state:
    st.session_state["ciudades_amigos"] = {}

# Menú lateral táctico
st.sidebar.header("⚙️ Ajuste de Rangos Máximos")
max_pob = st.sidebar.slider("Diferencia Máxima de Población", min_value=100, max_value=10000, value=4999, step=1)
max_edi = st.sidebar.slider("Diferencia Máxima de Edificios", min_value=1, max_value=50, value=20, step=1)

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Limpiar Base de Datos"):
    st.session_state["mis_ciudades"] = {}
    st.session_state["ciudades_amigos"] = {}
    st.rerun()

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_tabla_perfecta(archivos_subidos):
    ciudades_extraidas = {}
    
    for archivo in archivos_subidos:
        file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        alto, ancho, _ = img.shape
        
        # Escaneo general inicial
        resultados_ocr = reader.readtext(img)
        
        # Agrupar por filas (coordenada Y)
        filas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            for y_base in filas.keys():
                if abs(y_base - y_centro) < 18:
                    filas[y_base].append((bbox, texto))
                    encontrado = True
                    break
            if not encontrado:
                filas[y_centro] = [(bbox, texto)]
        
        # Procesar cada fila detectada
        for y_coord in sorted(filas.keys()):
            bloques = sorted(filas[y_coord], key=lambda x: x[0][0][0]) # Ordenar de izquierda a derecha (X)
            
            id_detectado = None
            nombre_detectado = []
            numeros_encontrados = []
            
            # Analizar contenido de la fila
            for bbox, texto in bloques:
                texto_limpio = texto.strip()
                if not texto_limpio:
                    continue
                
                solo_num = texto_limpio.replace('.', '').replace(',', '').replace(' ', '')
                
                if solo_num.isdigit():
                    num_int = int(solo_num)
                    # El primer número a la izquierda de la pantalla siempre es el ID
                    if id_detectado is None and bbox[0][0] < (ancho * 0.20) and num_int < 1000:
                        id_detectado = num_int
                    else:
                        numeros_encontrados.append((bbox[0][0], num_int))
                else:
                    # Detectar el nombre omitiendo cabeceras de la tabla
                    if len(texto_limpio) > 1 and not any(w in texto_limpio.lower() for w in
