"""Punto de entrada: interfaz Streamlit del TikTok Web Scraper."""
import streamlit as st
from selenium.common.exceptions import TimeoutException, WebDriverException

from scraper import parse_user, collect_profile, collect_comments
from styles import apply_styles
from components import render_sidebar, render_header, render_profile_metrics, render_comments

st.set_page_config(
    page_title="TikTok Analytics | Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS únicamente visual: no cambia la lógica de scraping.
apply_styles()

# Los datos y el navegador permanecen en la sesión de Streamlit.
for key, default in {
    'profile': None,
    'videos': [],
    'comments': {},
    'username': '',
    'driver': None,
    'selected_video_id': None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Menú lateral con el estado real del navegador.
render_sidebar()
render_header()

# Formulario: mantiene el método de búsqueda del proyecto original.
with st.form('search_form', clear_on_submit=False):
    st.markdown('**Buscar perfil de TikTok**')
    input_value = st.text_input(
        'Usuario o enlace del perfil',
        value=st.session_state.username,
        placeholder='@usuario o https://www.tiktok.com/@usuario',
    )
    search = st.form_submit_button('🔎 Consultar perfil', type='primary', use_container_width=True)

if search:
    try:
        username = parse_user(input_value)
        # Limpiar datos anteriores solamente al iniciar otra consulta.
        st.session_state.profile = None
        st.session_state.videos = []
        st.session_state.comments = {}
        st.session_state.username = username
        st.session_state.selected_video_id = None
        with st.spinner('Consultando perfil con Firefox Developer Edition...'):
            profile, videos = collect_profile(username, st.progress(0))
        st.session_state.profile = profile
        st.session_state.videos = videos
        if videos:
            st.session_state.selected_video_id = videos[0]['id']
            st.success(f'Consulta completada: {len(videos)} publicaciones encontradas.')
        else:
            st.warning('No se encontraron publicaciones accesibles. Comprueba la página abierta en Firefox.')
    except (ValueError, WebDriverException, TimeoutException) as exc:
        st.error(f'No se pudo completar la consulta: {exc}')

profile = st.session_state.profile
videos = st.session_state.videos

if profile is not None:
    render_profile_metrics(profile, videos, st.session_state.username)

if videos:
    st.divider()
    st.markdown('### 🎬 Publicaciones y comentarios')
    st.caption('Selecciona una publicación, reproduce el video y consulta sus comentarios sin cambiar de pestaña.')

    video_ids = [v['id'] for v in videos]
    if st.session_state.selected_video_id not in video_ids:
        st.session_state.selected_video_id = video_ids[0]

    # El selector y los comentarios comparten el mismo video seleccionado.
    chosen = st.selectbox(
        'Selecciona una publicación',
        options=video_ids,
        format_func=lambda vid: (
            f"Video {video_ids.index(vid) + 1:02d} · "
            f"{videos[video_ids.index(vid)]['descripcion'][:65]}"
        ),
        key='selected_video_id',
    )
    video = next(v for v in videos if v['id'] == chosen)

    left, right = st.columns([1, 1.65], gap='large')
    with left:
        with st.container(border=True):
            st.markdown('#### 📋 Publicación seleccionada')
            st.write(video['descripcion'])
            st.caption(f"Video {video_ids.index(chosen) + 1} de {len(videos)}")
            st.link_button('↗ Abrir video en TikTok', video['url'], use_container_width=True)

        st.markdown('#### 💬 Comentarios del video')
        st.caption('Se consultan hasta 10 comentarios públicos y sus autores.')
        # Botón visible junto al video; no requiere escribir en TikTok.
        consultar = st.button(
            '🔎 Consultar hasta 10 comentarios',
            type='primary',
            use_container_width=True,
            key='consultar_comentarios',
        )
        if consultar:
            try:
                with st.spinner('Extrayendo comentarios automáticamente desde Firefox...'):
                    comments_nuevos = collect_comments(video['url'], st.progress(0))
                st.session_state.comments[video['url']] = comments_nuevos
            except (WebDriverException, TimeoutException) as exc:
                st.error(f'Error al consultar comentarios: {exc}')

        comments = st.session_state.comments.get(video['url'])
        render_comments(comments, video['id'])

    with right:
        st.markdown('#### ▶️ Reproductor integrado')
        st.caption('Reproductor oficial de TikTok.')
        st.components.v1.iframe(
            f"https://www.tiktok.com/player/v1/{video['id']}",
            height=650,
            scrolling=True,
        )

else:
    st.write('')
    st.markdown('<div class="empty-panel">🔎 <b>Tu dashboard está listo.</b><br>Introduce un perfil público de TikTok para consultar sus estadísticas y publicaciones.</div>', unsafe_allow_html=True)
