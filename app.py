import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Modo Definitivo", layout="wide")

st.title("⚔️ Panel de Control - Extractor Inteligente")
st.write("Sube tus capturas. Clasificación matemática exacta por rangos de valores.")

# Almacenamiento en memoria
if "mis_ciudades" not in st.session_state:
    st.session_state["mis_ciudades"] = {}
if "ciudades_amigos" not in st.session_state:
    st.session_state["ciudades_amigos"] = {}

# Menú lateral
st.sidebar.header("⚙️ Ajuste de Rangos Máximos")
max_pob = st.sidebar.slider("Diferencia Máxima de Población", min_value=100, max_value=10000, value=4999, step=1)
max_edi = st.sidebar.slider("Diferencia Máxima de Edificios", min_value=1, max_value=50, value=20, step=1)

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Limpiar Base de Datos"):
    st.session_state["mis_ciudades"] = {}
    st.session_state["ciudades_amigos"] = {}
    st.rerun()

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_tabla_inteligente(archivos_subidos):
    ciudades_extraidas = {}
    
    for archivo in archivos_subidos:
        file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        # Escaneo general de la imagen
        resultados_ocr = reader.readtext(img)
        
        # 1. Agrupar bloques de texto por su altura (Filas horizontales Y)
        filas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            for y_base in filas.keys():
                if abs(y_base - y_centro) < 18:  # Tolerancia estándar de fila
                    filas[y_base].append((bbox, texto))
                    encontrado = True
                    break
            if not encontrado:
                filas[y_centro] = [(bbox, texto)]
        
        # 2. Procesar cada fila de forma lógica y sencilla
        for y_coord in sorted(filas.keys()):
            # Ordenar de izquierda a derecha de forma ultra-segura
            try:
                bloques = sorted(filas[y_coord], key=lambda x: x[0][0][0])
            except (IndexError, TypeError, ValueError):
                bloques = filas[y_coord]
            
            id_detectado = None
            nombre_detectado = []
            numeros_encontrados = []
            
            for bloque in bloques:
                try:
                    bbox, texto = bloque[0], bloque[1]
                    x_inicio = int(bbox[0][0])
                except (IndexError, TypeError, ValueError):
                    x_inicio = 0
                    if isinstance(bloque, tuple) and len(bloque) >= 2:
                        texto = bloque[1]
                    else:
                        continue
                
                texto_limpio = str(texto).strip()
                # Ignorar encabezados de la tabla
                if not texto_limpio or any(w in texto_limpio.lower() for w in ["id", "nombre", "pob", "edi", "regi", "ciudad"]):
                    continue
                
                # Extraer solo caracteres numéricos
                solo_num = "".join([c for c in texto_limpio if c.isdigit()])
                
                if solo_num.isdigit() and len(solo_num) > 0:
                    val_num = int(solo_num)
                    numeros_encontrados.append((x_inicio, val_num))
                else:
                    if len(texto_limpio) > 1:
                        nombre_detectado.append(texto_limpio)
            
            if numeros_encontrados:
                # Ordenamos de izquierda a derecha por posición X
                numeros_ordenados = sorted(numeros_encontrados, key=lambda x: x[0])
                
                # El primero de la izquierda es el ID
                id_detectado = int(numeros_ordenados[0][1])
                
                poblacion = 0
                edificios = 0
                
                # Evaluamos matemáticamente los demás números de la fila
                for _, num in numeros_ordenados[1:]:
                    if 1000 <= num <= 99999:
                        poblacion = num
                    elif 1 <= num <= 330:
                        edificios = num
                
                # Guardar la información si el ID es de ciudad válido
                if id_detectado is not None and id_detectado < 1000:
                    nombre_final = " ".join(nombre_detectado) if nombre_detectado else f"Ciudad {id_detectado}"
                    
                    ciudades_extraidas[id_detectado] = {
                        "ID": int(id_detectado),
                        "Nombre": str(nombre_final),
                        "Población": int(poblacion),
                        "Edificios": int(edificios)
                    }
                    
    return ciudades_extraidas

# --- INTERFAZ GRÁFICA ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("👤 1. MIS CIUDADES (Prioritarias)")
    mis_archivos = st.file_uploader("Sube TU captura aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="mis_up")
