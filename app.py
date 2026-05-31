import streamlit as st
import cv2
import numpy as np
import easyocr

# 1. Configuración de la interfaz de la página
st.set_page_config(page_title="Optimizador de Ciudades Pro", layout="wide")

st.title("⚔️ Panel de Control y Emparejamiento de Ciudades")
st.write("Sube tus capturas (puedes subir varias a la vez). La app extraerá los datos y ordenará las mejores opciones por ciudad.")

# 2. Base de datos global en memoria (Almacena los datos de todos los usuarios)
if "base_ciudades" not in st.session_state:
    st.session_state["base_ciudades"] = {}

# 3. Menú lateral con controles de rangos máximos
st.sidebar.header("⚙️ Ajuste de Rangos Máximos")
st.sidebar.write("Define los límites máximos de diferencia permitidos (hacia arriba o hacia abajo):")

max_pob = st.sidebar.slider("Diferencia Máxima de Población", min_value=100, max_value=10000, value=4999, step=1)
max_edi = st.sidebar.slider("Diferencia Máxima de Edificios", min_value=1, max_value=50, value=20, step=1)

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Limpiar Base de Datos", help="Borra todas las ciudades para cargar capturas nuevas"):
    st.session_state["base_ciudades"] = {}
    st.success("¡Base de datos vaciada!")
    st.rerun()

# 4. Inicialización del motor de Inteligencia Artificial (OCR)
@st.cache_resource
def load_ocr():
    # Detecta texto e idioma estándar
    return easyocr.Reader(['es', 'en'], gpu=False)

reader = load_ocr()

# 5. Zona de subida de archivos (Soporta múltiples imágenes arrastradas juntas)
uploaded_files = st.file_uploader(
    "Arrastra o selecciona una o varias capturas de pantalla de tus tablas...", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

# 6. Procesamiento de las imágenes cargadas
if uploaded_files:
    with st.spinner("La IA está leyendo y organizando los datos de las imágenes..."):
        for uploaded_file in uploaded_files:
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, 1)
            
            # Ejecutar la lectura de texto de EasyOCR
            resultados_ocr = reader.readtext(image)
            
            # Agrupar lecturas por su altura (eje Y) para reconstruir las filas reales
            lineas = {}
            for (bbox, texto, prob) in resultados_ocr:
                y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
                encontrado = False
                for y_base in lineas.keys():
                    if abs(y_base - y_centro) < 16:  # Margen de píxeles para pertenecer a la misma fila
                        lineas[y_base].append((bbox[0][0], texto)) # Guardamos posición X y texto
                        encontrado = True
                        break
                if not encontrado:
                    lineas[y_centro] = [(bbox[0][0], texto)]

            # Extraer y mapear de forma ordenada: ID -> Nombre -> Población -> Edificios
            for y_coord in sorted(lineas.keys()):
                # Ordenar los bloques de la fila de izquierda a derecha usando el eje X
                bloques_ordenados = sorted(lineas[y_coord], key=lambda x: x[0])
                textos_fila = [b[1] for b in bloques_ordenados]
                
                # Filtrar solo los elementos que son números puros
                numeros_fila = []
                for t in textos_fila:
                    limpio = t.replace('.', '').replace(',', '').replace(' ', '').strip()
                    if limpio.isdigit():
                        numeros_fila.append(int(limpio))
                
                # Una fila del juego siempre tiene mínimo: ID (primero), Población (medio), Edificios (último)
                if len(numeros_fila) >= 3:
                    id_ciudad = numeros_fila[0]
                    poblacion = numeros_fila[1]
                    edificios = numeros_fila[-1] # Tomamos siempre la última columna numérica detectada (Edif)
                    
                    # Tratar de capturar el nombre (suele estar en la segunda posición de texto)
                    nombre_ciudad = "Desconocido"
                    if len(textos_fila) > 1:
                        # Si el segundo bloque no es número, asumimos que es el nombre
                        if not textos_fila[1].replace('.', '').strip().isdigit():
                            nombre_ciudad = textos_fila[1].strip()
                    
                    # Insertar o actualizar en la base de datos compartida usando el ID como clave única
                    st.session_state["base_ciudades"][id_ciudad] = {
                        "ID": id_ciudad,
                        "Nombre": nombre_ciudad,
                        "Población": poblacion,
                        "Edificios": edificios
                    }

