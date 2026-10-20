"""Componentes reutilizables de Streamlit para el dashboard."""
from html import escape
import streamlit as st
from scraper import DEVELOPER_EXE, driver_alive

def render_sidebar():
    """Muestra el estado de Firefox y permite cerrar su sesión."""
    with st.sidebar:
        st.markdown('### 🎵 TikTok Analytics')
        st.caption('Panel de consulta de contenido público')
        st.divider()
        st.markdown('**Estado del navegador**')
        if driver_alive(st.session_state.driver):
            st.success('Firefox Selenium conectado')
        else:
            st.info('Firefox se iniciará al consultar')
        if DEVELOPER_EXE.is_file():
            st.caption('✓ Firefox Developer Edition detectado')
        else:
            st.warning('Se utilizará el Firefox disponible en el sistema.')
        st.divider()
        st.markdown('**Funciones disponibles**')
        st.caption('• Consultar perfil y estadísticas\n\n• Explorar hasta 10 publicaciones\n\n• Reproducir videos\n\n• Leer hasta 10 comentarios por video')
        st.divider()
        if st.button('Cerrar sesión de Firefox', use_container_width=True):
            navegador = st.session_state.get('driver')
            if driver_alive(navegador):
                navegador.quit()
            st.session_state.driver = None
            st.success('Sesión cerrada.')
        st.caption('Solo lectura: no se descargan videos ni se publican comentarios.')

def render_header():
    """Muestra el encabezado principal del dashboard."""
    st.markdown("""<div class="hero">
    <div class="hero-title">TikTok Analytics <span style="color:#F24876">●</span></div>
    <p class="hero-sub">Dashboard de perfiles, publicaciones y comentarios públicos</p>
    <span class="pill">● Selenium + BeautifulSoup + Streamlit</span>
    </div>""", unsafe_allow_html=True)

def render_profile_metrics(profile, videos, username):
    """Muestra los datos y métricas del perfil consultado."""
    st.markdown('#### Resumen del perfil')
    st.markdown(f'<div class="caption-soft">@{escape(username)}</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('👤 Nombre', str(profile['nombre']))
    col2.metric('👥 Seguidores', str(profile['seguidores']))
    col3.metric('➕ Seguidos', str(profile['seguidos']))
    col4.metric('🎬 Publicaciones detectadas', len(videos))

def render_comments(comments, video_id):
    """Muestra comentarios con autores y filtro; no consulta TikTok."""
    if comments is None:
        st.info('Pulsa el botón para cargar los comentarios de este video.')
    elif not comments:
        st.warning('No se detectaron comentarios accesibles. Puedes reintentar la consulta.')
    else:
        st.success(f'✅ {len(comments)} comentarios recuperados')
        filtro = st.text_input(
            'Buscar por autor o palabra',
            placeholder='Ej.: lopez, lindo, primero...',
            key=f"filtro_{video_id}",
        )
        filtrados = [
            c for c in comments
            if filtro.casefold() in (c['autor'] + ' ' + c['texto']).casefold()
        ]
        st.caption(f'Mostrando {len(filtrados)} de {len(comments)} comentarios')
        for numero, comment in enumerate(filtrados, 1):
            with st.container(border=True):
                autor = escape(str(comment['autor']))
                texto = escape(str(comment['texto']))
                st.markdown(
                    f'<div><span class="comment-num">{numero:02d}</span>'
                    f'<span class="comment-author">👤 {autor}</span></div>'
                    f'<div class="comment-body">{texto}</div>',
                    unsafe_allow_html=True,
                )
        if not filtrados:
            st.info('No hay comentarios que coincidan con el filtro.')
