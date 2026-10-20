"""TikTok Web Scraper: Streamlit + Selenium + BeautifulSoup.

Consulta información pública visible; no descarga videos ni exporta datos.
Requiere Firefox Developer Edition y un geckodriver compatible (Selenium Manager).
"""
import json
import re
import time
from pathlib import Path
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



