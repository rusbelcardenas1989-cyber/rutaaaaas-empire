import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Modo Inteligente", layout="wide")

st.title("⚔️ Panel de Control - Filtro de Columnas Inteligente")
st.write("Esta versión lee la imagen completa y separa los datos por su posición de izquierda a derecha. ¡No más IDs mezclados!")

# Bases de datos en memoria
if "mis_ciudades" not in st.session_state:
    st.session_state["mis_ciudades"] = {}
if "ciudades_amigos" not in st.session_state:
    st.session_state["ciudades_amigos"] = {}

# Menú lateral
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
    # Leemos texto completo para recuperar nombres e IDs reales
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_captura_inteligente(archivos_subidos):
    ciudades_extraidas = {}
    
    for archivo in archivos_subidos:
        file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        # Lectura de la imagen completa
        resultados_ocr = reader.readtext(img)
        
        # 1. Agrupar bloques de texto por su altura (Fila vertical Y)
        lineas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            for y_base in lineas.keys():
                if abs(y_base - y_centro) < 18:  # Tolerancia por fila
                    lineas[y_base].append((bbox[0][0], texto)) # Guardamos posición X (izquierda a derecha) y texto
                    encontrado = True
                    break
            if not encontrado:
                lineas[y_centro] = [(bbox[0][0], texto)]
        
        # 2. Procesar cada fila analizando las posiciones de izquierda a derecha
        for y_coord in sorted(lineas.keys()):
            # Ordenamos los elementos de la fila horizontalmente (Eje X)
            bloques_horizontales = sorted(lineas[y_coord], key=lambda x: x[0])
            textos_limpios = [b[1].strip() for b in bloques_horizontales]
            
            # Busquemos números válidos en la fila
            numeros = []
            for t in textos_limpios:
                num_limpio = t.replace('.', '').replace(',', '').replace(' ', '').strip()
                if num_limpio.isdigit():
                    numeros.append(int(num_limpio))
            
            # Una fila válida debe tener mínimo el ID al inicio y otros números
            if len(numeros) >= 3:
                # El primer número de la izquierda SIEMPRE es el ID
                id_ciudad = numeros[0]
                
                # El segundo número limpio (columna central) es la Población
                poblacion = numeros[1]
                
                # El último número a la extrema derecha SIEMPRE son los Edificios
                edificios = numeros[-1]
                
                # Buscar el nombre (suele ser el bloque de texto en la posición 2 o 3 de la izquierda)
                nombre_ciudad = f"Ciudad {id_ciudad}"
                for txt in textos_limpios[1:4]:
                    # Si el bloque contiene letras y no es un número puro, es el nombre del jugador
                    if not txt.replace('.', '').replace(',', '').strip().isdigit() and len(txt) > 2:
                        nombre_ciudad = txt
                        break
                
                # Validar que el ID tenga sentido (en tu juego son números de 3 dígitos usualmente)
                if id_ciudad < 1000:
                    ciudades_extraidas[id_ciudad] = {
                        "ID": id_ciudad,
                        "Nombre": nombre_ciudad,
                        "Población": poblacion,
                        "Edificios": edificios
                    }
                    
    return ciudades_extraidas

# --- INTERFAZ VISUAL (Dos columnas limpias) ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("👤 1. MIS CIUDADES (Prioritarias)")
    mis_archivos = st.file_uploader("Sube TU captura completa aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="mis_up")
    if mis_archivos:
        st.session_state["mis_ciudades"].update(procesar_captura_inteligente(mis_archivos))
    
    if st.session_state["mis_ciudades"]:
        lista_mia = sorted(list(st.session_state["mis_ciudades"].values()), key=lambda x: x["ID"])
        st.dataframe(lista_mia, use_container_width=True)

with col_der:
    st.subheader("👥 2. CIUDADES DE MIS AMIGOS")
    archivos_amigos = st.file_uploader("Sube las de tus AMIGOS aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ami_up")
    if archivos_amigos:
        st.session_state["ciudades_amigos"].update(procesar_captura_inteligente(archivos_amigos))
    
    if st.session_state["ciudades_amigos"]:
        lista_amigos = sorted(list(st.session_state["ciudades_amigos"].values()), key=lambda x: x["ID"])
        st.dataframe(lista_amigos, use_container_width=True)

st.markdown("---")

# --- GENERADOR TÁCTICO DE RUTAS ---
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
                st.write("Ciudades de tus amigos que entran en el rango:")
                st.table(opciones_validas)
                
    if rutas_creadas == 0:
        st.info("No se encontraron ciudades de amigos que coincidan con tus rangos.")
else:
    st.info("Sube imágenes en ambos cuadros para calcular las rutas.")
