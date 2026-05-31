import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Estable", layout="wide")

st.title("⚔️ Panel de Control - Extracción por Orden de Columnas")
st.write("Esta versión asigna los datos estrictamente según su orden de izquierda a derecha en la tabla.")

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

def procesar_por_orden_columnas(archivos_subidos):
    ciudades_extraidas = {}
    
    for archivo in archivos_subidos:
        file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        resultados_ocr = reader.readtext(img)
        
        # 1. Agrupar los bloques de texto por su altura (Fila vertical Y)
        filas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            x_inicio = int(bbox[0][0])
            
            encontrado = False
            for y_base in filas.keys():
                if abs(y_base - y_centro) < 15:  # Tolerancia por fila
                    filas[y_base].append((x_inicio, texto))
                    encontrado = True
                    break
            if not encontrado:
                filas[y_centro] = [(x_inicio, texto)]
        
        # 2. Procesar cada fila basándonos en su orden horizontal
        for y_coord in sorted(filas.keys()):
            # Ordenamos los bloques de izquierda a derecha usando su coordenada X
            bloques_horizontales = sorted(filas[y_coord], key=lambda x: x[0])
            textos_fila = [b[1].strip() for b in bloques_horizontales if b[1].strip()]
            
            # Filtro para ignorar los encabezados de la tabla
            if any(w in "".join(textos_fila).lower() for w in ["id", "nombre", "pob", "edi", "regi"]):
                continue
                
            # Necesitamos que la fila tenga datos suficientes para procesar
            if len(textos_fila) >= 3:
                try:
                    # Columna 1 (Extrema izquierda): El ID
                    id_limpio = "".join([c for c in textos_fila[0] if c.isdigit()])
                    if not id_limpio:
                        continue
                    id_ciudad = int(id_limpio)
                    
                    # Columna 2: El Nombre
                    nombre_ciudad = textos_fila[1]
                    
                    # Columna 3: La Población
                    pob_limpio = "".join([c for c in textos_fila[2] if c.isdigit()])
                    poblacion = int(pob_limpio) if pob_limpio else 0
                    
                    # Columna 4 (Extrema derecha): Los Edificios
                    # Si la fila tiene 4 o más elementos, agarramos el último
                    if len(textos_fila) >= 4:
                        edi_limpio = "".join([c for c in textos_fila[-1] if c.isdigit()])
                        edificios = int(edi_limpio) if edi_limpio else 0
                    else:
                        edificios = 0
                    
                    # Si la población o los edificios se leyeron mal o quedaron en 0, 
                    # intentamos un intercambio lógico por si se cruzaron de posición
                    if edificios > poblacion and poblacion == 0:
                        poblacion = edificios
                        edificios = 0

                    # Guardar el registro si el ID es válido
                    if id_ciudad < 1000:
                        ciudades_extraidas[id_ciudad] = {
                            "ID": id_ciudad,
                            "Nombre": nombre_ciudad,
                            "Población": poblacion,
                            "Edificios": edificios
                        }
                except Exception:
                    continue
                    
    return ciudades_extraidas

# --- INTERFAZ GRÁFICA ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("👤 1. MIS CIUDADES (Prioritarias)")
    mis_archivos = st.file_uploader("Sube TU captura aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="mis_up")
    if mis_archivos:
        st.session_state["mis_ciudades"].update(procesar_por_orden_columnas(mis_archivos))
    
    if st.session_state["mis_ciudades"]:
        lista_mia = sorted(list(st.session_state["mis_ciudades"].values()), key=lambda x: x["ID"])
        st.dataframe(lista_mia, use_container_width=True)

with col_der:
    st.subheader("👥 2. CIUDADES DE MIS AMIGOS")
    archivos_amigos = st.file_uploader("Sube las de tus AMIGOS aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ami_up")
    if archivos_amigos:
        st.session_state["ciudades_amigos"].update(procesar_por_orden_columnas(archivos_amigos))
    
    if st.session_state["ciudades_amigos"]:
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
                st.write("Ciudades de tus amigos compatibles:")
                st.table(opciones_validas)
                
    if rutas_creadas == 0:
        st.info("No hay ciudades que coincidan con los rangos seleccionados.")
else:
    st.info("Sube capturas en ambos cuadros para calcular las rutas óptimas.")
