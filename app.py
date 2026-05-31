import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor Preciso - Juego", layout="wide")
st.title("🎯 Optimizador Avanzado por Columnas Fijas")
st.write("Esta versión recorta la imagen en columnas verticales para que la IA no confunda Población con Edificios.")

@st.cache_resource
def load_ocr():
    # Usamos el modo "allowlist" en el lector para forzarlo a leer solo números
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

uploaded_file = st.file_uploader("Sube la captura de pantalla de la tabla...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img_original = cv2.imdecode(file_bytes, 1)
    
    # Dimensiones de la imagen
    alto, ancho, _ = img_original.shape
    
    # --- RECORTE POR COLUMNAS (Ajustado a la estructura de tu tabla) ---
    # Definimos qué porcentaje del ancho de la imagen corresponde a cada dato
    # ID: primer 15% | Población: del 48% al 60% | Edificios: del 90% al 100%
    col_id = img_original[:, 0:int(ancho * 0.15)]
    col_pob = img_original[:, int(ancho * 0.48):int(ancho * 0.60)]
    col_edi = img_original[:, int(ancho * 0.90):ancho]
    
    # Mostrar visualmente las columnas recortadas para control del usuario
    st.subheader("🔍 Así es como la IA ve tus columnas por separado:")
    c_visual1, c_visual2, c_visual3 = st.columns(3)
    with c_visual1: st.image(col_id, caption="Columna ID", use_container_width=True)
    with c_visual2: st.image(col_pob, caption="Columna Población", use_container_width=True)
    with c_visual3: st.image(col_edi, caption="Columna Edificios", use_container_width=True)
    
    with st.spinner("Procesando columnas numéricas de forma independiente..."):
        # Forzamos al OCR a buscar SOLO números para evitar confusiones con letras
        res_id = reader.readtext(col_id, allowlist='0123456789')
        res_pob = reader.readtext(col_pob, allowlist='0123456789., ')
        res_edi = reader.readtext(col_edi, allowlist='0123456789')
        
        # Función para agrupar las lecturas por su altura (Y) en la pantalla
        def extraer_por_filas(resultados_ocr):
            datos_filas = {}
            for (bbox, texto, prob) in resultados_ocr:
                y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
                limpio = texto.replace('.', '').replace(',', '').replace(' ', '').strip()
                if limpio.isdigit():
                    # Agrupar si están en un rango de 15 píxeles de altura
                    agrupado = False
                    for y_base in datos_filas.keys():
                        if abs(y_base - y_centro) < 15:
                            datos_filas[y_base] = int(limpio)
                            agrupado = True
                            break
                    if not agrupado:
                        datos_filas[y_centro] = int(limpio)
            return datos_filas

        ids_por_fila = extraer_por_filas(res_id)
        pob_por_fila = extraer_por_filas(res_pob)
        edi_por_fila = extraer_por_filas(res_edi)
        
        # Alinear los datos de las tres columnas usando la posición vertical (Y)
        ciudades_procesadas = []
        for y_id, id_val in ids_por_fila.items():
            pob_val = None
            edi_val = None
            
            # Buscar la población más cercana en altura (Y)
            for y_pob, p_val in pob_por_fila.items():
                if abs(y_id - y_pob) < 18:
                    pob_val = p_val
                    break
                    
            # Buscar los edificios más cercanos en altura (Y)
            for y_edi, e_val in edi_por_fila.items():
                if abs(y_id - y_edi) < 18:
                    edi_val = e_val
                    break
            
            # Solo guardamos si pudimos rescatar los tres datos de la fila
            if pob_val is not None and edi_val is not None:
                ciudades_procesadas.append({
                    "id": id_val,
                    "poblacion": pob_val,
                    "edificios": edi_val
                })

    # --- MOSTRAR RESULTADOS ---
    st.subheader("📋 Tabla Alineada Correctamente")
    if ciudades_procesadas:
        st.dataframe(ciudades_procesadas)
        
        st.subheader("🎯 Parejas Óptimas Encontradas")
        parejas = []
        n =
