"""TikTok Web Scraper: Streamlit + Selenium + BeautifulSoup.

Consulta información pública visible; no descarga videos ni exporta datos.
Requiere Firefox Developer Edition y un geckodriver compatible (Selenium Manager).
"""
import json
import re
import time
from pathlib import Path
from html import escape
from urllib.parse import urlparse

import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

DEVELOPER_EXE = Path(r"C:\Program Files\Firefox Developer Edition\firefox.exe")
VIDEO_RE = re.compile(r"/@([^/?#]+)/video/(\d{15,22})")
# Selectores comprobados con Firefox Developer Edition.
COMMENT_BLOCKS = '[data-e2e="comment-level-1"]'
COMMENT_TEXT = '[data-e2e="comment-text"], [class*="PCommentText"]'
# Variantes posibles del nombre del autor (TikTok cambia su HTML).
COMMENT_USER = (
    '[data-e2e="comment-username-1"], '
    '[data-e2e="comment-username"], '
    '[class*="SpanUserName"], '
    '[class*="UserName"], '
    'a[href^="/@"], a[href*="tiktok.com/@"]'
)


def parse_user(value):
    value = value.strip()
    if value.startswith(('https://', 'http://')):
        parsed = urlparse(value)
        if (parsed.hostname or '').lower() not in ('tiktok.com', 'www.tiktok.com', 'm.tiktok.com'):
            raise ValueError('El enlace debe pertenecer a TikTok.')
        value = parsed.path.strip('/').split('/')[0]
    value = value.lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9._]{1,24}', value):
        raise ValueError('Introduce un usuario o enlace válido de TikTok.')
    return value


def json_scripts(soup):
    for script in soup.find_all('script'):
        raw = (script.string or script.get_text() or '').strip()
        if raw.startswith(('{', '[')):
            try:
                yield json.loads(raw)
            except (ValueError, TypeError):
                pass


def profile_from_html(html):
    profile = {'nombre': 'No disponible', 'seguidores': 'N/D', 'seguidos': 'N/D'}
    for data in json_scripts(BeautifulSoup(html, 'html.parser')):
        if not isinstance(data, dict):
            continue
        scope = data.get('__DEFAULT_SCOPE__', {})
        info = scope.get('webapp.user-detail', {}).get('userInfo', {}) if isinstance(scope, dict) else {}
        if not info:
            users = data.get('UserModule', {}).get('users', {})
            if isinstance(users, dict) and users:
                info = {'user': next(iter(users.values()), {})}
        if not isinstance(info, dict):
            continue
        user, stats = info.get('user', {}), info.get('stats', {})
        if isinstance(user, dict) and user:
            profile['nombre'] = user.get('nickname') or profile['nombre']
            if isinstance(stats, dict):
                profile['seguidores'] = stats.get('followerCount', 'N/D')
                profile['seguidos'] = stats.get('followingCount', 'N/D')
            break
    return profile


def videos_from_html(html, username):
    soup = BeautifulSoup(html, 'html.parser')
    found = {}

    def add(video_id, description='', author=None):
        video_id = str(video_id or '')
        if not re.fullmatch(r'\d{15,22}', video_id) or len(found) >= 10:
            return
        if author and str(author).lstrip('@').lower() != username.lower():
            return
        found.setdefault(video_id, {
            'id': video_id,
            'url': f'https://www.tiktok.com/@{username}/video/{video_id}',
            'descripcion': str(description or 'Descripción no disponible')[:300]
        })

    for link in soup.select('a[href*="/video/"]'):
        match = VIDEO_RE.search(link.get('href', ''))
        if match and match.group(1).lower() == username.lower():
            add(match.group(2), link.get('title') or link.get_text(' ', strip=True))

    def walk(node, depth=0):
        if depth > 20 or len(found) >= 10:
            return
        if isinstance(node, dict):
            for key in ('itemList', 'items'):
                entries = node.get(key)
                if isinstance(entries, list):
                    for item in entries:
                        if isinstance(item, (str, int)):
                            add(item)
                        elif isinstance(item, dict):
                            author = item.get('author')
                            if isinstance(author, dict):
                                author = author.get('uniqueId')
                            add(item.get('id'), item.get('desc'), author)
            module = node.get('itemModule')
            if isinstance(module, dict):
                for key, item in module.items():
                    if isinstance(item, dict):
                        author = item.get('author')
                        if isinstance(author, dict):
                            author = author.get('uniqueId')
                        add(item.get('id', key), item.get('desc'), author)
            for val in node.values():
                if isinstance(val, (dict, list)):
                    walk(val, depth + 1)
        elif isinstance(node, list):
            for val in node:
                if isinstance(val, (dict, list)):
                    walk(val, depth + 1)

    for data in json_scripts(soup):
        walk(data)
        if len(found) >= 10:
            break
    return list(found.values())


