import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Filtros Calibrados", layout="wide")

st.title("⚔️ Panel de Control - Extractor Inteligente")
st.write("Sube tus capturas. Filtros ajustados: Población mínima 1,000 y Edificios máximos 330.")

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
        
        # Escaneo general inicial
        resultados_ocr = reader.readtext(img)
        
        # 1. Agrupar los bloques de texto por su altura (Fila vertical Y)
        filas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            for y_base in filas.keys():
                if abs(y_base - y_centro) < 18:  # Tolerancia de fila estándar
                    filas[y_base].append((bbox, texto))
                    encontrado = True
                    break
            if not encontrado:
                filas[y_centro] = [(bbox, texto)]
        
        # 2. Procesar cada fila analizando el contenido real del texto
        for y_coord in sorted(filas.keys()):
            bloques = sorted(filas[y_coord], key=lambda x: x[0][0][0]) # Izquierda a derecha
            
            id_detectado = None
            nombre_detectado = []
            numeros_fila = []
            
            for bbox, texto in bloques:
                texto_limpio = texto.strip()
                if not texto_limpio or any(w in texto_limpio.lower() for w in ["id", "nombre", "pob", "edi", "regi", "ciudad"]):
                    continue
                
                # Extraer solo dígitos numéricos puros
                solo_num = "".join([c for c in texto_limpio if c.isdigit()])
                x_inicio = bbox[0][0]
                
                if solo_num.isdigit() and len(solo_num) > 0:
                    val_num = int(solo_num)
                    numeros_fila.append((x_inicio, val_num))
                else:
                    # Si tiene letras, asumimos que es parte del Nombre
                    if len(texto_limpio) > 1:
                        nombre_detectado.append(texto_limpio)
            
            if numeros_fila:
                # El ID siempre es el número que está más a la izquierda de la fila
                numeros_ordenados_por_x = sorted(numeros_fila, key=lambda x: x[0])
                id_detectado = numeros_ordenados_por_x[0][1]
                
                # Descartamos el ID para analizar el resto de números (Población y Edificios)
                otros_numeros = [n[1] for n in numeros_ordenados_por_x[1:]]
                
                poblacion = 0
                edificios = 0
                
                for num in otros_numeros:
                    # NUEVA CONDICIÓN: Población mínima de 1k (1000)
                    if num >= 1000:
                        poblacion = num
                    # NUEVA CONDICIÓN: Edificios máximo de 330
                    elif 10 <= num <= 330:
                        edificios = num
                
                # Si por error el ID se procesó como un número de ciudad gigante, lo saltamos
                if id_detectado is not None and id_detectado < 1000:
                    nombre_final = " ".join(nombre_detectado) if nombre_detectado else f"Ciudad {id_detectado}"
                    
                    # Guardar solo si se logró rescatar al menos uno de los dos datos clave
                    if poblacion > 0 or edificios > 0:
                        ciudades_extraidas[id_detectado] = {
                            "ID": id_detectado,
                            "Nombre": nombre_final,
                            "Población": poblacion,
                            "Edificios": edificios
                        }
                    
    return ciudades_extraidas

# --- INTERFAZ GRÁFICA ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("👤 1. MIS CIUDADES (Prioritarias)")
    mis_archivos = st.file_uploader("Sube TU captura aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="mis_up")
    if mis_archivos:
        st.session_state["mis_ciudades"].update(procesar_tabla_inteligente(mis_archivos))
    
    if st.session_state["mis_ciudades"]:
        lista_mia = sorted(list(st.session_state["mis_ciudades"].values()), key=lambda x: x["ID"])
        st.dataframe
