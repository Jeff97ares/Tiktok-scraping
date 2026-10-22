"""Agrupación semántica, similitud y sentimiento de comentarios."""
import numpy as np
import umap
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from embeddings import generar_embeddings
from sentiment import clasificar_sentimientos


def analizar_comentarios(textos):
    textos = [str(t).strip() for t in textos]
    if len(textos) < 5 or any(not t for t in textos):
        return None
    embeddings = generar_embeddings(textos)
    # Tres grupos como máximo; son grupos exploratorios, no temas validados.
    n_grupos = min(3, len(textos))
    kmeans = KMeans(n_clusters=n_grupos, random_state=42, n_init=10)
    grupos = kmeans.fit_predict(embeddings)
    coordenadas = umap.UMAP(n_components=2, n_neighbors=min(5, len(textos)-1),
                            random_state=42).fit_transform(embeddings)
    similitudes = cosine_similarity(embeddings)
    sentimientos = clasificar_sentimientos(textos)
    ejemplos = {}
    for grupo in sorted(set(grupos)):
        indices = np.flatnonzero(grupos == grupo)
        centro = kmeans.cluster_centers_[grupo]
        mejor = max(indices, key=lambda i: float(np.dot(embeddings[i], centro)))
        ejemplos[int(grupo)] = textos[int(mejor)]
    return {'textos': textos, 'grupos': grupos, 'coordenadas': coordenadas,
            'similitudes': similitudes, 'sentimientos': sentimientos,
            'ejemplos': ejemplos}
