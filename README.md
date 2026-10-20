# TikTok Web Scraper

Aplicación web desarrollada en Python para consultar y visualizar información pública de perfiles de TikTok.

## Tecnologías utilizadas

- Python
- Streamlit
- Selenium
- BeautifulSoup
- Firefox Developer Edition

## Funcionalidades

- Consulta de perfiles públicos.
- Visualización de seguidores y seguidos.
- Identificación de hasta 10 publicaciones.
- Reproductor integrado de videos.
- Extracción de hasta 10 comentarios visibles por video.
- Identificación de los autores de los comentarios.
- Dashboard interactivo para presentar resultados.

## Instalación

Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

Ejecutar la aplicación:

```bash
python -m streamlit run main.py
```

## Consideraciones

La aplicación consulta información pública visible en TikTok. La disponibilidad de los datos depende de la plataforma y de sus restricciones de acceso. No descarga videos ni publica comentarios.