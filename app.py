import streamlit as st
import pandas as pd
import easyocr
import re
import numpy as np
import cv2

st.set_page_config(layout="wide", page_title="Optimizador de Rutas PRO")
st.title("💰 Optimizador de Rutas con Edición Manual")

# --- OCR ENGINE ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr()

def limpiar_num(texto):
    return int(re.sub(r'[^\d]', '', str(texto)))

def procesar_captura(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # Procesamiento para mejorar OCR
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    
    results = reader.readtext(thresh)
    
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
                data.append({"ID": t[0], "Nombre": t[1], "Poblacion": limpiar_num(t[2]), "Edificios": limpiar_num(t[3])})
            except: continue
    return pd.DataFrame(data)

# --- UI Y EDICIÓN ---
st.sidebar.header("📂 Carga de Datos")
f_yo = st.sidebar.file_uploader("👤 Subir Mis Ciudades", type=['png', 'jpg'])
f_amigos = st.sidebar.file_uploader("👥 Subir Amigos", type=['png', 'jpg'], accept_multiple_files=True)

if f_yo and f_amigos:
    # Procesar
    df_yo_raw = procesar_captura(f_yo)
    df_amigos_raw = pd.concat([procesar_captura(f) for f in f_amigos])
    
    # --- LA MAGIA: st.data_editor permite editar la tabla ---
    st.subheader("✏️ Edita tus datos (Si el OCR falló, corrige aquí)")
    df_yo = st.data_editor(df_yo_raw, key="editor_yo")
    df_amigos = st.data_editor(df_amigos_raw, key="editor_amigos")
    
    # --- MATRIZ DE COMPATIBILIDAD ---
    st.divider()
    st.subheader("🎯 Matriz de Emparejamiento (Datos Editados)")
    
    recomendaciones = []
    for _, yo in df_yo.iterrows():
        # Aquí usamos el df_amigos que ya pasó por el editor
        opciones = df_amigos[
            (abs(df_amigos['Edificios'] - yo['Edificios']) <= 20) & 
            (abs(df_amigos['Poblacion'] - yo['Poblacion']) <= 4999)
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
        st.warning("No se encontraron coincidencias con los datos actuales.")
else:
    st.info("Sube las imágenes para comenzar.")
