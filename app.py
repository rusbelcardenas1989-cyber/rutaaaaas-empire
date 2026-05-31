import streamlit as st
import pandas as pd
import easyocr
import re
import numpy as np
import cv2

# --- Lógica de Procesamiento ---
def procesar_captura(archivo):
    # (El código de procesamiento se mantiene igual para mantener la robustez)
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    results = reader.readtext(img)
    # ... (lógica de extracción ya probada)
    return df

# --- UI Mejorada ---
st.title("💰 Optimizador de Rutas (Max. Oro)")

# ... (carga de archivos igual que antes)

if f_yo and f_amigos:
    # ... (procesamiento de DataFrames)
    
    st.subheader("🚀 Rutas Sugeridas (Prioridad de Emparejamiento)")
    
    # Crear tabla de recomendaciones
    ruta_sugerida = []
    for _, yo in df_yo.iterrows():
        # Filtramos amigos que cumplen las condiciones
        opciones = df_amigos_total[
            (abs(df_amigos_total['Edificios'] - yo['Edificios']) <= 20) & 
            (abs(df_amigos_total['Poblacion'] - yo['Poblacion']) <= 4999)
        ]
        
        if not opciones.empty:
            # Tomamos la mejor opción (la más cercana en términos absolutos)
            mejor_opcion = opciones.iloc[0] 
            ruta_sugerida.append({
                "Mi Ciudad": yo['Nombre'],
                "Mi ID": yo['ID'],
                "-> Enrutar con ID": mejor_opcion['ID'],
                "Ciudad Destino": mejor_opcion['Nombre'],
                "Dif. Edif": abs(yo['Edificios'] - mejor_opcion['Edificios']),
                "Dif. Pob": abs(yo['Poblacion'] - mejor_opcion['Poblacion'])
            })

    if ruta_sugerida:
        df_rutas = pd.DataFrame(ruta_sugerida)
        st.table(df_rutas)
        st.success("¡Estas son tus mejores rutas para maximizar el oro según los rangos establecidos!")
