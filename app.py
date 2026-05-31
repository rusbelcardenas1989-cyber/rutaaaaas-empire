import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Optimizador de Ciudades", layout="wide")

st.title("⚔️ Optimizador de Emparejamientos para el Juego")
st.write("Sube tu captura. El sistema buscará ciudades con diferencias hacia arriba o hacia abajo según los límites.")

# --- MENÚ LATERAL DE CONFIGURACIÓN ---
st.sidebar.header("⚙️ Configuración de Límites")
st.sidebar.write("Define las diferencias máximas permitidas (hacia arriba o hacia abajo):")

# Configuración de los máximos solicitados por el usuario
max_pob = st.sidebar.slider("Diferencia Máxima de Población", min_value=100, max_value=10000, value=4999, step=1)
max_edi = st.sidebar.slider("Diferencia Máxima de Edificios", min_value=1, max_value=50, value=20, step=1)

# Inicializar el motor de IA
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

uploaded_file = st.file_uploader("Arrastra aquí la captura de pantalla de la tabla...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, 1)
    
    st.image(image, caption="Tabla cargada para analizar", use_container_width=True)
    
    with st.spinner("La IA está leyendo las columnas de la tabla..."):
        resultados_ocr = reader.readtext(image)
        
        # Agrupar las lecturas por filas (coordenada Y de la pantalla)
        lineas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            for y_base in lineas.keys():
                if abs(y_base - y_centro) < 15:
                    lineas[y_base].append((bbox[0][0], texto))
                    encontrado = True
                    break
            if not encontrado:
                lineas[y_centro] = [(bbox[0][0], texto)]

        ciudades_procesadas = []
        for y_coord in sorted(lineas.keys()):
            bloques_ordenados = sorted(lineas[y_coord], key=lambda x: x[0])
            bloques_texto = [b[1] for b in bloques_ordenados]
            
            numeros = []
            for t in bloques_texto:
                limpio = t.replace('.', '').replace(',', '').replace(' ', '').strip()
                if limpio.isdigit():
                    numeros.append(int(limpio))
            
            # Identificar ID, Población (columna central) y Edificios (última columna)
            if len(numeros) >= 3:
                ciudades_procesadas.append({
                    "id": numeros[0],
                    "poblacion": numeros[1],
                    "edificios": numeros[-1]
                })

    st.subheader("📋 Datos reconocidos por la IA")
    if ciudades_procesadas:
        st.dataframe(ciudades_procesadas)
        
        # --- ALGORITMO DE EMPAREJAMIENTO (MÁXIMOS HACIA ARRIBA Y ABAJO) ---
        st.subheader("🎯 Parejas Encontradas dentro del Rango")
        parejas_validas = []
        n = len(ciudades_procesadas)
        
        for i in range(n):
            for j in range(i + 1, n):
                c1 = ciudades_procesadas[i]
                c2 = ciudades_procesadas[j]
                
                # Al usar abs(), medimos la diferencia sin importar quién esté arriba o abajo
                dif_pob = abs(c1["poblacion"] - c2["poblacion"])
                dif_edi = abs(c1["edificios"] - c2["edificios"])
                
                # Condición: que no superen los máximos definidos en la barra lateral
                if dif_pob <= max_pob and dif_edi <= max_edi:
                    parejas_validas.append((c1, c2, dif_pob, dif_edi))

        if parejas_validas:
            st.info(f"Se encontraron {len(parejas_validas)} combinaciones que se llevan como máximo {max_pob} pob. y {max_edi} edif.")
            
            for c1, c2, dp, de in parejas_validas:
                # Determinar cuál está arriba y cuál abajo para mostrárselo claro al usuario
                if c1["poblacion"] >= c2["poblacion"]:
                    superior, inferior = c1, c2
                else:
                    superior, inferior = c2, c1
                
                with st.expander(f"➔ Pareja: ID {superior['id']} e ID {inferior['id']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Ciudad Más Alta (ID {superior['id']}):**")
                        st.write(f"📈 {superior['poblacion']} Población | 🏛️ {superior['edificios']} Edificios")
                    with col2:
                        st.markdown(f"**Ciudad Más Baja (ID {inferior['id']}):**")
                        st.write(f"📉 {inferior['poblacion']} Población | 🏛️ {inferior['edificios']} Edificios")
                    st.caption(f"Diferencias netas actuales: Diferencia Población = {dp} | Diferencia Edificios = {de}")
        else:
            st.warning("No se hallaron ciudades que cumplan con los rangos establecidos en esta imagen.")
    else:
        st.error("No se pudieron extraer datos numéricos. Asegúrate de que la tabla sea legible.")
