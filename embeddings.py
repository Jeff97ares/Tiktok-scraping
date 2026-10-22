"""Embeddings multilingües, cargados solo cuando se necesitan."""
import streamlit as st
from sentence_transformers import SentenceTransformer

MODELO = 'paraphrase-multilingual-MiniLM-L12-v2'

@st.cache_resource(show_spinner='Cargando modelo de embeddings...')
def cargar_modelo():
    return SentenceTransformer(MODELO)

def generar_embeddings(textos):
    return cargar_modelo().encode(textos, convert_to_numpy=True, normalize_embeddings=True)
