<div align="center">

# 🎵 TikTok Scraping

### Dashboard de consulta y visualización de perfiles, publicaciones y comentarios públicos de TikTok

**Python · Streamlit · Selenium · BeautifulSoup · Firefox**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Selenium](https://img.shields.io/badge/Selenium-Automatizaci%C3%B3n-43B02A?logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-HTML-555555)](https://www.crummy.com/software/BeautifulSoup/)
[![GitHub](https://img.shields.io/badge/Repositorio-GitHub-181717?logo=github&logoColor=white)](https://github.com/Jeff97ares/Tiktok-scraping)

**[Ver repositorio](https://github.com/Jeff97ares/Tiktok-scraping)**

</div>

---

## 📌 Descripción

**TikTok Scraping** es una aplicación web desarrollada con Python que permite consultar y visualizar información pública de perfiles de TikTok mediante un dashboard interactivo.

Combina **Selenium** para automatizar la navegación en Firefox, **BeautifulSoup** para analizar el HTML y **Streamlit** para presentar los resultados en una interfaz moderna. La aplicación permite explorar publicaciones, reproducir videos mediante el reproductor oficial y consultar comentarios visibles junto con los nombres de sus autores.

> **Alcance:** herramienta de consulta y visualización. No descarga videos, no publica comentarios y no incorpora una función de exportación de datos.

## ✨ Funcionalidades

| Funcionalidad | Descripción |
|---|---|
| 🔎 Búsqueda de perfiles | Consulta mediante nombre de usuario (`@usuario`) o enlace de TikTok. |
| 👤 Resumen del perfil | Muestra el nombre visible, el número de seguidores y las cuentas seguidas, cuando están disponibles. |
| 🎬 Exploración de publicaciones | Identifica hasta **10 videos** accesibles del perfil consultado. |
| ▶️ Reproductor integrado | Permite visualizar la publicación seleccionada con el reproductor oficial de TikTok. |
| 💬 Consulta de comentarios | Intenta recuperar hasta **10 comentarios visibles** por publicación. |
| 🧑 Autores de comentarios | Presenta el autor junto al texto del comentario cuando esa información está disponible. |
| 🔍 Filtro de comentarios | Busca por autor o por palabras dentro de los comentarios recuperados. |
| 🌐 Sesión reutilizable | Mantiene una sesión de Firefox para las consultas realizadas durante la sesión de Streamlit. |
| 📊 Dashboard profesional | Incluye tarjetas de estadísticas, menú lateral y presentación de video y comentarios en columnas. |

**Nota:** la cantidad de videos y comentarios recuperados puede ser menor a diez. Depende de la visibilidad del contenido, la carga de la página y los cambios que TikTok realice en su interfaz.

## 🖥️ Interfaz

El dashboard está organizado en tres áreas:

1. **Búsqueda y resumen:** ingreso del perfil y visualización de estadísticas.
2. **Publicación seleccionada:** descripción, enlace directo y reproductor de TikTok.
3. **Comentarios:** botón de consulta, listado de autores y textos, y filtro de búsqueda.

<!-- Puedes agregar una captura real del dashboard más adelante:
![Dashboard de TikTok Scraping](docs/dashboard.png)
-->

## 🧰 Tecnologías utilizadas

| Tecnología | Uso en el proyecto |
|---|---|
| **Python** | Lenguaje principal de desarrollo. |
| **Streamlit** | Interfaz web y gestión del estado de la aplicación. |
| **Selenium WebDriver** | Navegación automatizada y carga dinámica del contenido. |
| **Firefox Developer Edition** | Navegador utilizado para las consultas automatizadas. |
| **BeautifulSoup** | Análisis del HTML y extracción de información visible. |
| **HTML y CSS** | Personalización visual del dashboard. |
| **Git y GitHub** | Control de versiones y publicación del código fuente. |

## 🏗️ Arquitectura modular

El proyecto se organiza en archivos independientes para facilitar su mantenimiento:

```text
TikTok_Scraper/
├── main.py             # Aplicación principal y flujo de Streamlit
├── scraper.py          # Selenium, BeautifulSoup y extracción de información
├── styles.py           # Estilos CSS del dashboard
├── components.py       # Componentes visuales reutilizables
├── requirements.txt    # Dependencias de Python
├── README.md           # Documentación del proyecto
└── .gitignore          # Archivos excluidos del control de versiones
```

**Responsabilidades de cada módulo:**

- **`main.py`:** coordina las búsquedas, administra los resultados y presenta la aplicación.
- **`scraper.py`:** abre o reutiliza Firefox, obtiene datos del perfil, detecta publicaciones y extrae comentarios y autores.
- **`styles.py`:** concentra la apariencia visual y los estilos CSS.
- **`components.py`:** agrupa elementos de interfaz que pueden reutilizarse.

Esta separación permite modificar la presentación sin reescribir la lógica de extracción.

## ⚙️ Instalación y ejecución

### 1. Requisitos previos

- Python **3.9 o superior**.
- Git (para clonar el repositorio).
- Firefox Developer Edition o una instalación de Firefox compatible con Selenium.
- Conexión a Internet.

> **Importante:** el código actual contempla una ruta de Firefox Developer Edition en Windows. Si Firefox está instalado en otra ubicación o utilizas otro sistema operativo, revisa la constante `DEVELOPER_EXE` en `scraper.py`. Selenium puede utilizar el Firefox disponible en el sistema si no encuentra esa ruta.

### 2. Clonar el repositorio

```bash
git clone https://github.com/Jeff97ares/Tiktok-scraping.git
cd Tiktok-scraping
```

### 3. Crear un entorno virtual

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
python -m pip install -r requirements.txt
```

### 5. Ejecutar la aplicación

```bash
python -m streamlit run main.py
```

Abre la dirección local indicada en la terminal, normalmente **http://localhost:8501**.

## 🚀 Cómo utilizar la aplicación

1. Escribe un nombre de usuario de TikTok o pega el enlace de un perfil público.
2. Selecciona **Consultar perfil** y espera a que Firefox cargue la información.
3. Revisa las estadísticas y selecciona una de las publicaciones detectadas.
4. Utiliza el reproductor integrado para visualizar el video.
5. Haz clic en **Consultar hasta 10 comentarios**.
6. Explora los comentarios recuperados y utiliza el filtro para localizar autores o palabras.

La aplicación no requiere escribir ni publicar comentarios en TikTok.

## 🔍 ¿Cómo funciona la extracción?

```text
Usuario introduce un perfil
            │
            ▼
Streamlit valida el usuario o enlace
            │
            ▼
Selenium abre o reutiliza Firefox
            │
            ▼
Se carga el perfil y se detectan publicaciones
            │
            ▼
BeautifulSoup analiza el HTML disponible
            │
            ▼
Streamlit presenta estadísticas y videos
            │
            ▼
Usuario selecciona un video y solicita comentarios
            │
            ▼
Selenium activa la carga de comentarios visibles
            │
            ▼
BeautifulSoup identifica texto y autor
            │
            ▼
Dashboard muestra los resultados
```

**Detalle técnico:** el nombre del autor y el texto del comentario pueden encontrarse en elementos hermanos dentro de un mismo contenedor HTML. El extractor localiza el contenedor compartido para asociar correctamente cada comentario con su autor.

## ⚠️ Limitaciones y uso responsable

- La aplicación está diseñada para consultar **contenido público accesible**.
- No permite acceder a perfiles privados ni garantiza resultados para todos los perfiles o publicaciones.
- TikTok puede modificar su estructura HTML, sus mecanismos de carga o sus restricciones de acceso, por lo que algunos selectores podrían necesitar mantenimiento.
- Los tiempos de consulta dependen de la conexión, la respuesta del sitio y la carga dinámica de los comentarios.
- Los resultados no representan necesariamente todos los videos o comentarios de un perfil.
- Utiliza la herramienta respetando la privacidad de las personas, los términos aplicables de la plataforma y la normativa vigente.

## 🛠️ Posibles mejoras

- [ ] Incorporar pruebas automatizadas para las funciones de extracción.
- [ ] Mejorar el manejo de errores y los mensajes de diagnóstico.
- [ ] Optimizar los tiempos de espera y los intentos de carga.
- [ ] Añadir capturas reales del dashboard a la documentación.
- [ ] Revisar y simplificar las dependencias del proyecto.

## 📚 Aprendizajes del proyecto

Este desarrollo permitió trabajar con automatización de navegadores, análisis de documentos HTML, contenido cargado dinámicamente, gestión de sesiones en Streamlit, diseño de interfaces web y **programación modular**. Además, se utilizó Git para conservar una versión funcional antes de reorganizar el código y posteriormente integrar los cambios en la rama principal.

---

<div align="center">

**Proyecto desarrollado con Python, Selenium, BeautifulSoup y Streamlit.**

[⬆ Volver al inicio](#-tiktok-scraping)

</div>
