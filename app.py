import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Precisión Real", layout="wide")

st.title("⚔️ Panel de Control - Extractor de Alta Precisión")
st.write("Sube tus capturas. Sistema optimizado para forzar la lectura de Edificios reales mediante escaneo enfocado.")

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
        h_img, w_img, _ = img.shape
        
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
            
            # Guardamos límites de la fila para escaneos de rescate
            y_min = max(0, y_coord - 20)
            y_max = min(h_img, y_coord + 20)
            x_poblacion_fin = 0
            
            for bbox, texto in bloques:
                texto_limpio = texto.strip()
                if not texto_limpio or any(w in texto_limpio.lower() for w in ["id", "nombre", "pob", "edi", "regi", "ciudad"]):
                    continue
                
                # Extraer solo dígitos numéricos puros
                solo_num = "".join([c for c in texto_limpio if c.isdigit()])
                
                try:
                    x_inicio = int(bbox[0][0])
                    x_fin = int(bbox[1][0])
                except (IndexError, TypeError, ValueError):
                    x_inicio = 0
                    x_fin = 0
                
                if solo_num.isdigit() and len(solo_num) > 0:
                    val_num = int(solo_num)
                    numeros_fila.append((x_inicio, val_num))
                    if val_num >= 1000:
                        x_poblacion_fin = x_fin
                else:
                    if len(texto_limpio) > 1:
                        nombre_detectado.append(texto_limpio)
            
            if numeros_fila:
                # Ordenar todos los números encontrados de izquierda a derecha
                numeros_ordenados = sorted(numeros_fila, key=lambda x: x[0])
                
                # El primero siempre es el ID
                id_detectado = int(numeros_ordenados[0][1])
                
                poblacion = 0
                edificios = 0
                
                restantes = numeros_ordenados[1:]
                
                if len(restantes) == 1:
                    val = int(restantes[0][1])
                    if val >= 1000:
                        poblacion = val
                    else:
                        edificios = val
                elif len(restantes) >= 2:
                    poblacion = int(restantes[0][1])
                    edificios = int(restantes[1][1])
                
                # 🛠️ ESCANEO ENFOCADO DE RESCATE PARA EDIFICIOS REALES 🛠️
                # Si detectamos población pero los edificios quedaron en 0, obligamos al OCR a mirar la esquina derecha
                if poblacion >= 1000 and edificios == 0:
                    x_start = x_poblacion_fin if x_poblacion_fin > 0 else int(w_img * 0.75)
                    # Cortamos la zona exacta donde deberían estar los edificios en esa fila
                    zona_edificios = img[y_min:y_max, x_start:w_img]
                    
                    # Forzamos un escaneo ultra enfocado usando solo caracteres numéricos
                    res_rescate = reader.readtext(zona_edificios, allowlist='0123456789')
                    for (_, txt_r, _) in res_rescate:
                        txt_r_limpio = "".join([c for c in txt_r.strip() if c.isdigit()])
                        if txt_r_limpio.isdigit():
                            val_r = int(txt_r_limpio)
                            if 10 <= val_r <= 330:
                                edificios = val_r
                                break
                
                # Validar ID de ciudad correcto
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
    if mis_archivos:
        st.session_state["mis_ciudades"].update(procesar_tabla_inteligente(mis_archivos))
    
    if st.session_state["mis_ciudades"]:
        lista_mia = sorted(list(st.session_state["mis_ciudades"].values()), key=lambda x: x["ID"])
        st.dataframe(lista_mia, use_container_width=True)

with col_der:
    st.subheader("👥 2. CIUDADES DE MIS AMIGOS")
    archivos_amigos = st.file_uploader("Sube las de tus AMIGOS aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ami_up")
    if archivos_amigos:
        st.session_state["ciudades_amigos"].update(procesar_tabla_inteligente(archivos_amigos))
    
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
