import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas - Alianza", layout="wide")

st.title("⚔️ Optimizador de Rutas y Emparejamiento")
st.write("Gestiona tus ciudades prioritarias y crúzalas con el banco de datos de tus amigos.")

# --- BASE DE DATOS EN MEMORIA (Separada en Mis Ciudades y Amigos) ---
if "mis_ciudades" not in st.session_state:
    st.session_state["mis_ciudades"] = {}
if "ciudades_amigos" not in st.session_state:
    st.session_state["ciudades_amigos"] = {}

# --- MENÚ LATERAL ---
st.sidebar.header("⚙️ Ajuste de Rangos Máximos")
max_pob = st.sidebar.slider("Diferencia Máxima de Población", min_value=100, max_value=10000, value=4999, step=1)
max_edi = st.sidebar.slider("Diferencia Máxima de Edificios", min_value=1, max_value=50, value=20, step=1)

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Limpiar Todo", help="Borra todas las imágenes cargadas para empezar de cero"):
    st.session_state["mis_ciudades"] = {}
    st.session_state["ciudades_amigos"] = {}
    st.success("¡Base de datos limpia!")
    st.rerun()

# Inicializar IA
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

# Función interna para procesar imágenes y extraer datos limpios
def procesar_captura(archivos_subidos):
    ciudades_extraidas = {}
    for archivo in archivos_subidos:
        file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)
        resultados_ocr = reader.readtext(image)
        
        lineas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            for y_base in lineas.keys():
                if abs(y_base - y_centro) < 16:
                    lineas[y_base].append((bbox[0][0], texto))
                    encontrado = True
                    break
            if not encontrado:
                lineas[y_centro] = [(bbox[0][0], texto)]

        for y_coord in sorted(lineas.keys()):
            bloques_ordenados = sorted(lineas[y_coord], key=lambda x: x[0])
            textos_fila = [b[1] for b in bloques_ordenados]
            
            numeros_fila = []
            for t in textos_fila:
                limpio = t.replace('.', '').replace(',', '').replace(' ', '').strip()
                if limpio.isdigit():
                    numeros_fila.append(int(limpio))
            
            if len(numeros_fila) >= 3:
                id_ciudad = numeros_fila[0]
                poblacion = numeros_fila[1]
                edificios = numeros_fila[-1]
                
                nombre_ciudad = "Desconocido"
                if len(textos_fila) > 1 and not textos_fila[1].replace('.', '').strip().isdigit():
                    nombre_ciudad = textos_fila[1].strip()
                
                ciudades_extraidas[id_ciudad] = {
                    "ID": id_ciudad,
                    "Nombre": nombre_ciudad,
                    "Población": poblacion,
                    "Edificios": edificios
                }
    return ciudades_extraidas

# --- INTERFAZ DE DOS CUADROS SEPARADOS ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("👤 1. MIS CIUDADES (Prioritarias - Necesitan Ruta)")
    mis_archivos = st.file_uploader("Sube TU captura de pantalla aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="mis_ciudades_uploader")
    if mis_archivos:
        datos = procesar_captura(mis_archivos)
        st.session_state["mis_ciudades"].update(datos)
    
    # Mostrar mis ciudades guardadas
    if st.session_state["mis_ciudades"]:
        st.dataframe(list(st.session_state["mis_ciudades"].values()), use_container_width=True)

with col_der:
    st.subheader("👥 2. CIUDADES DE MIS AMIGOS (Objetivos/Aliados)")
    archivos_amigos = st.file_uploader("Sube las capturas de tus AMIGOS aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="amigos_uploader")
    if archivos_amigos:
        datos_amigos = procesar_captura(archivos_amigos)
        st.session_state["ciudades_amigos"].update(datos_amigos)
        
    # Mostrar ciudades de amigos guardadas
    if st.session_state["ciudades_amigos"]:
        st.dataframe(list(st.session_state["ciudades_amigos"].values()), use_container_width=True)

st.markdown("---")

# --- LÓGICA DE EMPAREJAMIENTO DE RUTAS (Tus ciudades vs Amigos) ---
st.subheader("🎯 Panel de Rutas Óptimas Generadas")

mis_ciudades_lista = list(st.session_state["mis_ciudades"].values())
amigos_ciudades_lista = list(st.session_state["ciudades_amigos"].values())

if mis_ciudades_lista and amigos_ciudades_lista:
    rutas_creadas = 0
    
    for mi_c in sorted(mis_ciudades_lista, key=lambda x: x["ID"]):
        opciones_validas = []
        
        # Buscar coincidencias UNICAMENTE en la lista de los amigos
        for ca in amigos_ciudades_lista:
            dif_pob = abs(mi_c["Población"] - ca["Población"])
            dif_edi = abs(mi_c["Edificios"] - ca["Edificios"])
            
            if dif_pob <= max_pob and dif_edi <= max_edi:
                opciones_validas.append({
                    "id_destino": ca["ID"],
                    "nombre_destino": ca["Nombre"],
                    "pob_destino": ca["Población"],
                    "edi_destino": ca["Edificios"],
                    "dif_poblacion": dif_pob,
                    "dif_edificios": dif_edi,
                    "prioridad": dif_pob + (dif_edi * 150)
                })
        
        # Mostrar las rutas si tu ciudad encontró amigos compatibles
        if opciones_validas:
            rutas_creadas += 1
            opciones_ordenadas = sorted(opciones_validas, key=lambda x: x["prioridad"])
            
            titulo_ruta = f"🚨 NECESITA RUTA: Tu Ciudad ID {mi_c['ID']} — {mi_c['Nombre']} ➔ Tiene {len(opciones_ordenadas)} opciones con tus amigos"
            with st.expander(titulo_ruta):
                st.markdown(f"**Tus datos actuales:** `{mi_c['Población']} Población` | `{mi_c['Edificios']} Edificios`")
                st.write("Mejores opciones encontradas en las capturas de tus amigos:")
                
                tabla_visual = []
                for opc in opciones_ordenadas:
                    relacion = "📈 Más alta" if opc["pob_destino"] > mi_c["Población"] else "📉 Más baja"
                    tabla_visual.append({
                        "ID Amigo": opc["id_destino"],
                        "Nombre Amigo": opc["nombre_destino"],
                        "Población": f"{opc['pob_destino']:,}",
                        "Edificios": opc["edi_destino"],
                        "Diferencia Pob.": f"{opc['dif_poblacion']:,}",
                        "Diferencia Edif.": opc["dif_edificios"],
                        "Tipo Objetivo": relacion
                    })
                st.table(tabla_visual)
                
    if rutas_creadas == 0:
        st.info("Tus ciudades no tienen opciones compatibles con las de tus amigos bajo los límites actuales.")
else:
    st.info("Por favor, asegúrate de subir al menos una captura en TU cuadro y otra captura en el cuadro de tus AMIGOS para trazar las rutas.")
