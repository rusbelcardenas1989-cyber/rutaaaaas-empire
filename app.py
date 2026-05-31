import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(layout="wide")
st.title("⚔️ Extractor Directo y Final")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_fila_final(lista_texto):
    # Intentamos extraer números de la lista
    numeros = []
    nombre = ""
    
    for item in lista_texto:
        # Limpiar texto: quitar puntos de millar
        clean = str(item).replace(".", "").replace(",", "").strip()
        if clean.isdigit():
            numeros.append(int(clean))
        elif len(clean) > 3:
            nombre = clean
            
    # Asignación lógica basada en la estructura de tu imagen:
    # Si tenemos al menos 3 números: [ID, Población, Edificios]
    if len(numeros) >= 3:
        return {"ID": numeros[0], "Nombre": nombre, "Población": numeros[1], "Edificios": numeros[2]}
    # Si detecta ID y Población, pero no edificios, ponemos 0
    elif len(numeros) == 2:
        return {"ID": numeros[0], "Nombre": nombre, "Población": numeros[1], "Edificios": 0}
    return None

def procesar_imagen(archivo):
    file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    results = reader.readtext(img)
    
    # Agrupar elementos por altura (Y)
    filas = {}
    for (bbox, text, prob) in results:
        y = int(bbox[0][1])
        encontrado = False
        for y_base in filas:
            if abs(y_base - y) < 30:
                filas[y_base].append(text)
                encontrado = True
                break
        if not encontrado:
            filas[y] = [text]
            
    data = []
    for y in filas:
        resultado = procesar_fila_final(filas[y])
        if resultado and resultado["ID"] > 0:
            data.append(resultado)
    return data

# UI
files = st.file_uploader("Sube tus capturas", accept_multiple_files=True)
if files:
    todos_datos = []
    for f in files:
        todos_datos.extend(procesar_imagen(f))
    st.table(todos_datos)
