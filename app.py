import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Extractor de Rutas Preciso", layout="wide")

st.title("⚔️ Panel de Control - Modo Ultra Preciso")
st.write("Esta versión corta la imagen internamente en columnas para asegurar que capture el 100% de las ciudades.")

if "mis_ciudades" not in st.session_state:
    st.session_state["mis_ciudades"] = {}
if "ciudades_amigos" not in st.session_state:
    st.session_state["ciudades_amigos"] = {}

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
    # allowlist fuerza a la IA a buscar ÚNICAMENTE números, eliminando fallos por letras
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

def procesar_captura_columnas(archivos_subidos):
    ciudades_extraidas = {}
    
    for archivo in archivos_subidos:
        file_bytes = np.asarray(bytearray(archivo.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        alto, ancho, _ = img.shape
        
        # OJO: Recortamos verticalmente solo las zonas numéricas de tus capturas
        # ID: 0% al 10% | Población: 45% al 62% | Edificios: 90% al 100%
        crop_id = img[:, 0:int(ancho * 0.10)]
        crop_pob = img[:, int(ancho * 0.45):int(ancho * 0.62)]
        crop_edi = img[:, int(ancho * 0.90):ancho]
        
        # Forzamos reconocimiento numérico estricto en cada pedazo
        res_id = reader.readtext(crop_id, allowlist='0123456789')
        res_pob = reader.readtext(crop_pob, allowlist='0123456789')
        res_edi = reader.readtext(crop_edi, allowlist='0123456789')
        
        # Agrupar lecturas por altura Y
        def organizar_columna(resultados):
            datos = {}
            for (bbox, texto, prob) in resultados:
                y = int((bbox[0][1] + bbox[2][1]) / 2)
                limpio = texto.replace('.', '').replace(',', '').strip()
                if limpio.isdigit():
                    datos[y] = int(limpio)
            return datos
        
        dict_ids = organizar_columna(res_id)
        dict_pobs = organizar_columna(res_pob)
        dict_edis = organizar_columna(res_edi)
        
        # Alinear las 3 columnas de forma flexible (margen de 25 píxeles de tolerancia en altura)
        for y_id, v_id in dict_ids.items():
            v_pob = None
            v_edi = None
            
            for y_pob, p_val in dict_pobs.items():
                if abs(y_id - y_pob) < 25:
                    v_pob = p_val
                    break
            
            for y_edi, e_val in dict_edis.items():
                if abs(y_id - y_edi) < 25:
                    v_edi = e_val
                    break
            
            # Si logramos rescatar ID y al menos uno de los datos, lo agregamos para no perder la fila
            if v_pob is not None or v_edi is not None:
                ciudades_extraidas[v_id] = {
                    "ID": v_id,
                    "Nombre": f"Ciudad {v_id}",
                    "Población": v_pob if v_pob else 0,
                    "Edificios": v_edi if v_edi else 0
                }
                
    return ciudades_extraidas

# --- INTERFAZ ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("👤 1. MIS CIUDADES (Prioritarias)")
    mis_archivos = st.file_uploader("Sube TU captura aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="mis_up")
    if mis_archivos:
        st.session_state["mis_ciudades"].update(procesar_captura_columnas(mis_archivos))
    if st.session_state["mis_ciudades"]:
        st.dataframe(list(st.session_state["mis_ciudades"].values()), use_container_width=True)

with col_der:
    st.subheader("👥 2. CIUDADES DE MIS AMIGOS")
    archivos_amigos = st.file_uploader("Sube las de tus AMIGOS aquí...", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ami_up")
    if archivos_amigos:
        st.session_state["ciudades_amigos"].update(procesar_captura_columnas(archivos_amigos))
    if st.session_state["ciudades_amigos"]:
        st.dataframe(list(st.session_state["ciudades_amigos"].values()), use_container_width=True)

st.markdown("---")
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
                    "id_destino": ca["ID"],
                    "pob_destino": ca["Población"],
                    "edi_destino": ca["Edificios"],
                    "dif_poblacion": dif_pob,
                    "dif_edificios": dif_edi
                })
        
        if opciones_validas:
            rutas_creadas += 1
            with st.expander(f"🚨 RUTA PARA ID {mi_c['ID']} ({mi_c['Población']} Pob | {mi_c['Edificios']} Edif)"):
                st.table(opciones_validas)
    if rutas_creadas == 0:
        st.info("No hay coincidencias con los rangos actuales.")
else:
    st.info("Sube imágenes en ambos cuadros para calcular.")
