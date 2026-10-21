"""Extracción de información pública de perfiles y videos de TikTok.

Este módulo reúne la lógica de scraping del proyecto:
- Selenium controla Firefox Developer Edition y carga contenido dinámico.
- BeautifulSoup interpreta el HTML para obtener perfiles, videos y comentarios.
- Streamlit conserva la sesión del navegador y muestra el progreso.

Flujo principal:
    main.py -> collect_profile() -> profile_from_html() / videos_from_html()
    main.py -> collect_comments() -> comments_from_html()

Nota: los resultados dependen del HTML y de las restricciones de TikTok.
El módulo no publica comentarios ni descarga videos.
"""

import json  # Permite leer y convertir datos JSON a estructuras de Python.

import re  # Permite utilizar expresiones regulares para validar usuarios y extraer IDs de videos.

import time  # Permite establecer pausas para esperar que TikTok cargue contenido.

from pathlib import Path  # Permite manejar rutas de archivos, como la ubicación de Firefox.

from urllib.parse import urlparse  # Permite separar y analizar las partes de una URL.


import streamlit as st  # Permite gestionar la sesión del navegador y mostrar el progreso en la interfaz.

from bs4 import BeautifulSoup  # Permite analizar el HTML y extraer información de TikTok.

from selenium import webdriver  # Permite controlar y automatizar el navegador Firefox.

from selenium.common.exceptions import TimeoutException, WebDriverException  # Permite manejar errores de espera y del navegador.

from selenium.webdriver.common.by import By  # Permite localizar elementos HTML mediante selectores CSS, ID, etc.

from selenium.webdriver.firefox.options import Options  # Permite configurar Firefox antes de iniciarlo.

from selenium.webdriver.support.ui import WebDriverWait  # Permite esperar hasta que aparezcan elementos en la página.


# Ruta opcional del ejecutable de Firefox Developer Edition.
DEVELOPER_EXE = Path(r"C:\Program Files\Firefox Developer Edition\firefox.exe")

# Expresión regular: extrae el usuario y el ID de una URL de video.
VIDEO_RE = re.compile(r"/@([^/?#]+)/video/(\d{15,22})")

# Cambia estos dos valores para ajustar los límites de extracción.
MAX_VIDEOS = 10
MAX_COMENTARIOS = 10

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

    """Valida y normaliza un nombre de usuario o enlace de TikTok.

    Args:
        value (str): Nombre con o sin @, o URL del perfil.
    Returns:
        str: Nombre de usuario sin @.
    Raises:
        ValueError: Si la URL no es de TikTok o el usuario no es válido.
    """
    # Elimina espacios al inicio y al final de la entrada.
    value = value.strip()

    if value.startswith(('https://', 'http://')):

        # Separa la URL en componentes para verificar el dominio.
        parsed = urlparse(value)

        if (parsed.hostname or '').lower() not in ('tiktok.com', 'www.tiktok.com', 'm.tiktok.com'):

            raise ValueError('El enlace debe pertenecer a TikTok.')

        value = parsed.path.strip('/').split('/')[0]

    # Acepta usuarios escritos con o sin @.
    value = value.lstrip('@')

    if not re.fullmatch(r'[A-Za-z0-9._]{1,24}', value):

        raise ValueError('Introduce un usuario o enlace válido de TikTok.')

    return value


def json_scripts(soup):

    """Genera objetos Python a partir de scripts con JSON válido.

    Args:
        soup (BeautifulSoup): Documento HTML previamente analizado.
    Yields:
        dict | list: Datos JSON decodificados; omite scripts no válidos.
    """
    # Recorre los bloques <script> que podrían contener datos JSON.
    for script in soup.find_all('script'):

        raw = (script.string or script.get_text() or '').strip()

        if raw.startswith(('{', '[')):

            try:

                # Convierte JSON a objetos Python y los entrega uno a uno.
                yield json.loads(raw)

            except (ValueError, TypeError):

                pass


