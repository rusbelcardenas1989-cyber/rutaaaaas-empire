import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor Pro - Ciudades", layout="wide")
st.title("📊 Optimizador Pro de Ciudades (Mejorado)")
st.write("Esta versión incluye limpieza de imagen automática para mejorar la lectura de la tabla.")

# Inicializar OCR
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

# Controles laterales para dar margen de error si el OCR se equivoca en un dígito
st.sidebar.header("⚙️ Ajustes de Coincidencia")
margen_pob = st.sidebar.slider("Margen de error en Población", 0, 10, 0, help="Por si el OCR lee un número ligeramente mal")
margen_edi = st.sidebar.slider("Margen de error en Edificios", 0, 2, 0)

uploaded_file = st.file_uploader("Sube la captura de pantalla de tu juego...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, 1)
    
    # --- PROCESAMIENTO AVANZADO DE IMAGEN ---
    # 1. Convertir a escala de grises
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 2. Aplicar un filtro de umbral para dejar el texto negro y el fondo blanco puro
    # Esto elimina el color pergamino que confunde al OCR
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # Mostrar ambas imágenes para que veas la diferencia
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        st.image(image, caption="Imagen Original", use_container_width=True)
    with col_img2:
        st.image(thresh, caption="Imagen Limpiada para la IA", use_container_width=True)
    
    with st.spinner("Analizando texto con filtros de alta precisión..."):
        # Leemos la imagen limpia (en blanco y negro)
        resultados_ocr = reader.readtext(thresh)
        
        lineas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            # Agrupar por filas (margen de 18 píxeles de altura)
            for y_base in lineas.keys():
                if abs(y_base - y_centro) < 18:
                    lineas[y_base].append((bbox[0][0], texto)) # Guardamos también la posición X (izquierda a derecha)
                    encontrado = True
                    break
            if not getattr(st, "encontrado", encontrado):
                lineas[y_centro] = [(bbox[0][0], texto)]

        ciudades_procesadas = []
        
        for y_coord in sorted(lineas.keys()):
            # Ordenar los bloques de texto de izquierda a derecha usando la posición X
            bloques_ordenados = sorted(lineas[y_coord], key=lambda x: x[0])
            bloques_texto = [b[1] for b in bloques_ordenados]
            
            # Extraer solo los números limpios de la fila
            numeros = []
            for t in bloques_texto:
                # Quitar puntos, comas y espacios comunes en los números del juego
                limpio = t.replace('.', '').replace(',', '').replace(' ', '').strip()
                if limpio.isdigit():
                    numeros.append(int(limpio))
            
            # Una fila correcta del juego debe tener al menos: ID, Población, Edificios
            if len(numeros) >= 3:
                ciudades_procesadas.append({
                    "id": numeros[0],
                    "poblacion": numeros[1],
                    "edificios": numeros[-1]
                })

    st.subheader("📋 Datos detectados en la tabla")
    if ciudades_procesadas:
        st.dataframe(ciudades_procesadas)
        
        # --- ALGORITMO DE EMPAREJAMIENTO CON MARGEN DE ERROR ---
        st.subheader("🎯 Ciudades Óptimas Encontradas")
        parejas = []
        n = len(ciudades_procesadas)
        
        target_pob = 4999
        target_edi = 20
        
        for i in range(n):
            for j in range(i + 1, n):
                c1 = ciudades_procesadas[i]
                c2 = ciudades_procesadas[j]
                
                dif_pob = abs(c1["poblacion"] - c2["poblacion"])
                dif_edi = abs(c1["edificios"] - c2["edificios"])
                
                # Verificar si entra en el rango configurado en la barra lateral
                condicion_pob = (target_pob - margen_pob) <= dif_pob <= (target_pob + margen_pob)
                condicion_edi = (target_edi - margen_edi) <= dif_edi <= (target_edi + margen_edi)
                
                if condicion_pob and condicion_edi:
                    parejas.append((c1, c2, dif_pob, dif_edi))

        if parejas:
            for c1, c2, dp, de in parejas:
                st.success(f"¡Combinación válida encontrada!")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label=f"Ciudad ID {c1['id']}", value=f"{c1['edificios']} Edif", delta=f"{c1['poblacion']} Pob")
                with col2:
                    st.metric(label=f"Ciudad ID {c2['id']}", value=f"{c2['edificios']} Edif", delta=f"{c2['poblacion']} Pob")
                st.caption(f"Diferencias reales encontradas -> Población: {dp} | Edificios: {de}")
                st.write("---")
        else:
            st.info("No se encontraron ciudades con los rangos seleccionados en esta imagen.")
    else:
        st.error("No se pudo detectar ninguna fila con datos numéricos. Intenta recortar la imagen enfocando más la tabla.")
