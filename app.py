import streamlit as st
import pandas as pd
import easyocr
import re
import numpy as np
import cv2

st.set_page_config(layout="wide")
st.title("⚔️ Buscador de Ciudades: Emparejamiento por ID")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr()

def limpiar_num(texto):
    # Elimina todo lo que no sea dígito
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
                # Asumimos: ID, Nombre, Población, Edificios
                data.append({
                    "ID": t[0], 
                    "Nombre": t[1],
                    "Poblacion": limpiar_num(t[2]),
                    "Edificios": limpiar_num(t[3])
                })
            except: continue
    return pd.DataFrame(data)

# --- Interfaz ---
col1, col2 = st.columns(2)
with col1:
    f_yo = st.file_uploader("👤 Mis Ciudades (1 captura)", type=['png', 'jpg'])
with col2:
    f_amigos = st.file_uploader("👥 Ciudades Amigos (Varias capturas)", type=['png', 'jpg'], accept_multiple_files=True)

if f_yo and f_amigos:
    df_yo = procesar_captura(f_yo)
    df_amigos_total = pd.DataFrame()
    for f in f_amigos:
        df_amigos_total = pd.concat([df_amigos_total, procesar_captura(f)])
    
    matches = []
    for _, yo in df_yo.iterrows():
        for _, amigo in df_amigos_total.iterrows():
            dif_edif = abs(yo['Edificios'] - amigo['Edificios'])
            dif_pob = abs(yo['Poblacion'] - amigo['Poblacion'])
            
            # Filtro: Diferencia de edificios <= 20
            # Filtro: Diferencia de población <= 4999 (hacia arriba o abajo)
            if dif_edif <= 20 and dif_pob <= 4999:
                matches.append({
                    "Mi ID": yo['ID'],
                    "Mi Ciudad": yo['Nombre'],
                    "Ciudad Amigo": amigo['Nombre'],
                    "Dif. Edificios": dif_edif,
                    "Dif. Población": dif_pob
                })
    
    if matches:
        res_df = pd.DataFrame(matches)
        # Ordenamos por tu ID para que sea más fácil de leer
        res_df = res_df.sort_values(by="Mi ID")
        st.success(f"¡Encontradas {len(res_df)} opciones óptimas!")
        st.table(res_df)
    else:
        st.warning("No se encontraron ciudades que cumplan el rango de ±4999 de población y ±20 edificios.")
