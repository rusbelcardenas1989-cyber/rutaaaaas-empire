import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas", layout="wide")
st.title("⚔️ Panel de Control - Extractor Estricto")

if "mis_ciudades" not in st.session_state: st.session_state["mis_ciudades"] = {}
if "ciudades_amigos" not in st.session_state: st.session_state["ciudades_amigos"] = {}

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_fila_posicional(bloques_brutos):
    # Filtrar solo elementos válidos [bbox, texto, prob]
    bloques_validos = [b for b in bloques_brutos if isinstance(b, (list, tuple)) and len(b) >= 2]
    
    # Ordenar estrictamente de izquierda a derecha por coordenada X
    bloques_validos.sort(key=lambda x: x[0][0][0])
    
    numeros = []
    nombre_partes = []
    
    for item in bloques_validos:
        texto = str(item[1]).replace(".", "").replace(",", "").strip()
        if texto.isdigit():
            numeros.append(int(texto))
        elif len(texto) > 2:
            nombre_partes.append(texto)
            
    datos = {"ID": 0, "Nombre": " ".join(nombre_partes), "Población": 0, "Edificios": 0}
    
    # Asignación posicional literal
    if len(numeros) >= 1: datos["ID"] = numeros[0]
    if len(numeros) >= 2: datos["Población"] = numeros[1]
    if len(numeros) >= 3: datos["Edificios"] = numeros[2]
                
    return datos

def procesar_imagen(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    resultados = reader.readtext(img)
    
    filas = {}
    for res in resultados:
        y = int((res[0][0][1] + res[0][2][1]) / 2)
        agrupado = False
        for y_base in filas:
            if abs(y_base - y) < 25:
                filas[y_base].append(res)
                agrupado = True
                break
        if not agrupado: filas[y] = [res]
            
    ciudades = {}
    for y in filas:
        if any("id" in str(b[1]).lower() for b in filas[y]): continue
        ciudad = procesar_fila_posicional(filas[y])
        if 0 < ciudad["ID"] < 1000: ciudades[ciudad["ID"]] = ciudad
    return ciudades

# --- UI ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("👤 Mis Ciudades")
    files = st.file_uploader("Sube tus capturas", accept_multiple_files=True, key="m")
    if files:
        for f in files: st.session_state["mis_ciudades"].update(procesar_imagen(f))
    st.dataframe(sorted(list(st.session_state["mis_ciudades"].values()), key=lambda x: x["ID"]))

with col2:
    st.subheader("👥 Ciudades Amigos")
    files2 = st.file_uploader("Sube capturas amigos", accept_multiple_files=True, key="a")
    if files2:
        for f in files2: st.session_state["ciudades_amigos"].update(procesar_imagen(f))
    st.dataframe(sorted(list(st.session_state["ciudades_amigos"].values()), key=lambda x: x["ID"]))
