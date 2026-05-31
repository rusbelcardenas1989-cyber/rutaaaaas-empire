import streamlit as st
import cv2
import numpy as np
import pandas as pd
import easyocr

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

st.set_page_config(
    page_title="Extractor de Ciudades",
    layout="wide"
)

st.title("⚔️ Extractor de Ciudades")

# --------------------------------------------------
# OCR
# --------------------------------------------------

@st.cache_resource
def load_ocr():
    return easyocr.Reader(
        ['es', 'en'],
        gpu=False
    )

reader = load_ocr()

# --------------------------------------------------
# PROCESAMIENTO OCR
# --------------------------------------------------

def mejorar_imagen(img):

    # Escalar para ayudar al OCR
    img = cv2.resize(
        img,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    # Aumentar contraste
    gray = cv2.equalizeHist(gray)

    # Binarizar
    _, thresh = cv2.threshold(
        gray,
        150,
        255,
        cv2.THRESH_BINARY
    )

    return thresh


def limpiar_numero(texto):

    texto = str(texto)

    texto = texto.replace(".", "")
    texto = texto.replace(",", "")
    texto = texto.replace(" ", "")

    numeros = "".join(
        c for c in texto if c.isdigit()
    )

    return numeros


# --------------------------------------------------
# EXTRAER DATOS POR POSICIÓN
# --------------------------------------------------

def extraer_datos_fila(bloques):

    ciudad = {
        "ID": 0,
        "Nombre": "",
        "Población": 0,
        "Edificios": 0
    }

    nombres = []

    for box, texto in bloques:

        x = int(box[0][0])

        numero = limpiar_numero(texto)

        # --------------------------------
        # COLUMNA ID
        # --------------------------------
        if x < 150:

            if numero:
                ciudad["ID"] = int(numero)

        # --------------------------------
        # COLUMNA NOMBRE
        # --------------------------------
        elif x < 700:

            nombres.append(texto)

        # --------------------------------
        # COLUMNA POBLACIÓN
        # --------------------------------
        elif x < 1050:

            if numero:
                ciudad["Población"] = int(numero)

        # --------------------------------
        # COLUMNA EDIFICIOS
        # --------------------------------
        else:

            if numero:
                ciudad["Edificios"] = int(numero)

    ciudad["Nombre"] = " ".join(nombres)

    return ciudad


# --------------------------------------------------
# PROCESAR IMAGEN
# --------------------------------------------------

def procesar_imagen(archivo):

    file_bytes = np.asarray(
        bytearray(archivo.read()),
        dtype=np.uint8
    )

    img = cv2.imdecode(
        file_bytes,
        cv2.IMREAD_COLOR
    )

    img = mejorar_imagen(img)

    resultados = reader.readtext(
        img,
        detail=1
    )

    filas = {}

    for r in resultados:

        box = r[0]
        texto = r[1]

        y = int(
            (
                box[0][1] +
                box[2][1]
            ) / 2
        )

        encontrada = False

        for y_base in list(filas.keys()):

            if abs(y_base - y) < 40:

                filas[y_base].append(
                    (box, texto)
                )

                encontrada = True
                break

        if not encontrada:

            filas[y] = [
                (box, texto)
            ]

    ciudades = []

    for y in filas:

        fila_texto = " ".join(
            str(x[1])
            for x in filas[y]
        ).lower()

        if "id" in fila_texto:
            continue

        ciudad = extraer_datos_fila(
            filas[y]
        )

        if ciudad["ID"] > 0:

            ciudades.append(ciudad)

    return ciudades


# --------------------------------------------------
# INTERFAZ
# --------------------------------------------------

st.subheader("Sube capturas")

files = st.file_uploader(
    "Selecciona imágenes",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if files:

    datos = []

    for f in files:

        datos.extend(
            procesar_imagen(f)
        )

    # Eliminar duplicados por ID
    unicos = {}

    for ciudad in datos:

        unicos[ciudad["ID"]] = ciudad

    datos = list(unicos.values())

    datos = sorted(
        datos,
        key=lambda x: x["ID"]
    )

    df = pd.DataFrame(datos)

    st.success(
        f"Ciudades detectadas: {len(df)}"
    )

    st.dataframe(
        df,
        use_container_width=True
    )