def profile_from_html(html):

    """Extrae el nombre visible y las estadísticas de un perfil.

    Busca datos incrustados en scripts JSON de TikTok. Si no encuentra
    un campo, conserva su valor predeterminado.

    Args:
        html (str): Código HTML del perfil.
    Returns:
        dict: Campos nombre, seguidores y seguidos.
    """
    # Prepara valores de respaldo cuando faltan datos.
    profile = {'nombre': 'No disponible', 'seguidores': 'N/D', 'seguidos': 'N/D'}

    for data in json_scripts(BeautifulSoup(html, 'html.parser')):

        if not isinstance(data, dict):

            continue

        # Intenta obtener los datos del perfil del formato JSON principal.
        scope = data.get('__DEFAULT_SCOPE__', {})

        info = scope.get('webapp.user-detail', {}).get('userInfo', {}) if isinstance(scope, dict) else {}

        if not info:

            # Busca una estructura alternativa utilizada por TikTok.
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

    """Obtiene hasta diez publicaciones pertenecientes al perfil indicado.

    Combina enlaces HTML con datos JSON incrustados. El ID del video
    se usa como clave para evitar duplicados.

    Args:
        html (str): HTML del perfil.
        username (str): Nombre del propietario del perfil.
    Returns:
        list[dict]: Videos con id, url y descripcion.
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Usa un diccionario para evitar repetir IDs de videos.
    found = {}


    # Función interna: valida un video y lo añade si corresponde al usuario.
    def add(video_id, description='', author=None):

        video_id = str(video_id or '')

        if not re.fullmatch(r'\d{15,22}', video_id) or len(found) >= MAX_VIDEOS:

            return

        if author and str(author).lstrip('@').lower() != username.lower():

            return

        found.setdefault(video_id, {

            'id': video_id,

            'url': f'https://www.tiktok.com/@{username}/video/{video_id}',

            'descripcion': str(description or 'Descripción no disponible')[:300]

        })


    # Primera estrategia: localizar enlaces de publicaciones en HTML.
    for link in soup.select('a[href*="/video/"]'):

        match = VIDEO_RE.search(link.get('href', ''))

        if match and match.group(1).lower() == username.lower():

            add(match.group(2), link.get('title') or link.get_text(' ', strip=True))


    # Segunda estrategia: recorrer recursivamente listas y diccionarios JSON.
    def walk(node, depth=0):

        if depth > 20 or len(found) >= MAX_VIDEOS:

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


    # Analiza datos estructurados incrustados en scripts.
    for data in json_scripts(soup):

        walk(data)

        if len(found) >= MAX_VIDEOS:

            break

    return list(found.values())


def make_driver():

    """Inicia una sesión de Firefox controlada mediante Selenium.

    Si existe Firefox Developer Edition en la ruta configurada, lo usa;
    en caso contrario, Selenium intenta encontrar Firefox normalmente.
    Returns:
        WebDriver: Controlador de Firefox.
    """
    # Configura el navegador antes de iniciarlo.
    options = Options()

    if DEVELOPER_EXE.is_file():

        options.binary_location = str(DEVELOPER_EXE)

    # Crea la sesión automatizada de Firefox.
    driver = webdriver.Firefox(options=options)

    # Evita esperas indefinidas durante la carga de páginas.
    driver.set_page_load_timeout(45)

    return driver


def driver_alive(driver):

    """Comprueba si el controlador responde y tiene ventanas abiertas.

    Args:
        driver: Sesión WebDriver o None.
    Returns:
        bool: True si la sesión responde y tiene ventanas; False si no.
    """
    try:

        # Comprueba si hay un controlador y ventanas disponibles.
        return bool(driver and driver.window_handles)

    except WebDriverException:

        return False


def ensure_driver():

    """Recupera Firefox desde la sesión de Streamlit o crea uno nuevo.

    Returns:
        WebDriver: Sesión disponible para navegar por TikTok.
    """
    # Recupera la sesión conservada entre ejecuciones de Streamlit.
    driver = st.session_state.get('driver')

    # Solo abre otro navegador si el anterior no está disponible.
    if not driver_alive(driver):

        driver = make_driver()

        st.session_state.driver = driver

    return driver


def collect_profile(username, progress):

    """Abre un perfil y recopila sus datos y hasta diez videos.

    Utiliza dos métodos para encontrar videos: análisis del HTML y
    búsqueda directa de enlaces con Selenium. Desplaza la página
    para intentar cargar publicaciones adicionales.

    Args:
        username (str): Usuario de TikTok previamente validado.
        progress: Componente de progreso creado en Streamlit.
    Returns:
        tuple[dict, list[dict]]: Perfil y lista de publicaciones.
    """
    driver = ensure_driver()

    # Abre la URL del perfil en Firefox.
    driver.get(f'https://www.tiktok.com/@{username}')

    try:

        # Espera hasta 25 segundos por datos incrustados o enlaces de videos.
        WebDriverWait(driver, 25).until(lambda d:

            d.find_elements(By.ID, '__UNIVERSAL_DATA_FOR_REHYDRATION__') or

            d.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]'))

    except TimeoutException:

        pass

    # Analiza el HTML actual para obtener nombre y estadísticas.
    profile = profile_from_html(driver.page_source)

    # Acumula publicaciones sin duplicar IDs.
    videos = {}

    # Realiza hasta doce rondas de búsqueda y desplazamiento.
    for attempt in range(12):

        # Extrae publicaciones desde HTML y JSON.
        for video in videos_from_html(driver.page_source, username):

            videos.setdefault(video['id'], video)

        # Complementa la extracción con enlaces encontrados por Selenium.
        for el in driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]'):

            match = VIDEO_RE.search(el.get_attribute('href') or '')

            if match and match.group(1).lower() == username.lower():

                video_id = match.group(2)

                videos.setdefault(video_id, {'id': video_id,

                    'url': f'https://www.tiktok.com/@{username}/video/{video_id}',

                    'descripcion': 'Descripción no disponible'})

        # Actualiza el avance en la interfaz.
        progress.progress(min(len(videos), MAX_VIDEOS) / MAX_VIDEOS, text=f'Publicaciones encontradas: {min(len(videos), MAX_VIDEOS)}/{MAX_VIDEOS}')

        # Termina anticipadamente al alcanzar el objetivo.
        if len(videos) >= MAX_VIDEOS:

            break

        # Desplaza la página para intentar cargar más videos.
        driver.execute_script('window.scrollBy(0, 650)')

        time.sleep(1.5)

    return profile, list(videos.values())[:MAX_VIDEOS]


def comments_from_html(html):

    """Extrae hasta diez comentarios y sus autores del mismo contenedor.

    El nombre del autor y el texto son elementos relacionados mediante
    un contenedor padre. Se descartan entradas vacías y combinaciones
    repetidas de autor y comentario.

    Args:
        html (str): HTML de la página de un video.
    Returns:
        list[dict]: Elementos con autor y texto.
    """

    soup = BeautifulSoup(html, 'html.parser')

    # La lista guarda resultados y el conjunto ayuda a evitar duplicados.
    result, seen = [], set()


    # Busca elementos de comentarios de primer nivel.
    for text_el in soup.select('[data-e2e="comment-level-1"]'):

        content = text_el.get_text(' ', strip=True)

        if not content:

            continue


        # El autor NO está dentro del span del comentario, sino en su padre.

        # Sube al contenedor que agrupa el comentario con su autor.
        parent = text_el.parent

        # Intenta obtener el autor desde el contenedor compartido.
        author_el = parent.select_one('[data-e2e="comment-username-1"]') if parent else None

        author = author_el.get_text(' ', strip=True) if author_el else ''


        # Alternativa: recuperar @usuario desde el enlace del mismo contenedor.

        # Si no aparece el nombre, busca su enlace de perfil.
        if not author and parent:

            link = parent.select_one('a[href^="/@"]')

            if link:

                match = re.search(r'/@([^/?#]+)', link.get('href', ''))

                if match:

                    author = '@' + match.group(1)

        if not author:

            author = 'Usuario no disponible'


        # Considera duplicada la misma combinación de autor y texto.
        key = (author, content)

        if key in seen:

            continue

        seen.add(key)

        # Almacena el comentario con sus dos campos.
        result.append({'autor': author, 'texto': content})

        if len(result) >= MAX_COMENTARIOS:

            break

    return result


def collect_comments(video_url, progress):

    """Carga y extrae hasta diez comentarios visibles de un video.

    Reutiliza Firefox, intenta abrir el panel de comentarios y lo desplaza
    para activar la carga diferida. Puede repetir la carga si el primer
    ciclo no encuentra comentarios. No escribe ni publica contenido.

    Args:
        video_url (str): Dirección del video.
        progress: Componente de progreso de Streamlit.
    Returns:
        list[dict]: Comentarios con autor y texto (hasta diez).
    """

    # Reutiliza la sesión de Firefox.
    driver = ensure_driver()

    selector = '[data-e2e="comment-level-1"]'

    # Define selectores alternativos para abrir el panel de comentarios.
    panel_buttons = (

        '[data-e2e="comment-icon"]',

        '[data-e2e="browse-comment-icon"]',

        '[data-e2e="comment-button"]',

    )

    # Conserva la lista más numerosa encontrada.
    best = []


    # Permite un segundo ciclo solo si el primero no obtuvo comentarios.
    for carga in range(2):

        # Segundo intento: recargar solo si la primera visita no mostró nada.

        driver.get(video_url)

        time.sleep(2)


        # Realiza hasta quince intentos por ciclo.
        for attempt in range(15):

            # Leer primero: algunos videos muestran comentarios de inmediato.

            # Lee los comentarios actualmente presentes en el HTML.
            current = comments_from_html(driver.page_source)

            if len(current) > len(best):

                best = current


            # Calcula el avance según el número de intentos.
            avance = (carga * 15 + attempt + 1) / 30

            progress.progress(min(avance, 1.0),

                              text=f'Leyendo comentarios automáticamente: {len(best)}/{MAX_COMENTARIOS}')

            # Devuelve inmediatamente los diez comentarios al completar el objetivo.
            if len(best) >= MAX_COMENTARIOS:

                progress.progress(1.0, text=f'Se encontraron {MAX_COMENTARIOS} comentarios')

                return best[:MAX_COMENTARIOS]


            # Intentar activar el panel sin escribir ni publicar comentarios.

            # Si ya está abierto, no es necesario hacer clic.

            # Si aún no hay comentarios, intenta abrir el panel.
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

            # Localiza los bloques visibles para desplazarse dentro del panel.
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

        # No recarga el video cuando ya hay comentarios.
        if best:

            break


    progress.progress(1.0, text=f'Consulta terminada: {len(best)} comentarios')

    return best[:MAX_COMENTARIOS]
