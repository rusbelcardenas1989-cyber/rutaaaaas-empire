import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Optimizador por Ciudad", layout="wide")

st.title("⚔️ Panel de Opciones Óptimas por Ciudad")
st.write("Sube tu captura. La app agrupará y ordenará todas las opciones válidas para cada ciudad de forma individual.")

# --- MENÚ LATERAL DE CONFIGURACIÓN ---
st.sidebar.header("⚙️ Límites Máximos")
max_pob = st.sidebar.slider("Diferencia Máxima de Población", min_value=100, max_value=10000, value=4999, step=1)
max_edi = st.sidebar.slider("Diferencia Máxima de Edificios", min_value=1, max_value=50, value=20, step=1)

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

uploaded_file = st.file_uploader("Sube la captura de pantalla de la tabla...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, 1)
    
    st.image(image, caption="Tabla analizada", use_container_width=True)
    
    with st.spinner("La IA está leyendo y procesando la tabla..."):
        resultados_ocr = reader.readtext(image)
        
        # Agrupar lecturas por filas (coordenada Y)
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
            
            if len(numeros) >= 3:
                ciudades_procesadas.append({
                    "id": numeros[0],
                    "poblacion": numeros[1],
                    "edificios": numeros[-1]
                })

    st.subheader("📋 Tabla de Datos Detectados")
    if ciudades_procesadas:
        st.dataframe(ciudades_procesadas)
        
        # --- ALGORITMO: AGRUPAR OPCIONES POR CIUDAD ORIGEN ---
        st.subheader("🎯 Opciones Disponibles para cada Ciudad")
        
        # Creamos un diccionario para guardar las opciones de cada ID
        opciones_por_ciudad = {c["id"]: [] for c in ciudades_procesadas}
        
        # Cruzamos todas contra todas
        for c1 in ciudades_procesadas:
            for c2 in ciudades_procesadas:
                if c1["id"] == c2["id"]:
                    continue # No compararse consigo misma
                
                dif_pob = abs(c1["poblacion"] - c2["poblacion"])
                dif_edi = abs(c1["edificios"] - c2["edificios"])
                
                # Si cumple la condición de máximos (tanto arriba como abajo)
                if dif_pob <= max_pob and dif_edi <= max_edi:
                    # Guardamos la opción y la suma de diferencias para saber qué tan "óptima" es
                    opciones_por_ciudad[c1["id"]].append({
                        "id_opcion": c2["id"],
                        "poblacion_opcion": c2["poblacion"],
                        "edificios_opcion": c2["edificios"],
                        "dif_pob": dif_pob,
                        "dif_edi": dif_edi,
                        "score_optimo": dif_pob + (dif_edi * 100) # Criterio de orden de mejor a peor
                    })
        
        # --- MOSTRAR EN PANTALLA ORGANIZADO ---
        ciudades_con_opciones = 0
        
        for c_id in opciones_por_ciudad.keys():
            ciudad_actual = next(c for c in ciudades_procesadas if c["id"] == c_id)
            lista_opciones = opciones_por_ciudad[c_id]
            
            # Ordenar las opciones: las más cercanas/óptimas primero
            lista_opciones = sorted(lista_opciones, key=lambda x: x["score_optimo"])
            
            if lista_opciones:
                ciudades_con_opciones += 1
                # Crear una pestaña colapsable para cada ciudad de la lista
                with st.expander(f"🏢 Ciudad ID {c_id} ({ciudad_actual['poblacion']} Pob | {ciudad_actual['edificios']} Edif) ➔ Tiene {len(lista_opciones)} opciones"):
                    
                    # Mostrar las opciones en una tabla limpia dentro de la pestaña
                    tabla_opciones = []
                    for opc in lista_opciones:
                        # Indicar si la opción está arriba o abajo en población respecto a la original
                        direccion = "📈 Más alta" if opc["poblacion_opcion"] > ciudad_actual["poblacion"] else "📉 Más baja"
                        
                        tabla_opciones.append({
                            "ID Opción": opc["id_opcion"],
                            "Población": opc["poblacion_opcion"],
                            "Edificios": opc["edificios_opcion"],
                            "Dif. Población": opc["dif_pob"],
                            "Dif. Edificios": opc["dif_edi"],
                            "Tipo Relación": direccion
                        })
                    
                    st.table(tabla_opciones)
                    
        if ciudades_con_opciones == 0:
            st.warning("Ninguna ciudad tiene opciones válidas con los límites actuales.")
            
    else:
        st.error("No se pudieron extraer datos válidos de la imagen.")
