"""Dashboard TikTok: scraping, almacenamiento SQLite y análisis semántico opcional."""

import streamlit as st
from selenium.common.exceptions import TimeoutException, WebDriverException

from analysis import analizar_actividad_digital
from charts import grafico_actividad_circular, grafico_actividad_barras

from scraper import parse_user, collect_profile, collect_comments, MAX_COMENTARIOS
from styles import apply_styles
from components import (
    render_sidebar,
    render_header,
    render_profile_metrics,
    render_comments,
)
from database import (
    inicializar_db,
    guardar_perfil,
    guardar_comentarios,
    obtener_estadisticas,
)

st.set_page_config(
    page_title="TikTok Analytics | Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_styles()

# SQLite: crea las tablas solo si todavía no existen.
inicializar_db()

for key, default in {
    "profile": None,
    "videos": [],
    "comments": {},
    "username": "",
    "driver": None,
    "selected_video_id": None,
    "resultado_ia": None,
    "firma_ia": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

render_sidebar()
render_header()

with st.form("search_form", clear_on_submit=False):
    st.markdown("**Buscar perfil de TikTok**")
    input_value = st.text_input(
        "Usuario o enlace del perfil",
        value=st.session_state.username,
        placeholder="@usuario o https://www.tiktok.com/@usuario",
    )
    search = st.form_submit_button(
        "🔎 Consultar perfil", type="primary", width="stretch"
    )

if search:
    try:
        username = parse_user(input_value)
        st.session_state.profile = None
        st.session_state.videos = []
        st.session_state.comments = {}
        st.session_state.username = username
        st.session_state.selected_video_id = None
        st.session_state.resultado_ia = None
        st.session_state.firma_ia = None

        with st.spinner("Consultando perfil con Firefox Developer Edition..."):
            profile, videos = collect_profile(username, st.progress(0))

        st.session_state.profile = profile
        st.session_state.videos = videos

        if videos:
            st.session_state.selected_video_id = videos[0]["id"]
            st.success(
                f"Consulta completada: {len(videos)} publicaciones encontradas."
            )
        else:
            st.warning("No se encontraron publicaciones accesibles. Comprueba Firefox.")

        # El scraping es independiente del guardado: si falla SQLite,
        # los datos recién extraídos siguen disponibles en pantalla.
        try:
            guardar_perfil(username, profile, videos)
            st.caption("🗄️ Perfil y publicaciones guardados en SQLite.")
        except Exception as exc:
            st.warning(f"Se consultó el perfil, pero no se pudo guardar en SQLite: {exc}")

    except (ValueError, WebDriverException, TimeoutException) as exc:
        st.error(f"No se pudo completar la consulta: {exc}")

profile = st.session_state.profile
videos = st.session_state.videos

if profile is not None:
    render_profile_metrics(profile, videos, st.session_state.username)

    # Datos adicionales: se muestran solo si TikTok los proporciona.
    st.markdown("### 👤 Información pública adicional")
    biografia = profile.get("biografia")
    with st.container(border=True):
        st.markdown("**Biografía del perfil**")
        st.write(biografia if biografia else "No disponible en los datos extraídos.")
        fechas_disponibles = sum(bool(v.get("fecha_publicacion")) for v in videos)
        st.caption(
            f"Fechas de publicación identificadas: {fechas_disponibles} "
            f"de {len(videos)} videos."
        )

if videos:
    st.divider()
    st.markdown("### 🎬 Publicaciones y comentarios")
    st.caption(
        "Selecciona una publicación, reproduce el video y consulta sus comentarios."
    )

    video_ids = [v["id"] for v in videos]
    if st.session_state.selected_video_id not in video_ids:
        st.session_state.selected_video_id = video_ids[0]

    chosen = st.selectbox(
        "Selecciona una publicación",
        options=video_ids,
        format_func=lambda vid: (
            f"Video {video_ids.index(vid) + 1:02d} · "
            f"{str(videos[video_ids.index(vid)].get('descripcion', ''))[:65]}"
        ),
        key="selected_video_id",
    )
    video = next(v for v in videos if v["id"] == chosen)

    left, right = st.columns([1, 1.65], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("#### 📋 Publicación seleccionada")
            st.write(video.get("descripcion", ""))
            fecha = video.get("fecha_publicacion")
            st.caption(f"Fecha de publicación (UTC): {fecha or 'No disponible'}")
            st.caption(f"Video {video_ids.index(chosen) + 1} de {len(videos)}")
            st.link_button(
                "↗ Abrir video en TikTok", video["url"], width="stretch"
            )

        st.markdown("#### 💬 Comentarios del video")
        st.caption(
            f"Se consultan hasta {MAX_COMENTARIOS} comentarios públicos y sus autores."
        )
        consultar = st.button(
            f"🔎 Consultar hasta {MAX_COMENTARIOS} comentarios",
            type="primary",
            width="stretch",
            key="consultar_comentarios",
        )
        if consultar:
            try:
                with st.spinner("Extrayendo comentarios automáticamente desde Firefox..."):
                    comments_nuevos = collect_comments(video["url"], st.progress(0))
                st.session_state.comments[video["url"]] = comments_nuevos
                st.session_state.resultado_ia = None
                st.session_state.firma_ia = None

                try:
                    nuevos = guardar_comentarios(video["id"], comments_nuevos)
                    st.success(
                        f"🗄️ {nuevos} comentarios nuevos guardados en SQLite. "
                        "Los repetidos no se duplican."
                    )
                except Exception as exc:
                    st.warning(
                        "Los comentarios se extrajeron, pero no se pudieron guardar "
                        f"en SQLite: {exc}"
                    )
            except (WebDriverException, TimeoutException) as exc:
                st.error(f"Error al consultar comentarios: {exc}")

        comments = st.session_state.comments.get(video["url"])
        render_comments(comments, video["id"])

    with right:
        st.markdown("#### ▶️ Reproductor integrado")
        st.caption("Reproductor oficial de TikTok.")
        st.components.v1.iframe(
            f"https://www.tiktok.com/player/v1/{video['id']}",
            height=650,
            scrolling=True,
        )
else:
    st.markdown(
        '<div class="empty-panel">🔎 <b>Tu dashboard está listo.</b><br>'
        "Introduce un perfil público de TikTok para consultar sus estadísticas "
        "y publicaciones.</div>",
        unsafe_allow_html=True,
    )

# Resumen de datos observables del perfil, sin inferencias psicológicas.
if profile is not None:
    with st.expander("📈 Actividad pública del perfil · análisis exploratorio", expanded=False):
        st.caption(
            "Estos indicadores describen publicaciones accesibles. No son puntuaciones "
            "Big Five ni permiten determinar la personalidad del titular."
        )
        descripciones = [
            str(v.get("descripcion") or "").strip()
            for v in videos
            if str(v.get("descripcion") or "").strip().lower()
            not in ("", "descripción no disponible")
        ]
        fechas = sorted({
            str(v.get("fecha_publicacion")) for v in videos
            if v.get("fecha_publicacion")
        })
        a, b, c = st.columns(3)
        a.metric("Publicaciones accesibles", len(videos))
        b.metric("Descripciones disponibles", len(descripciones))
        c.metric("Fechas disponibles", sum(bool(v.get("fecha_publicacion")) for v in videos))
        if len(fechas) >= 2:
            st.write(f"Periodo observado: {fechas[0]} a {fechas[-1]} (UTC).")
        elif fechas:
            st.write(f"Fecha observada: {fechas[0]} (UTC).")
        else:
            st.info("No hay fechas suficientes para estudiar regularidad de publicación.")
        if descripciones:
            st.markdown("**Descripciones publicadas por el perfil**")
            st.dataframe(
                [{"Descripción": texto} for texto in descripciones],
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No hay descripciones disponibles para analizar temas.")

# Distribución porcentual de indicadores observables del contenido público.
# Se calcula a partir de las publicaciones de la sesión, sin usar comentarios.
if videos:
    st.divider()
    with st.expander("📊 Perfil de actividad digital · distribución 100 %", expanded=True):
        st.caption(
            "Distribución relativa de cinco indicadores calculados a partir de las "
            "descripciones y fechas de los videos recopilados. No representa "
            "rasgos de personalidad ni una evaluación Big Five."
        )
        try:
            resultado_actividad = analizar_actividad_digital(videos)
            if resultado_actividad:
                m1, m2, m3 = st.columns(3)
                m1.metric("Publicaciones analizadas", resultado_actividad["cantidad_videos"])
                m2.metric("Descripciones válidas", resultado_actividad["descripciones_validas"])
                m3.metric("Fechas distintas", resultado_actividad["fechas_validas"])

                if resultado_actividad["total_porcentaje"] > 0:
                    izquierda, derecha = st.columns(2, gap="large")
                    with izquierda:
                        st.plotly_chart(
                            grafico_actividad_circular(resultado_actividad),
                            width="stretch",
                            key="actividad_circular",
                        )
                    with derecha:
                        st.plotly_chart(
                            grafico_actividad_barras(resultado_actividad),
                            width="stretch",
                            key="actividad_barras",
                        )
                    st.metric(
                        "Suma de los indicadores",
                        f"{resultado_actividad['total_porcentaje']:.2f} %",
                    )
                    st.dataframe(
                        [
                            {"Indicador": nombre, "Porcentaje": f"{valor:.2f} %"}
                            for nombre, valor in resultado_actividad["porcentajes"].items()
                        ],
                        hide_index=True,
                        width="stretch",
                    )
                else:
                    st.info("Los datos disponibles no permiten calcular porcentajes positivos.")

                if resultado_actividad["fechas_validas"] < 3:
                    st.info(
                        "La regularidad temporal necesita al menos tres fechas "
                        "de publicación distintas; con menos fechas se muestra como cero."
                    )
                st.caption(resultado_actividad["advertencia"])
            else:
                st.info("No hay publicaciones suficientes para mostrar el análisis.")
        except Exception as exc:
            st.error(f"No se pudo calcular el perfil de actividad digital: {exc}")

# Estado de almacenamiento, incluso antes de realizar una nueva búsqueda.
with st.expander("🗄️ Estado de la base de datos SQLite", expanded=False):
    try:
        estadisticas = obtener_estadisticas()
        col1, col2, col3 = st.columns(3)
        col1.metric("Perfiles", estadisticas["perfiles"])
        col2.metric("Videos", estadisticas["videos"])
        col3.metric("Comentarios", estadisticas["comentarios"])
        st.caption(
            "Estos registros permanecen en SQLite al cerrar la aplicación. "
            "El análisis con IA sigue utilizando los comentarios de la sesión actual."
        )
    except Exception as exc:
        st.error(f"No se pudieron consultar las estadísticas de SQLite: {exc}")

if videos:
    st.divider()
    with st.expander("🧠 Análisis con IA y embeddings", expanded=False):
        st.markdown("### Temas y sentimientos de los comentarios")
        st.caption("Se analizan textos públicos, no la personalidad de quien publica.")

        opciones = {"Todos los videos": None}
        for i, v in enumerate(videos, 1):
            opciones[f"Video {i:02d} · {str(v.get('descripcion', ''))[:40]}"] = v["url"]
        seleccion = st.selectbox(
            "Filtrar por publicación", list(opciones), key="filtro_ia"
        )
        url_elegida = opciones[seleccion]

        registros = []
        for url, comentarios in st.session_state.comments.items():
            if url_elegida is not None and url != url_elegida:
                continue
            for comentario in comentarios:
                texto = str(comentario.get("texto", "")).strip()
                if texto:
                    registros.append(
                        {
                            "video": url,
                            "autor": comentario.get("autor", ""),
                            "texto": texto,
                        }
                    )

        st.metric("Comentarios disponibles", len(registros))
        firma = tuple(
            (r["video"], r["autor"], r["texto"]) for r in registros
        )

        if len(registros) < 5:
            st.info("Extrae al menos cinco comentarios para analizar esta selección.")
        else:
            if st.button(
                "🚀 Analizar temas y sentimientos",
                type="primary",
                key="generar_analisis_ia",
            ):
                try:
                    # Cargar los modelos pesados solo al solicitar el análisis.
                    from analysis import analizar_comentarios

                    with st.spinner(
                        "Analizando embeddings y sentimientos "
                        "(la primera vez puede tardar)..."
                    ):
                        resultado = analizar_comentarios(
                            [r["texto"] for r in registros]
                        )
                    st.session_state.resultado_ia = resultado
                    st.session_state.firma_ia = firma
                    st.success("Análisis generado correctamente.")
                except Exception as exc:
                    st.session_state.resultado_ia = None
                    st.error(f"Error al analizar: {exc}")
                    st.exception(exc)

            resultado = st.session_state.resultado_ia
            if resultado is not None and st.session_state.firma_ia == firma:
                from charts import (
                    tabla_resultados,
                    grafico_semantico,
                    grafico_similitud,
                    grafico_distribucion,
                    grafico_sentimientos,
                )

                df = tabla_resultados(resultado, registros)
                st.markdown("#### Resumen de sentimientos")
                cantidades = df["sentimiento"].value_counts()
                cols = st.columns(3)
                for col, nombre in zip(cols, ["Positivo", "Neutro", "Negativo"]):
                    cantidad = int(cantidades.get(nombre, 0))
                    col.metric(nombre, f"{cantidad} ({cantidad / len(df):.0%})")
                st.caption(
                    "La clasificación es automática y puede equivocarse con sarcasmo, "
                    "jerga o comentarios breves. Confianza no equivale a exactitud."
                )

                st.markdown("#### Temas exploratorios")
                st.write(
                    "Cada grupo muestra un comentario representativo, no una etiqueta "
                    "temática validada. Lee los ejemplos antes de interpretarlo."
                )
                for grupo, ejemplo in resultado["ejemplos"].items():
                    cantidad = int((resultado["grupos"] == grupo).sum())
                    with st.expander(f"Grupo {grupo + 1} · {cantidad} comentarios"):
                        st.write("**Comentario representativo:**", ejemplo)
                        st.dataframe(
                            df.loc[
                                df["grupo"] == f"Grupo {grupo + 1}",
                                ["autor", "comentario", "sentimiento", "video"],
                            ],
                            hide_index=True,
                            width="stretch",
                        )

                tab1, tab2, tab3, tab4, tab5 = st.tabs(
                    [
                        "🌐 Mapa semántico",
                        "🔥 Similitud",
                        "📊 Grupos",
                        "💬 Sentimientos",
                        "📋 Comentarios",
                    ]
                )
                with tab1:
                    st.plotly_chart(
                        grafico_semantico(resultado, registros),
                        width="stretch",
                    )
                with tab2:
                    st.plotly_chart(
                        grafico_similitud(resultado, registros),
                        width="stretch",
                    )
                with tab3:
                    st.plotly_chart(
                        grafico_distribucion(resultado, registros),
                        width="stretch",
                    )
                with tab4:
                    st.plotly_chart(
                        grafico_sentimientos(resultado, registros),
                        width="stretch",
                    )
                with tab5:
                    st.dataframe(
                        df[
                            [
                                "video",
                                "autor",
                                "comentario",
                                "grupo",
                                "sentimiento",
                                "confianza",
                            ]
                        ],
                        hide_index=True,
                        width="stretch",
                    )
                st.caption(
                    "Los resultados describen comentarios de la muestra, "
                    "no rasgos psicológicos del titular del perfil."
                )
