import streamlit as st
import pandas as pd
import easyocr
import re
import numpy as np
import cv2

st.set_page_config(layout="wide")
st.title("⚔️ Gestor de Ciudades: Biblioteca y Emparejamiento")

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

# --- UI: CARGA DE DATOS ---
col1, col2 = st.columns(2)
f_yo = col1.file_uploader("👤 Subir Mis Ciudades", type=['png', 'jpg'])
f_amigos = col2.file_uploader("👥 Subir Ciudades Amigos", type=['png', 'jpg'], accept_multiple_files=True)

if f_yo and f_amigos:
    df_yo = procesar_captura(f_yo)
    df_amigos_total = pd.DataFrame()
    for f in f_amigos:
        df_amigos_total = pd.concat([df_amigos_total, procesar_captura(f)])
    
    # --- APARTADO 1: BIBLIOTECA ---
    st.divider()
    st.subheader("📋 Biblioteca de Ciudades")
    tab1, tab2 = st.tabs(["Mis Ciudades", "Ciudades Amigos"])
    tab1.table(df_yo)
    tab2.table(df_amigos_total)
    
    # --- APARTADO 2: MOTOR DE RECOMENDACIÓN ---
    st.divider()
    st.subheader("🎯 Recomendaciones de Emparejamiento")
    matches = []
    for _, yo in df_yo.iterrows():
        for _, amigo in df_amigos_total.iterrows():
            dif_edif = abs(yo['Edificios'] - amigo['Edificios'])
            dif_pob = abs(yo['Poblacion'] - amigo['Poblacion'])
            
            if dif_edif <= 20 and dif_pob <= 4999:
                matches.append({
                    "Mi ID": yo['ID'],
                    "Mi Ciudad": yo['Nombre'],
                    "Ciudad Amigo": amigo['Nombre'],
                    "ID Amigo": amigo['ID'],
                    "Dif. Edificios": dif_edif,
                    "Dif. Población": dif_pob
                })
    
    if matches:
        res_df = pd.DataFrame(matches)
        # Ordenar por tu ID y luego por mejor coincidencia (menor diferencia total)
        res_df['Score'] = res_df['Dif. Edificios'] + (res_df['Dif. Población'] / 1000)
        res_df = res_df.sort_values(by=["Mi ID", "Score"])
        st.table(res_df.drop(columns=['Score']))
    else:
        st.warning("No se encontraron ciudades que cumplan el rango de ±4999 población y ±20 edificios.")
