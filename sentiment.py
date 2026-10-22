
"""Clasificación multilingüe de sentimientos en comentarios de TikTok."""

import streamlit as st
from transformers import pipeline

# Modelo multilingüe para clasificar sentimientos.
MODELO = "cardiffnlp/twitter-xlm-roberta-base-sentiment"

# Traducción de las etiquetas al español.
ETIQUETAS = {
    "negative": "Negativo",
    "neutral": "Neutro",
    "positive": "Positivo",
    "LABEL_0": "Negativo",
    "LABEL_1": "Neutro",
    "LABEL_2": "Positivo",
}


@st.cache_resource(show_spinner="Cargando modelo de sentimientos...")
def cargar_clasificador():
    """
    Carga el modelo de sentimientos una sola vez
    y lo reutiliza mediante la caché de Streamlit.
    """

    try:
        clasificador = pipeline(
            task="text-classification",
            model=MODELO,
            tokenizer=MODELO,
            use_fast=False,
            device=-1,
        )

        return clasificador

    except Exception as exc:
        raise RuntimeError(
            "No se pudo cargar el modelo de sentimientos. "
            "Comprueba la instalación de transformers y sentencepiece, "
            "así como la descarga de los archivos del modelo."
        ) from exc


def clasificar_sentimientos(textos):
    """
    Clasifica los comentarios como positivos,
    negativos o neutros.

    Args:
        textos (list[str]): Comentarios extraídos de TikTok.

    Returns:
        list[dict]: Sentimiento y confianza estimada
                    para cada comentario.
    """

    if not textos:
        return []

    # Recuperar el modelo desde la caché.
    modelo = cargar_clasificador()

    # Analizar los comentarios por lotes.
    salidas = modelo(
        textos,
        truncation=True,
        max_length=512,
        batch_size=8,
    )

    resultados = []

    for salida in salidas:
        etiqueta = salida["label"]

        resultados.append({
            "sentimiento": ETIQUETAS.get(
                etiqueta,
                ETIQUETAS.get(etiqueta.lower(), etiqueta),
            ),
            "confianza": round(
                float(salida["score"]),
                3,
            ),
        })

    return resultados
