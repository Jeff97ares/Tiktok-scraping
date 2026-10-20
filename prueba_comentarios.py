"""Diagnóstico de comentarios y autores de TikTok (Firefox Developer Edition).

Ejecuta: python prueba_comentarios_corregida.py
No modifica main.py ni descarga videos. Espera tu confirmación antes de analizar.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

FIREFOX_DEV = Path(r"C:\Program Files\Firefox Developer Edition\firefox.exe")
SELECTOR_COMENTARIO = '[data-e2e="comment-level-1"]'
SELECTOR_AUTOR = '[data-e2e="comment-username-1"]'
SELECTORES_TEXTO = ('[data-e2e="comment-text"]', '[class*="CommentText"]')


def url_valida(url):
    try:
        parsed = urlparse(url)
        return (parsed.scheme in ('http', 'https')
                and (parsed.hostname or '').lower() in ('www.tiktok.com', 'tiktok.com', 'm.tiktok.com')
                and bool(re.search(r'/@[^/]+/video/\d+', parsed.path)))
    except ValueError:
        return False


def obtener_texto(elemento):
    try:
        return (elemento.text or '').strip()
    except (WebDriverException, StaleElementReferenceException):
        return ''


def diagnosticar(driver):
    print('\n===== ESTADO =====')
    print('URL:', driver.current_url)
    print('Título:', driver.title)

    bloques = driver.find_elements(By.CSS_SELECTOR, SELECTOR_COMENTARIO)
    autores_pagina = driver.find_elements(By.CSS_SELECTOR, SELECTOR_AUTOR)
    print('\nBloques de texto detectados:', len(bloques))
    print('Autores detectados en toda la página:', len(autores_pagina))

    print('\n===== AUTORES VISIBLES EN LA PÁGINA =====')
    for i, autor in enumerate(autores_pagina[:15], 1):
        nombre = obtener_texto(autor)
        try:
            enlace = autor.find_element(By.XPATH, './ancestor::a[1]').get_attribute('href')
        except WebDriverException:
            enlace = '(sin enlace)'
        print(f'{i}. {nombre or "(sin nombre visible)"} | {enlace}')

    if not bloques:
        print('\nNo se encontraron bloques de comentarios. Revisa si están visibles en Firefox.')
        return

    print('\n===== COMENTARIOS Y BÚSQUEDA DEL AUTOR EN SUS ANCESTROS =====')
    for i, bloque in enumerate(bloques[:10], 1):
        texto = obtener_texto(bloque)
        print(f'\nComentario {i}: {texto[:300]!r}')
        # Los nombres pueden estar fuera del nodo de texto: subir por los padres.
        encontrado = False
        for nivel in range(1, 7):
            try:
                padre = bloque.find_element(By.XPATH, './' + '/'.join(['..'] * nivel))
                autores = padre.find_elements(By.CSS_SELECTOR, SELECTOR_AUTOR)
                nombres = [obtener_texto(a) for a in autores if obtener_texto(a)]
                if nombres:
                    print(f'  Autor(es) en ancestro nivel {nivel}: {nombres[:5]}')
                    print('  Etiqueta contenedora:', padre.tag_name)
                    print('  Clase contenedora:', (padre.get_attribute('class') or '')[:180])
                    encontrado = True
                    break
            except (WebDriverException, StaleElementReferenceException):
                break
        if not encontrado:
            print('  Autor no localizado en los primeros 6 ancestros.')

    print('\n===== HTML DEL PRIMER COMENTARIO Y CONTENEDOR PADRE =====')
    try:
        primer = bloques[0]
        print('BLOQUE:', (primer.get_attribute('outerHTML') or '')[:2500])
        padre = primer.find_element(By.XPATH, '..')
        print('\nPADRE:', (padre.get_attribute('outerHTML') or '')[:6000])
    except WebDriverException as exc:
        print('No fue posible obtener el HTML:', str(exc)[:200])
    print('\nRevisa los datos antes de compartir la salida: puede incluir nombres y enlaces públicos.')


def main():
    url = input('Pega la URL completa de un video de TikTok: ').strip()
    if not url_valida(url):
        print('URL inválida. Ejemplo: https://www.tiktok.com/@usuario/video/1234567890123456789')
        return

    opciones = Options()
    if FIREFOX_DEV.is_file():
        opciones.binary_location = str(FIREFOX_DEV)

    driver = None
    try:
        print('\nAbriendo Firefox...')
        driver = webdriver.Firefox(options=opciones)
        driver.set_page_load_timeout(60)
        try:
            driver.get(url)
        except WebDriverException as exc:
            print('Aviso durante la carga:', str(exc)[:200])

        print('\nComprueba que los comentarios y sus nombres se vean en Firefox.')
        print('Si hace falta, abre el panel de comentarios manualmente.')
        input('Cuando estén visibles, vuelve a la terminal y pulsa Enter para ANALIZAR... ')
        diagnosticar(driver)
        input('\nPulsa Enter para cerrar Firefox y terminar... ')
    except KeyboardInterrupt:
        print('\nPrueba interrumpida.')
    except WebDriverException as exc:
        print('\nError de Selenium:', exc)
    finally:
        if driver is not None:
            try:
                driver.quit()
            except WebDriverException:
                pass


if __name__ == '__main__':
    main()