# 7. Convertir la base de datos compartida en una lista para operar matemáticamente
lista_maestra = list(st.session_state["base_ciudades"].values())

# Mostrar la tabla general con todas las ciudades acumuladas
st.subheader(f"📋 Banco de Ciudades Cargadas ({len(lista_maestra)} en total)")
if lista_maestra:
    # Ordenar la tabla visual por ID para que se vea organizada
    lista_maestra_ordenada = sorted(lista_maestra, key=lambda x: x["ID"])
    st.dataframe(lista_maestra_ordenada, use_container_width=True)
    
    # 8. ALGORITMO: Búsqueda y agrupación de opciones óptimas
    st.subheader("🎯 Opciones Óptimas Disponibles (Organizadas por Ciudad Origen)")
    
    # Estructura para almacenar las coincidencias de cada ciudad
    coincidencias_por_ciudad = {c["ID"]: [] for c in lista_maestra}
    
    # Comparar todas las ciudades contra todas las ciudades de la base de datos
    for c1 in lista_maestra:
        for c2 in lista_maestra:
            if c1["ID"] == c2["ID"]:
                continue # Evitar compararse consigo misma
            
            # Calcular las diferencias absolutas (evalúa automáticamente hacia arriba y hacia abajo)
            dif_pob = abs(c1["Población"] - c2["Población"])
            dif_edi = abs(c1["Edificios"] - c2["Edificios"])
            
            # Evaluar si cumple con los rangos máximos establecidos en los sliders laterales
            if dif_pob <= max_pob and dif_edi <= max_edi:
                coincidencias_por_ciudad[c1["ID"]].append({
                    "id_destino": c2["ID"],
                    "nombre_destino": c2["Nombre"],
                    "pob_destino": c2["Población"],
                    "edi_destino": c2["Edificios"],
                    "dif_poblacion": dif_pob,
                    "dif_edificios": dif_edi,
                    # Score para ordenar: menor diferencia total = más arriba en la lista de mejores opciones
                    "prioridad": dif_pob + (dif_edi * 150) 
                })

    # 9. Mostrar en la interfaz los bloques desplegables organizados por ciudad
    ciudades_con_opciones = 0
    
    for c_id in sorted(coincidencias_por_ciudad.keys()):
        ciudad_origen = next(c for c in lista_maestra if c["ID"] == c_id)
        opciones_validas = coincidencias_por_ciudad[c_id]
        
        # Ordenar las opciones de la ciudad actual desde la más óptima a la menos óptima
        opciones_ordenadas = sorted(opciones_validas, key=lambda x: x["prioridad"])
        
        if opciones_ordenadas:
            ciudades_con_opciones += 1
            
            # Crear pestaña colapsable con el resumen de la ciudad de origen
            titulo_pestana = f"🏢 ID {c_id} — {ciudad_origen['Nombre']} ({ciudad_origen['Población']} Pob | {ciudad_origen['Edificios']} Edif) ➔ {len(opciones_ordenadas)} opciones óptimas"
            with st.expander(titulo_pestana):
                
                # Crear estructura de tabla limpia para mostrar los rivales/aliados dentro del desplegable
                tabla_visual = []
                for opc in opciones_ordenadas:
                    # Determinar de forma clara si el objetivo está por encima o por debajo en población
                    relacion = "📈 Más alta (+)" if opc["pob_destino"] > ciudad_origen["Población"] else "📉 Más baja (-)"
                    
                    tabla_visual.append({
                        "ID Opción": opc["id_destino"],
                        "Nombre": opc["nombre_destino"],
                        "Población": f"{opc['pob_destino']:,}",
                        "Edificios": opc["edi_destino"],
                        "Diferencia Pob.": f"{opc['dif_poblacion']:,}",
                        "Diferencia Edif.": opc["dif_edificios"],
                        "Ubicación Relativa": relacion
                    })
                
                st.table(tabla_visual)
                
    if ciudades_con_opciones == 0:
        st.warning("Ninguna de las ciudades guardadas tiene opciones válidas dentro de los rangos máximos actuales.")
else:
    st.info("El banco de datos está vacío. Sube capturas de pantalla de las tablas para guardar las ciudades y cruzarlas.")
