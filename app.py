import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Modo Definitivo", layout="wide")

st.title("⚔️ Panel de Control - Extractor de Alta Precisión")
st.write("Esta versión combina análisis posicional y escaneo de rescate para asegurar que NINGÚN edificio quede en 0.")

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

def procesar_tabla_definitiva(archivos_subidos):
    ciudades_extraidas = {}
    
    for archivo in archivos_subidos:
        file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        alto, ancho, _ = img.shape
        
        # Escaneo general inicial
        resultados_ocr = reader.readtext(img)
        
        # 1. Agrupar los bloques de texto por su altura (Fila vertical Y) con tolerancia amplia
        filas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            for y_base in filas.keys():
                if abs(y_base - y_centro) < 20:  # Tolerancia de 20 píxeles por fila
                    filas[y_base].append((bbox, texto))
                    encontrado = True
                    break
            if not Found:
                filas[y_centro] = [(bbox, texto)]
        
        # 2. Procesar cada fila analizando las posiciones geográficas en la pantalla
        for y_coord in sorted(filas.keys()):
            bloques = sorted(filas[y_coord], key=lambda x: x[0][0][0]) # Izquierda a derecha
            
            id_detectado = None
            nombre_detectado = []
            poblacion = 0
            edificios = 0
            
            # Recorrer bloques horizontalmente
            for bbox, texto in bloques:
                texto_limpio = texto.strip()
                if not texto_limpio or any(w in texto_limpio.lower() for w in ["id", "nombre", "pob", "edi", "regi"]):
                    continue
                
                # Extraer solo dígitos numéricos puros
                solo_num = "".join([c for c in texto_limpio if c.isdigit()])
                x_inicio = int(bbox[0][0])
                
                # Clasificación inteligente basada en la posición X en la pantalla
                if solo_num.isdigit() and len(solo_num) > 0:
                    val_num = int(solo_num)
                    
                    # Zona Izquierda (0% - 25%): ID de la ciudad
                    if x_inicio < (ancho * 0.25) and id_detectado is None and val_num < 1000:
                        id_detectado = val_num
                    
                    # Zona Centro (40% - 75%): Población
                    elif (ancho * 0.40) <= x_inicio <= (ancho * 0.75):
                        poblacion = val_num
                        
                    # Zona Derecha (76% - 100%): Edificios
                    elif x_inicio > (ancho * 0.75):
                        edificios = val_num
                else:
                    # Si contiene letras y está en la primera mitad, es el Nombre
                    if x_inicio < (ancho * 0.50) and len(texto_limpio) > 1:
                        nombre_detectado.append(texto_limpio)
            
            # 3. REFUERZO DE SEGURIDAD PARA EDIFICIOS
            # Si se detectó el ID pero la columna de edificios falló o quedó en 0
            if id_detectado is not None and edificios == 0:
                y_min = max(0, y_coord - 22)
                y_max = min(alto, y_coord + 22)
                x_min = int(ancho * 0.78)  # Enfocarse exclusivamente en el final derecho
                
                # Recorte quirúrgico del área de edificios de esta fila
                crop_edif = img[y_min:y_max, x_min:ancho]
                res_edif = reader.readtext(crop_edif, allowlist='0123456789')
                
                for _, t_edif, _ in res_edif:
                    t_limpio = "".join([c for c in t_edif if c.isdigit()])
                    if t_limpio.isdigit():
                        val_edi = int(t_limpio)
                        if 10 <= val_edi <= 250:  # Rango lógico de edificios
                            edificios = val_edi
                            break
            
            # Guardar el registro final si el ID es correcto
            if id_detectado is not None:
                nombre_final = " ".join(nombre_detectado) if nombre_detectado else f"Ciudad {id_detectado}"
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
        st.session_state["mis_ciudades"].update(procesar_tabla_definitiva(mis_archivos))
    
    if st.session_state["mis_ciudades"]:
        lista_mia = sorted(list(st.session_state["mis_ciudades"].values()), key=lambda x: x["ID"])
        st.dataframe(lista_mia, use_container_width=True)

with col_der:
    st.subheader("👥 2. CIUDADES DE MIS AMIGOS")
    archivos_amigos = st.file_uploader("Sube las de tus AMIGOS aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ami_up")
    if archivos_amigos:
        st.session_state["ciudades_amigos"].update(procesar_tabla_definitiva(archivos_amigos))
    
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
