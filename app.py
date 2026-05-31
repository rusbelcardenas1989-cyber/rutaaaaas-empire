import streamlit as st
import pandas as pd
import easyocr
import re
import numpy as np
import cv2

st.set_page_config(layout="wide", page_title="Optimizador de Rutas")
st.title("💰 Optimizador de Rutas (Max. Oro)")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr()

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

# --- SIDEBAR DE CARGA ---
st.sidebar.header("📂 Carga de Datos")
f_yo = st.sidebar.file_uploader("👤 Subir Mis Ciudades", type=['png', 'jpg'])
f_amigos = st.sidebar.file_uploader("👥 Subir Ciudades Amigos", type=['png', 'jpg'], accept_multiple_files=True)

if f_yo and f_amigos:
    df_yo = procesar_captura(f_yo)
    df_amigos_total = pd.concat([procesar_captura(f) for f in f_amigos])
    
    # --- PESTAÑAS DE VISTA ---
    tab1, tab2, tab3 = st.tabs(["📋 Mi Biblioteca", "👥 Biblioteca Amigos", "🎯 Matriz de Emparejamiento"])
    
    with tab1:
        st.table(df_yo)
    with tab2:
        st.table(df_amigos_total)
        
    with tab3:
        st.subheader("🔗 IDs Compatibles para Rutas")
        recomendaciones = []
        for _, yo in df_yo.iterrows():
            opciones = df_amigos_total[
                (abs(df_amigos_total['Edificios'] - yo['Edificios']) <= 20) & 
                (abs(df_amigos_total['Poblacion'] - yo['Poblacion']) <= 4999)
            ]
            if not opciones.empty:
                ids_lista = opciones['ID'].unique().tolist()
                recomendaciones.append({
                    "Tu Ciudad (ID)": f"{yo['Nombre']} ({yo['ID']})",
                    "IDs Amigos Recomendados": ", ".join(ids_lista)
                })
        
        if recomendaciones:
            st.table(pd.DataFrame(recomendaciones))
        else:
            st.warning("No se encontraron coincidencias bajo los criterios (±20 Edif, ±4999 Pob).")
else:
    st.info("Por favor, sube una imagen tuya y al menos una de tus amigos para comenzar.")
