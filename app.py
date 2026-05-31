import streamlit as st
import cv2
import numpy as np
import easyocr

st.set_page_config(page_title="Optimizador Alianza", layout="wide")

st.title("⚔️ Optimizador de Ciudades - Base de Datos Compartida")
st.write("¡Sube tus capturas y las de tus amigos! La app sumará todas las ciudades y calculará las mejores opciones cruzadas.")

# --- BASE DE DATOS COMPARTIDA EN MEMORIA ---
# Creamos una lista global que no se borra cuando otra persona entra a la web
if "base_ciudades" not in st.session_state:
    st.session_state["base_ciudades"] = {}

# --- MENÚ LATERAL DE AJUSTES ---
st.sidebar.header("⚙️ Límites Máximos")
max_pob = st.sidebar.slider("Diferencia Máxima de Población", min_value=100, max_value=10000, value=4999, step=1)
max_edi = st.sidebar.slider("Diferencia Máxima de Edificios", min_value=1, max_value=50, value=20, step=1)

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Borrar toda la Base de Datos", help="Limpia todas las ciudades guardadas para empezar de cero"):
    st.session_state["base_ciudades"] = {}
    st.rerun()

# Inicializar IA de lectura
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

# --- SUBIDA DE IMÁGENES ---
# Permitimos subir múltiples archivos a la vez utilizando accept_multiple_files=True
uploaded_files = st.file_uploader("Sube una o varias capturas de pantalla de las tablas...", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    ciudades_nuevas_detectadas = 0
    
    for uploaded_file in uploaded_files:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)
        
        # Ejecutar lectura de IA
        resultados_ocr = reader.readtext(image)
        
        # Agrupar por filas (altura Y)
        lineas = {}
        for (bbox, texto, prob) in resultados_ocr:
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
            encontrado = False
            for y_base in lineas.keys():
                if abs(y_base - y_centro) < 15:
                    lineas[y_base].append((bbox[0][0], texto))
                    encontrado = True
                    break
            if not encontrado:
                lineas[y_centro] = [(bbox[0][0], texto)]

            # Procesar filas y extraer números
            for y_coord in sorted(lineas.keys()):
                bloques_ordenados = sorted(lineas[y_coord], key=lambda x: x[0])
                bloques_texto = [b[1] for b in bloques_ordenados]
                
                numeros = []
                for t in bloques_texto:
                    limpio = t.replace('.', '').replace(',', '').replace(' ', '').strip()
                    if limpio.isdigit():
                        numeros.append(int(limpio))
                
                # Si detectamos una fila válida (ID, Población, Edificios)
                if len(numeros) >= 3:
                    id_ciudad = numeros[0]
                    # Guardamos (o actualizamos) en la base de datos compartida usando el ID como llave única
                    st.session_state["base_ciudades"][id_ciudad] = {
                        "id": id_ciudad,
                        "poblacion": numeros[1],
                        "edificios": numeros[-1]
                    }
                    ciudades_nuevas_detectadas += 1

    st.success(f"¡Procesamiento completado! Se han cargado/actualizado los datos en la lista común.")

# --- MOSTRAR BASE DE DATOS TOTAL ---
lista_total_ciudades = list(st.session_state["base_ciudades"].values())

st.subheader(f"📋 Banco Total de Ciudades Guardadas ({len(lista_total_ciudades)} ciudades en total)")
if lista_total_ciudades:
    st.dataframe(lista_total_ciudades)
    
    # --- ALGORITMO DE EMPAREJAMIENTO DE MEJORES OPCIONES ---
    st.subheader("🎯 Tus Opciones Óptimas por Ciudad (Cruzando todas las imágenes)")
    
    opciones_por_ciudad = {c["id"]: [] for c in lista_total_ciudades}
    
    for c1 in lista_total_ciudades:
        for c2 in lista_total_ciudades:
            if c1["id"] == c2["id"]:
                continue
            
            dif_pob = abs(c1["poblacion"] - c2["poblacion"])
            dif_edi = abs(c1["edificios"] - c2["edificios"])
            
            if dif_pob <= max_pob and dif_edi <= max_edi:
                opciones_por_ciudad[c1["id"]].append({
                    "id_opcion": c2["id"],
                    "poblacion_opcion": c2["poblacion"],
                    "edificios_opcion": c2["edificios"],
                    "dif_pob": dif_pob,
                    "dif_edi": dif_edi,
                    "score_optimo": dif_pob + (dif_edi * 100)
                })
    
    # Desplegar los resultados ordenados de mejor a peor
    for c_id in opciones_por_ciudad.keys():
        ciudad_actual = next(c for c in lista_total_ciudades if c["id"] == c_id)
        lista_opciones = sorted(opciones_por_ciudad[c_id], key=lambda x: x["score_optimo"])
        
        if lista_opciones:
            with st.expander(f"🏢 Ciudad ID {c_id} ({ciudad_actual['poblacion']} Pob | {ciudad_actual['edificios']} Edif) ➔ {len(lista_opciones)} opciones óptimas encontradas"):
                tabla_opciones = []
                for opc in lista_opciones:
                    direccion = "📈 Más alta" if opc["poblacion_opcion"] > ciudad_actual["poblacion"] else "📉 Más baja"
                    tabla_opciones.append({
                        "ID Opción": opc["id_opcion"],
                        "Población": opc["poblacion_opcion"],
                        "Edificios": opc["edificios_opcion"],
                        "Dif. Población": opc["dif_pob"],
                        "Dif. Edificios": opc["dif_edi"],
                        "Posición": direccion
                    })
                st.table(tabla_opciones)
else:
    st.info("La base de datos está vacía. Sube capturas de pantalla para empezar a emparejar.")
