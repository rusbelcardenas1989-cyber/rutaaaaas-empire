import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Ciudades", layout="wide")
st.title("📊 Optimizador de Ciudades")
st.write("Sube la captura de pantalla de tu tabla para encontrar las combinaciones óptimas (Diferencia: 20 edif. y 4999 pob.).")

@st.cache_resource
def load_ocr():
    # Carga el lector en español e inglés
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

uploaded_file = st.file_uploader("Arrastra aquí tu imagen...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, 1)
    
    st.image(image, caption="Imagen cargada", use_container_width=True)
    
    with st.spinner("Analizando datos..."):
        resultados_ocr = reader.readtext(image)
        
        lineas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            for y_base in lineas.keys():
                if abs(y_base - y_centro) < 15:
                    lineas[y_base].append(texto)
                    encontrado = True
                    break
            if not encontrado:
                lineas[y_centro] = [texto]

        ciudades_procesadas = []
        for y_coord in sorted(lineas.keys()):
            bloques = lineas[y_coord]
            numeros = []
            for b in bloques:
                limpio = b.replace('.', '').replace(',', '').strip()
                if limpio.isdigit():
                    numeros.append(int(limpio))
            
            # Buscamos filas que tengan al menos ID, Población y Edificios
            if len(numeros) >= 3:
                ciudades_procesadas.append({
                    "id": numeros[0],
                    "poblacion": numeros[1],
                    "edificios": numeros[-1]
                })

    st.subheader("📋 Datos detectados")
    st.dataframe(ciudades_procesadas)

    st.subheader("🎯 Parejas Óptimas Encontradas")
    parejas = []
    n = len(ciudades_procesadas)
    
    for i in range(n):
        for j in range(i + 1, n):
            c1 = ciudades_procesadas[i]
            c2 = ciudades_procesadas[j]
            
            dif_pob = abs(c1["poblacion"] - c2["poblacion"])
            dif_edi = abs(c1["edificios"] - c2["edificios"])
            
            if dif_pob == 4999 and dif_edi == 20:
                parejas.append((c1, c2))

    if parejas:
        for c1, c2 in parejas:
            st.success(f"¡Combinación perfecta!")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label=f"Ciudad ID {c1['id']}", value=f"{c1['edificios']} Edif", delta=f"{c1['poblacion']} Pob")
            with col2:
                st.metric(label=f"Ciudad ID {c2['id']}", value=f"{c2['edificios']} Edif", delta=f"{c2['poblacion']} Pob")
            st.write("---")
    else:
        st.info("No se encontraron ciudades con la diferencia exacta de 20 edif. y 4999 pob. en esta imagen.")
