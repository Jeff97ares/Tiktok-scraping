"""Gráficos interactivos del análisis de comentarios y actividad pública."""
import pandas as pd
import plotly.express as px


def tabla_resultados(resultado, registros):
    return pd.DataFrame([{
        'video': r['video'], 'autor': r['autor'], 'comentario': r['texto'],
        'grupo': f"Grupo {int(resultado['grupos'][i]) + 1}",
        'sentimiento': resultado['sentimientos'][i]['sentimiento'],
        'confianza': resultado['sentimientos'][i]['confianza'],
        'x': float(resultado['coordenadas'][i, 0]),
        'y': float(resultado['coordenadas'][i, 1]),
    } for i, r in enumerate(registros)])


def grafico_semantico(resultado, registros):
    df = tabla_resultados(resultado, registros)
    fig = px.scatter(df, x='x', y='y', color='grupo',
                     hover_data={'comentario': True, 'autor': True, 'video': True,
                                 'x': False, 'y': False},
                     title='Mapa semántico de comentarios', template='plotly_dark')
    fig.update_traces(marker={'size': 13, 'opacity': 0.85})
    fig.update_layout(xaxis_title='Dimensión UMAP 1', yaxis_title='Dimensión UMAP 2')
    return fig


def grafico_similitud(resultado, registros):
    nombres = [f"{i+1}. {r['texto'][:28]}" for i, r in enumerate(registros)]
    fig = px.imshow(resultado['similitudes'], x=nombres, y=nombres,
                    color_continuous_scale='Viridis', zmin=-1, zmax=1,
                    title='Similitud del coseno entre comentarios',
                    template='plotly_dark', aspect='auto')
    fig.update_layout(height=max(470, min(1000, 25*len(registros)+200)))
    fig.update_xaxes(tickangle=-50)
    return fig


def grafico_distribucion(resultado, registros):
    df = tabla_resultados(resultado, registros)
    conteo = df.groupby('grupo', as_index=False).size().rename(columns={'size': 'cantidad'})
    fig = px.pie(conteo, names='grupo', values='cantidad', hole=0.45,
                 title='Distribución de grupos semánticos', template='plotly_dark')
    fig.update_traces(textinfo='label+percent+value')
    return fig


def grafico_sentimientos(resultado, registros):
    df = tabla_resultados(resultado, registros)
    orden = ['Positivo', 'Neutro', 'Negativo']
    conteo = df['sentimiento'].value_counts().reindex(orden, fill_value=0).reset_index()
    conteo.columns = ['sentimiento', 'cantidad']
    fig = px.bar(conteo, x='sentimiento', y='cantidad', color='sentimiento',
                 color_discrete_map={'Positivo': '#19a88a', 'Neutro': '#64748b',
                                     'Negativo': '#e66a66'},
                 title='Clasificación estimada de sentimientos', template='plotly_dark')
    fig.update_layout(showlegend=False)
    return fig


def grafico_actividad_circular(resultado):
    """Composición relativa de cinco indicadores observables (total 100 %)."""
    df = pd.DataFrame(list(resultado['porcentajes'].items()), columns=['indicador', 'porcentaje'])
    fig = px.pie(df, names='indicador', values='porcentaje', hole=0.48,
                 title='Composición de actividad digital (100 %)', template='plotly_dark')
    fig.update_traces(textinfo='label+percent')
    return fig


def grafico_actividad_barras(resultado):
    df = pd.DataFrame(list(resultado['porcentajes'].items()), columns=['indicador', 'porcentaje'])
    fig = px.bar(df, x='indicador', y='porcentaje', text='porcentaje',
                 title='Peso relativo de indicadores de actividad digital', template='plotly_dark')
    fig.update_traces(texttemplate='%{text:.2f} %', textposition='outside')
    fig.update_layout(yaxis_title='Porcentaje del total', xaxis_title='', yaxis_range=[0, 105])
    return fig
