import streamlit as st
import cv2
import numpy as np
import easyocr
import re

st.set_page_config(page_title="Extractor de Rutas - Estable", layout="wide")

st.title("⚔️ Panel de Control - Extracción Inteligente por Columnas")
st.write("Sube las capturas de pantalla. Esta versión corregida analiza el contenido de cada bloque para evitar mezclas.")

# Asegurar almacenamiento en memoria
if "mis_ciudades" not in st.session_state:
    st.session_state["mis_ciudades"] = {}
if "ciudades_amigos" not in st.session_state:
    st.session_state["ciudades_amigos"] = {}

# Menú lateral para rangos de estrategia
st.sidebar.header("⚙️ Ajuste de Rangos Máximos")
max_pob = st.sidebar.slider("Diferencia Máxima de Población", min_value=100, max_value=10000, value=4999, step=1)
max_edi = st.sidebar.slider("Diferencia Máxima de Edificios", min_value=1, max_value=50, value=20, step=1)

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Limpiar Todo"):
    st.session_state["mis_ciudades"] = {}
    st.session_state["ciudades_amigos"] = {}
    st.rerun()

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_tabla_robusta(archivos_subidos):
    ciudades_extraidas = {}
    
    for archivo in archivos_subidos:
        file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        # Lectura completa de la imagen por la IA
        resultados_ocr = reader.readtext(img)
        
        # Agrupar las cajas de texto por filas verticales (coordenada Y)
        filas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            x_inicio = bbox[0][0]
            
            encontrado = False
            for y_base in filas.keys():
                if abs(y_base - y_centro) < 15:  # Tolerancia de píxeles por fila
                    filas[y_base].append((x_inicio, texto))
                    encontrado = True
                    break
            if not encontrado:
                filas[y_centro] = [(x_inicio, texto)]
        
        # Analizar cada fila de forma independiente
        for y_coord in sorted(filas.keys()):
            # Ordenar bloques de izquierda a derecha (coordenada X)
            bloques = sorted(filas[y_coord], key=lambda x: x[0])
            
            id_detectado = None
            nombre_detectado = []
            numeros_encontrados = []
            
            for x_pos, texto in bloques:
                texto_limpio = texto.strip()
                if not texto_limpio:
                    continue
                
                # Quitar puntos y comas para verificar si es un número puro
                solo_num = texto_limpio.replace('.', '').replace(',', '').replace(' ', '')
                
                if solo_num.isdigit():
                    num_int = int(solo_num)
                    # Si está muy a la izquierda y tiene 3 dígitos, es un ID seguro
                    if id_detectado is None and num_int < 1000:
                        id_detectado = num_int
                    else:
                        numeros_encontrados.append(num_int)
                else:
                    # Si tiene letras, es parte del Nombre del jugador
                    # Ignoramos palabras del sistema como "ID", "Nombre", "Edif", "Región"
                    if len(texto_limpio) > 1 and not any(w in texto_limpio.lower() for w in ["id", "nombre", "edif", "regi", "ciudad"]):
                        nombre_detectado.append(texto_limpio)

            # Si logramos identificar al menos el ID y algún dato numérico extra
            if id_detectado is not None and len(numeros_encontrados) >= 1:
                # Reconstruir el nombre completo si se dividió en pedazos
                nombre_final = " ".join(nombre_detectado) if nombre_detectado else f"Ciudad {id_detectado}"
                
                # En tu juego la población siempre es un número grande (miles) y edificios es pequeño
                poblacion = 0
                edificios = 0
                
                # Filtrar si hay datos basura de otras columnas (como oro o recursos)
                # Nos quedamos con los que encajen en los rangos lógicos del juego
                for n in numeros_encontrados:
                    if 10000 <= n <= 90000:  # Rango típico de población de tus imágenes
                        poblacion = n
                    elif 10 <= n <= 200:     # Rango típico de edificios
                        edificios = n
                
                # Guardar solo si tiene datos mínimos coherentes
                if poblacion > 0 or edificios > 0:
                    ciudades_extraidas[id_detectado] = {
                        "ID": id_detectado,
                        "Nombre": nombre_final,
                        "Población": poblacion,
                        "Edificios": edificios
                    }
                    
    return ciudades_extraidas

# --- INTERFAZ VISUAL ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("👤 1. MIS CIUDADES (Prioritarias)")
    mis_archivos = st.file_uploader("Sube TU captura aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="mis_up")
    if mis_archivos:
        st.session_state["mis_ciudades"].update(procesar_tabla_robusta(mis_archivos))
    
    if st.session_state["mis_ciudades"]:
        lista_mia = sorted(list(st.session_state["mis_ciudades"].values()), key=lambda x: x["ID"])
        st.dataframe(lista_mia, use_container_width=True)

with col_der:
    st.subheader("👥 2. CIUDADES DE MIS AMIGOS")
    archivos_amigos = st.file_uploader("Sube las de tus AMIGOS aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ami_up")
    if archivos_amigos:
        st.session_state["ciudades_amigos"].update(procesar_tabla_robusta(archivos_amigos))
    
    if st.session_state["ciudades_amigos"]:
        lista_amigos = sorted(list(st.session_state["ciudades_amigos"].values()), key=lambda x: x["ID"])
        st.dataframe(lista_amigos, use_container_width=True)

st.markdown("---")

# --- PANEL DE RUTAS ---
st.subheader("🎯 Panel de Rutas Óptimas")

mis_ciudades_lista = list(st.session_state["mis_ciudades"].values())
amigos_ciudades_lista = list(st.session_state["ciudades_amigos"].values())

if mis_ciudades_lista and amigos_ciudades_lista:
    rutas_creadas = 0
    
    for mi_c in sorted(mis_ciudades_lista, key=lambda x: x["ID"]):
        opciones_validas = []
        for ca in amigos_ciudades_lista:
            dif_pob = abs(mi_c["Población"] - ca["Población"])
            dif_edi = abs(mi_c["Edificios"] - ca["Edificios"])
            
            if dif_pob <= max_pob and dif_edi <= max_edi:
                opciones_validas.append({
                    "ID Amigo": ca["ID"],
                    "Nombre Amigo": ca["Nombre"],
                    "Población": f"{ca['Población']:,}",
                    "Edificios": ca["Edificios"],
                    "Dif. Población": f"{dif_pob:,}",
                    "Dif. Edificios": dif_edi,
                    "Posición": "📈 Más alta" if ca["Población"] > mi_c["Población"] else "📉 Más baja"
                })
        
        if opciones_validas:
            rutas_creadas += 1
            with st.expander(f"🚨 RUTA PARA: {mi_c['Nombre']} [ID {mi_c['ID']}] ({mi_c['Población']:,} Pob | {mi_c['Edificios']} Edif)"):
                st.table(opciones_validas)
                
    if rutas_creadas == 0:
        st.info("No se encontraron ciudades que coincidan con los rangos establecidos.")
else:
    st.info("Sube capturas en ambos cuadros para activar el cálculo de rutas.")
