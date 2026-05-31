import streamlit as st
import pandas as pd
import easyocr
import re
import numpy as np
import cv2

st.set_page_config(layout="wide")
st.title("💰 Optimizador de Rutas (Max. Oro)")

# 1. Cargar OCR (Caché para velocidad)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr()

# 2. Funciones de procesamiento
def limpiar_num(texto):
    return int(re.sub(r'[^\d]', '', str(texto)))

def procesar_captura(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    results = reader.readtext(img)
    
    filas = {}
    for (bbox, text, prob) in results:
        y = int(bbox[0][1])
        y_base = next((k for k in filas if abs(k-y) < 20), y)
        if y_base not in filas: filas[y_base] = []
        filas[y_base].append(text)
        
    data = []
    for y in filas:
        t = filas[y]
        if len(t) >= 4:
            try:
                data.append({
                    "ID": t[0], 
                    "Nombre": t[1],
                    "Poblacion": limpiar_num(t[2]),
                    "Edificios": limpiar_num(t[3])
                })
            except: continue
    return pd.DataFrame(data)

# 3. INTERFAZ Y LÓGICA (Definir variables ANTES de usarlas)
col1, col2 = st.columns(2)
f_yo = col1.file_uploader("👤 Subir Mis Ciudades", type=['png', 'jpg'])
f_amigos = col2.file_uploader("👥 Subir Ciudades Amigos", type=['png', 'jpg'], accept_multiple_files=True)

# 4. Ejecución solo si hay archivos
if f_yo is not None and f_amigos:
    df_yo = procesar_captura(f_yo)
    df_amigos_total = pd.concat([procesar_captura(f) for f in f_amigos])
    
    st.subheader("🚀 Rutas Sugeridas")
    ruta_sugerida = []
    
    for _, yo in df_yo.iterrows():
        # Filtro: Dif Edif <= 20 Y Dif Pob <= 4999
        opciones = df_amigos_total[
            (abs(df_amigos_total['Edificios'] - yo['Edificios']) <= 20) & 
            (abs(df_amigos_total['Poblacion'] - yo['Poblacion']) <= 4999)
        ]
        
        for _, mejor in opciones.iterrows():
            ruta_sugerida.append({
                "Mi Ciudad": yo['Nombre'],
                "Mi ID": yo['ID'],
                "-> Enrutar con ID": mejor['ID'],
                "Ciudad Destino": mejor['Nombre'],
                "Dif. Edif": abs(yo['Edificios'] - mejor['Edificios']),
                "Dif. Pob": abs(yo['Poblacion'] - mejor['Poblacion'])
            })

    if ruta_sugerida:
        st.table(pd.DataFrame(ruta_sugerida))
    else:
        st.warning("No se encontraron ciudades compatibles con esos rangos.")