def make_driver():
    options = Options()
    if DEVELOPER_EXE.is_file():
        options.binary_location = str(DEVELOPER_EXE)
    driver = webdriver.Firefox(options=options)
    driver.set_page_load_timeout(45)
    return driver


def driver_alive(driver):
    try:
        return bool(driver and driver.window_handles)
    except WebDriverException:
        return False


def ensure_driver():
    driver = st.session_state.get('driver')
    if not driver_alive(driver):
        driver = make_driver()
        st.session_state.driver = driver
    return driver


def collect_profile(username, progress):
    driver = ensure_driver()
    driver.get(f'https://www.tiktok.com/@{username}')
    try:
        WebDriverWait(driver, 25).until(lambda d:
            d.find_elements(By.ID, '__UNIVERSAL_DATA_FOR_REHYDRATION__') or
            d.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]'))
    except TimeoutException:
        pass
    profile = profile_from_html(driver.page_source)
    videos = {}
    for attempt in range(12):
        for video in videos_from_html(driver.page_source, username):
            videos.setdefault(video['id'], video)
        for el in driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]'):
            match = VIDEO_RE.search(el.get_attribute('href') or '')
            if match and match.group(1).lower() == username.lower():
                video_id = match.group(2)
                videos.setdefault(video_id, {'id': video_id,
                    'url': f'https://www.tiktok.com/@{username}/video/{video_id}',
                    'descripcion': 'Descripción no disponible'})
        progress.progress(min(len(videos), 10) / 10, text=f'Publicaciones encontradas: {min(len(videos), 10)}/10')
        if len(videos) >= 10:
            break
        driver.execute_script('window.scrollBy(0, 650)')
        time.sleep(1.5)
    return profile, list(videos.values())[:10]


def comments_from_html(html):
    """Lee hasta 10 comentarios y sus autores desde el MISMO contenedor.

    Confirmado en la prueba de Firefox: el span comment-level-1 y el
    elemento comment-username-1 son hermanos dentro del div padre.
    """
    soup = BeautifulSoup(html, 'html.parser')
    result, seen = [], set()

    for text_el in soup.select('[data-e2e="comment-level-1"]'):
        content = text_el.get_text(' ', strip=True)
        if not content:
            continue

        # El autor NO está dentro del span del comentario, sino en su padre.
        parent = text_el.parent
        author_el = parent.select_one('[data-e2e="comment-username-1"]') if parent else None
        author = author_el.get_text(' ', strip=True) if author_el else ''

        # Alternativa: recuperar @usuario desde el enlace del mismo contenedor.
        if not author and parent:
            link = parent.select_one('a[href^="/@"]')
            if link:
                match = re.search(r'/@([^/?#]+)', link.get('href', ''))
                if match:
                    author = '@' + match.group(1)
        if not author:
            author = 'Usuario no disponible'

        key = (author, content)
        if key in seen:
            continue
        seen.add(key)
        result.append({'autor': author, 'texto': content})
        if len(result) >= 10:
            break
    return result


def collect_comments(video_url, progress):
    """Extrae hasta diez comentarios sin publicar ninguno.

    TikTok carga comentarios de forma diferida. Por eso primero intentamos
    activar el panel y desplazarlo. Reutilizamos el Firefox de Streamlit.
    """
    driver = ensure_driver()
    selector = '[data-e2e="comment-level-1"]'
    panel_buttons = (
        '[data-e2e="comment-icon"]',
        '[data-e2e="browse-comment-icon"]',
        '[data-e2e="comment-button"]',
    )
    best = []

    for carga in range(2):
        # Segundo intento: recargar solo si la primera visita no mostró nada.
        driver.get(video_url)
        time.sleep(2)

        for attempt in range(15):
            # Leer primero: algunos videos muestran comentarios de inmediato.
            current = comments_from_html(driver.page_source)
            if len(current) > len(best):
                best = current

            avance = (carga * 15 + attempt + 1) / 30
            progress.progress(min(avance, 1.0),
                              text=f'Leyendo comentarios automáticamente: {len(best)}/10')
            if len(best) >= 10:
                progress.progress(1.0, text='Se encontraron 10 comentarios')
                return best[:10]

            # Intentar activar el panel sin escribir ni publicar comentarios.
            # Si ya está abierto, no es necesario hacer clic.
            if not driver.find_elements(By.CSS_SELECTOR, selector):
                for button_selector in panel_buttons:
                    buttons = driver.find_elements(By.CSS_SELECTOR, button_selector)
                    if not buttons:
                        continue
                    try:
                        driver.execute_script('arguments[0].click();', buttons[0])
                        break
                    except WebDriverException:
                        continue

            # Desplazar el último comentario para activar la carga diferida.
            blocks = driver.find_elements(By.CSS_SELECTOR, selector)
            if blocks:
                try:
                    driver.execute_script(
                        'arguments[0].scrollIntoView({block:"end", behavior:"instant"});',
                        blocks[-1]
                    )
                    # La rueda se dirige al bloque: útil cuando TikTok usa
                    # un panel desplazable independiente de la página.
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(driver).move_to_element(blocks[-1]).scroll_by_amount(0, 350).perform()
                except WebDriverException:
                    pass
            else:
                driver.execute_script('window.scrollBy(0, 350)')

            time.sleep(1.5)

        # Si ya hay comentarios, no recargar: conservar los obtenidos.
        if best:
            break

    progress.progress(1.0, text=f'Consulta terminada: {len(best)} comentarios')
    return best[:10]



