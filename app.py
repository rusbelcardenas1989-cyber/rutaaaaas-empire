import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Modo Definitivo", layout="wide")

st.title("⚔️ Panel de Control - Extractor Inteligente")
st.write("Sube tus capturas. Clasificación matemática exacta por rangos de valores.")

# Almacenamiento en memoria permanente de la sesión
if "mis_ciudades" not in st.session_state:
    st.session_state["mis_ciudades"] = {}
if "ciudades_amigos" not in st.session_state:
    st.session_state["ciudades_amigos"] = {}

# Menú lateral de configuración
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
        
        # Escaneo directo con EasyOCR
        resultados_ocr = reader.readtext(img)
        
        # 1. Agrupar bloques de texto por filas horizontales (coordenada Y)
        filas = {}
        for elemento in resultados_ocr:
            bbox = elemento[0]
            texto = elemento[1]
            
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            
            encontrado = False
            for y_base in filas.keys():
                if abs(y_base - y_centro) < 18:  # Tolerancia de fila para agrupar en la misma línea
                    filas[y_base].append((bbox, texto))
                    encontrado = True
                    break
            if not encontrado:
                filas[y_centro] = [(bbox, texto)]
        
        # 2. Procesar fila por fila en orden de arriba hacia abajo
        for y_coord in sorted(filas.keys()):
            # Forzar el orden de los bloques de izquierda a derecha usando la coordenada X
            bloques = sorted(filas[y_coord], key=lambda x: x[0][0][0])
            
            id_detectado = None
            nombre_detectado = []
            numeros_encontrados = []
            
            for bbox, texto in bloques:
                texto_limpio = str(texto).strip()
                
                # Descartar los encabezados de la tabla
                if not texto_limpio or any(w in texto_limpio.lower() for w in ["id", "nombre", "pob", "edi", "regi", "ciudad"]):
                    continue
                
                # Extraer únicamente los dígitos numéricos
                solo_num = "".join([c for c in texto_limpio if c.isdigit()])
                
                if solo_num.isdigit() and len(solo_num) > 0:
                    val_num = int(solo_num)
                    x_inicio = int(bbox[0][0])
                    numeros_encontrados.append((x_inicio, val_num))
                else:
                    # Todo lo que no sea número puro va al Nombre
                    if len(texto_limpio) > 1:
                        nombre_detectado.append(texto_limpio)
            
            if numeros_encontrados:
                # Ordenar los números detectados estrictamente de izquierda a derecha
                numeros_ordenados = sorted(numeros_encontrados, key=lambda x: x[0])
                
                # El primer número de la izquierda es el ID de la ciudad
                id_detectado = int(numeros_ordenados[0][1])
                
                poblacion = 0
                edificios = 0
                
                # Clasificar matemáticamente los siguientes números por sus valores reales
                for _, num in numeros_ordenados[1:]:
                    if 1000 <= num <= 99999:
                        poblacion = num
                    elif 1 <= num <= 330:
                        edificios = num
                
                # Guardar en el diccionario final si el ID cumple con el formato estándar
                if id_detectado is not None and id_detectado < 1000:
                    nombre_final = " ".join(nombre_detectado) if nombre_detectado else f"Ciudad {id_detectado}"
                    
                    ciudades_extraidas[id_detectado] = {
                        "ID": int(id_detectado),
                        "Nombre": str(nombre_final),
                        "Población": int(poblacion),
                        "Edificios": int(edificios)
                    }
                    
    return ciudades_extraidas

# --- INTERFAZ GRÁFICA CORREGIDA (Visualización Fija) ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("👤 1. MIS CIUDADES (Prioritarias)")
    mis_archivos = st.file_uploader("Sube TU captura aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="mis_up")
    
    if mis_archivos:
        datos_mios = procesar_tabla_inteligente(mis_archivos)
        if datos_mios:
            st.session_state["mis_ciudades"].update(datos_mios)
    
    # Se muestra siempre la tabla, vacía o con datos cargados
    lista_mia = sorted(list(st.session_state["mis_ciudades"].values()), key=lambda x: x["ID"])
    st.dataframe(lista_mia, use_container_width=True)

with col_der:
    st.subheader("👥 2. CIUDADES DE MIS AMIGOS")
    archivos_amigos = st.file_uploader("Sube las de tus AMIGOS aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ami_up")
    
    if archivos_amigos:
        datos_amigos = procesar_tabla_inteligente(archivos_amigos)
        if datos_amigos:
            st.session_state["ciudades_amigos"].update(datos_amigos)
    
    # Se muestra siempre la tabla de amigos al lado derecho
    lista_amigos = sorted(list(st.session_state["ciudades_amigos"].values()), key=lambda x: x["ID"])
    st.dataframe(lista_amigos, use_container_width=True)

st.markdown("---")

# --- PROCESADOR TÁCTICO DE RUTAS ---
st.subheader("🎯 Panel de Rutas Óptimas")

mis_ciudades_lista = list(st.session_state["mis_ciudades"].values())
amigos_ciudades_lista = list(st.session_state["ciudades_amigos"].values())

if mis_ciudades_lista and amigos_ciudades_lista:
    rutas_creadas = 0
    
    for mi_c in sorted(mis_ciudades_lista, key=lambda x: x["ID"]):
        if int(mi_c["Población"]) == 0:
            continue
            
        opciones_validas = []
        for ca in amigos_ciudades_lista:
            if int(ca["Población"]) == 0:
                continue
                
            dif_pob = abs(int(mi_c["Población"]) - int(ca["Población"]))
            dif_edi = abs(int(mi_c["Edificios"]) - int(ca["Edificios"]))
            
            if dif_pob <= max_pob and dif_edi <= max_edi:
                opciones_validas.append({
                    "ID Amigo": int(ca["ID"]),
                    "Nombre Amigo": str(ca["Nombre"]),
                    "Población": int(ca["Población"]),
                    "Edificios": int(ca["Edificios"]),
                    "Dif. Población": int(dif_pob),
                    "Dif. Edificios": int(dif_edi),
                    "Posición": "📈 Más alta" if ca["Población"] > mi_c["Población"] else "📉 Más baja"
                })
        
        if opciones_validas:
            rutas_creadas += 1
            with st.expander(f"🚨 RUTA PARA: {mi_c['Nombre']} [ID {mi_c['ID']}] ({mi_c['Población']} Pob | {mi_c['Edificios']} Edif)"):
                st.write("Ciudades de tus amigos compatibles:")
                st.table(opciones_validas)
                
    if rutas_creadas == 0:
        st.info("No hay ciudades que coincidan con los rangos seleccionados.")
else:
    st.info("Sube capturas en ambos cuadros para calcular las rutas óptimas.")
