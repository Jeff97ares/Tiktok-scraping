"""Clasificación multilingüe de sentimiento: estimaciones, no hechos."""
import streamlit as st
from transformers import pipeline

MODELO = 'cardiffnlp/twitter-xlm-roberta-base-sentiment'
ETIQUETAS = {'negative': 'Negativo', 'neutral': 'Neutro', 'positive': 'Positivo',
             'LABEL_0': 'Negativo', 'LABEL_1': 'Neutro', 'LABEL_2': 'Positivo'}

@st.cache_resource(show_spinner='Cargando modelo de sentimientos...')
def cargar_clasificador():
    return pipeline('text-classification', model=MODELO, tokenizer=MODELO, device=-1)

def clasificar_sentimientos(textos):
    if not textos:
        return []
    modelo = cargar_clasificador()
    salidas = modelo(textos, truncation=True, max_length=512, batch_size=8)
    return [{'sentimiento': ETIQUETAS.get(x['label'], x['label']),
             'confianza': round(float(x['score']), 3)} for x in salidas]