# ================================================================
# INTERFAZ PROFESIONAL: Streamlit + CSS
# La extracción Selenium/BeautifulSoup de arriba se mantiene intacta.
# ================================================================
st.set_page_config(
    page_title="TikTok Analytics | Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS únicamente visual: no cambia la lógica de scraping.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stAppViewContainer"] {font-family: 'Inter', sans-serif;}
[data-testid="stAppViewContainer"] {background: #0B111B; color: #E9EDF5;}
[data-testid="stSidebar"] {background: #101A29; border-right: 1px solid #243247;}
.block-container {max-width: 1500px; padding-top: 1.7rem; padding-bottom: 3rem;}
h1, h2, h3 {letter-spacing: -0.035em;}
h1 {font-size: 2.1rem !important; font-weight: 800 !important;}
h3 {font-size: 1.2rem !important;}
[data-testid="stMetric"] {background: #172232; border: 1px solid #2B3A4D; border-radius: 15px; padding: 18px 20px;}
[data-testid="stMetricLabel"] {color: #9BAFC5;}
[data-testid="stMetricValue"] {color: #F5F8FC; font-size: 1.65rem;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color: #29384B !important; border-radius: 15px !important;}
[data-testid="stForm"] {background: #131F2E; border: 1px solid #2B3A4D; border-radius: 15px; padding: 12px 16px;}
[data-testid="stTabs"] button {font-weight: 600;}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button {background: #F02E62; border-color: #F02E62; border-radius: 10px; font-weight: 700;}
.stButton button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button:hover {background: #D71C4E; border-color: #D71C4E;}
.stTextInput input {border-radius: 10px;}
.hero {background: linear-gradient(110deg,#17243A 0%,#1C1B34 58%,#2A1934 100%); border:1px solid #31405B; border-radius:20px; padding:24px 28px; margin-bottom:20px;}
.hero-title {font-size:1.9rem; font-weight:800; color:#FFFFFF; margin:0 0 6px;}
.hero-sub {color:#ACBBD0; font-size:.94rem; margin:0;}
.pill {display:inline-block; padding:5px 11px; border-radius:99px; background:#1C4A41; color:#69E3BE; font-size:.76rem; font-weight:700; margin-top:10px;}
.section-h {font-size:1.12rem; font-weight:750; color:#EAF0F8; margin:12px 0;}
.comment-author {font-weight:750; color:#F3F7FC; font-size:.94rem;}
.comment-num {display:inline-block; color:#F46A90; font-weight:750; margin-right:8px;}
.comment-body {color:#D3DFEC; margin-top:7px; font-size:.93rem; white-space:pre-wrap; overflow-wrap:anywhere;}
.empty-panel {border:1px dashed #344760; background:#111B2A; border-radius:16px; padding:30px 20px; text-align:center; color:#A6B8CC;}
.caption-soft {color:#90A5BD; font-size:.85rem;}
@media (max-width: 768px) {.block-container {padding:1rem .7rem;} .hero {padding:18px;} .hero-title {font-size:1.5rem;}}
</style>
""", unsafe_allow_html=True)

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

st.markdown("""<div class="hero">
<div class="hero-title">TikTok Analytics <span style="color:#F24876">●</span></div>
<p class="hero-sub">Dashboard de perfiles, publicaciones y comentarios públicos</p>
<span class="pill">● Selenium + BeautifulSoup + Streamlit</span>
</div>""", unsafe_allow_html=True)

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
    st.markdown('#### Resumen del perfil')
    st.markdown(f'<div class="caption-soft">@{escape(st.session_state.username)}</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('👤 Nombre', str(profile['nombre']))
    col2.metric('👥 Seguidores', str(profile['seguidores']))
    col3.metric('➕ Seguidos', str(profile['seguidos']))
    col4.metric('🎬 Publicaciones detectadas', len(videos))

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
        if comments is None:
            st.info('Pulsa el botón para cargar los comentarios de este video.')
        elif not comments:
            st.warning('No se detectaron comentarios accesibles. Puedes reintentar la consulta.')
        else:
            st.success(f'✅ {len(comments)} comentarios recuperados')
            filtro = st.text_input(
                'Buscar por autor o palabra',
                placeholder='Ej.: lopez, lindo, primero...',
                key=f"filtro_{video['id']}",
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
