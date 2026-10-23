"""Agrupación semántica, similitud, sentimiento y actividad pública de TikTok."""
import re
from collections import Counter
from datetime import datetime, timezone

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


def _fecha_valida(valor):
    """Admite fecha ISO (YYYY-MM-DD) o timestamp Unix en segundos."""
    if valor is None or str(valor).strip() == '':
        return None
    try:
        if isinstance(valor, (int, float)) or str(valor).strip().isdigit():
            return datetime.fromtimestamp(float(valor), tz=timezone.utc).date()
        return datetime.fromisoformat(str(valor).strip().replace('Z', '+00:00')).date()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def analizar_actividad_digital(videos):
    """Calcula una composición relativa de cinco indicadores observables.

    `videos` es una lista de dicts con `descripcion` y `fecha_publicacion`.
    El resultado NO es una evaluación psicológica Big Five. Los porcentajes
    describen pesos relativos entre indicadores definidos para esta muestra.
    """
    videos = list(videos or [])
    if not videos:
        return None

    descripciones = [str(v.get('descripcion') or '').strip() for v in videos]
    descripciones = [d for d in descripciones if d and d.lower() != 'descripción no disponible']
    hashtags = [h.lower() for d in descripciones for h in re.findall(r'#[\wáéíóúñ]+', d, re.UNICODE)]
    textos_limpios = [re.sub(r'#[\wáéíóúñ]+', ' ', d, flags=re.UNICODE) for d in descripciones]
    palabras = [p.lower() for t in textos_limpios for p in re.findall(r'\b[^\W\d_]{2,}\b', t, re.UNICODE)]
    fechas = sorted(set(filter(None, (_fecha_valida(v.get('fecha_publicacion')) for v in videos))))

    # Cinco indicadores operativos de 0 a 1; son descriptivos, no rasgos personales.
    # Diversidad temática: aproximación por variedad de hashtags (no clasificación semántica).
    diversidad = len(set(hashtags)) / len(hashtags) if hashtags else 0.0
    # Regularidad: cercanía de intervalos de publicación (requiere >=3 fechas distintas).
    intervalos = [(b - a).days for a, b in zip(fechas, fechas[1:])]
    regularidad = (1.0 / (1.0 + float(np.std(intervalos)) / max(float(np.mean(intervalos)), 1.0))) if len(intervalos) >= 2 else 0.0
    # Actividad: cobertura de metadatos de publicaciones en la muestra, no frecuencia real.
    actividad = len(descripciones) / len(videos)
    variedad_linguistica = len(set(palabras)) / len(palabras) if palabras else 0.0
    uso_hashtags = sum(bool(re.search(r'#[\wáéíóúñ]+', d, re.UNICODE)) for d in descripciones) / len(descripciones) if descripciones else 0.0

    indicadores = {
        'Diversidad de hashtags': diversidad,
        'Regularidad temporal': regularidad,
        'Cobertura de descripciones': actividad,
        'Variedad léxica': variedad_linguistica,
        'Uso de hashtags': uso_hashtags,
    }
    total = sum(indicadores.values())
    if total <= 0:
        porcentajes = {k: 0.0 for k in indicadores}
    else:
        porcentajes = {k: round(v / total * 100, 2) for k, v in indicadores.items()}
        # Ajuste de redondeo: suma exactamente 100.00 cuando existe información.
        ultimo = next(reversed(porcentajes))
        porcentajes[ultimo] = round(100.0 - sum(v for k, v in porcentajes.items() if k != ultimo), 2)

    return {
        'indicadores': indicadores,
        'porcentajes': porcentajes,
        'total_porcentaje': round(sum(porcentajes.values()), 2),
        'cantidad_videos': len(videos),
        'descripciones_validas': len(descripciones),
        'fechas_validas': len(fechas),
        'hashtags_frecuentes': Counter(hashtags).most_common(10),
        'advertencia': ('Distribución relativa de indicadores de contenido público; '
                        'no mide personalidad ni Big Five. La regularidad temporal '
                        'requiere al menos tres fechas de publicación distintas.'),
    }
