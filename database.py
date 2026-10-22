
"""Almacenamiento local de perfiles, videos y comentarios de TikTok."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "tiktok_data.db"


def conectar():
    """Abre una conexión con la base de datos SQLite."""
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def _agregar_columna_si_falta(conn, tabla, columna, tipo):
    """Amplía tablas existentes sin eliminar registros ni recrear tablas."""
    columnas = {fila[1] for fila in conn.execute(f"PRAGMA table_info({tabla})")}
    if columna not in columnas:
        conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")


def inicializar_db():
    """Crea las tablas si todavía no existen y migra esquemas anteriores."""
    with conectar() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS perfiles (
                username TEXT PRIMARY KEY,
                nombre TEXT,
                seguidores TEXT,
                seguidos TEXT,
                fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP,
                biografia TEXT
            );

            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                url TEXT NOT NULL,
                descripcion TEXT,
                fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP,
                fecha_publicacion TEXT,
                FOREIGN KEY (username) REFERENCES perfiles(username)
            );

            CREATE TABLE IF NOT EXISTS comentarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                autor TEXT NOT NULL,
                texto TEXT NOT NULL,
                fecha_extraccion TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(video_id, autor, texto),
                FOREIGN KEY (video_id) REFERENCES videos(video_id)
            );
        """)
        # CREATE TABLE IF NOT EXISTS no modifica tablas que ya existen.
        _agregar_columna_si_falta(conn, "perfiles", "biografia", "TEXT")
        _agregar_columna_si_falta(conn, "videos", "fecha_publicacion", "TEXT")


def guardar_perfil(username, perfil, videos):
    """Guarda o actualiza un perfil y sus publicaciones."""
    # Permite ejecutar esta función incluso en instalaciones aún no migradas.
    inicializar_db()
    with conectar() as conn:
        conn.execute("""
            INSERT INTO perfiles
                (username, nombre, seguidores, seguidos, biografia)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                nombre = excluded.nombre,
                seguidores = excluded.seguidores,
                seguidos = excluded.seguidos,
                biografia = COALESCE(excluded.biografia, perfiles.biografia),
                fecha_actualizacion = CURRENT_TIMESTAMP
        """, (
            username,
            str(perfil.get("nombre", "")),
            str(perfil.get("seguidores", "")),
            str(perfil.get("seguidos", "")),
            perfil.get("biografia") or None,
        ))

        for video in videos:
            conn.execute("""
                INSERT INTO videos
                    (video_id, username, url, descripcion, fecha_publicacion)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    username = excluded.username,
                    url = excluded.url,
                    descripcion = CASE
                        WHEN excluded.descripcion IS NULL
                          OR TRIM(excluded.descripcion) = ''
                          OR excluded.descripcion = 'Descripción no disponible'
                        THEN videos.descripcion
                        ELSE excluded.descripcion
                    END,
                    fecha_publicacion = COALESCE(
                        excluded.fecha_publicacion, videos.fecha_publicacion
                    ),
                    fecha_actualizacion = CURRENT_TIMESTAMP
            """, (
                str(video["id"]),
                username,
                video["url"],
                video.get("descripcion", ""),
                video.get("fecha_publicacion") or None,
            ))


def guardar_comentarios(video_id, comentarios):
    """Guarda comentarios sin duplicar autor y texto en el mismo video."""
    nuevos = 0

    with conectar() as conn:
        for comentario in comentarios:
            autor = str(comentario.get("autor", "")).strip()
            texto = str(comentario.get("texto", "")).strip()

            if not texto:
                continue

            cursor = conn.execute("""
                INSERT OR IGNORE INTO comentarios
                    (video_id, autor, texto)
                VALUES (?, ?, ?)
            """, (str(video_id), autor, texto))

            nuevos += cursor.rowcount

    return nuevos


def obtener_comentarios(video_id=None):
    """Consulta los comentarios almacenados."""
    consulta = """
        SELECT
            c.video_id,
            v.url,
            c.autor,
            c.texto,
            c.fecha_extraccion
        FROM comentarios AS c
        JOIN videos AS v ON v.video_id = c.video_id
    """

    parametros = ()

    if video_id is not None:
        consulta += " WHERE c.video_id = ?"
        parametros = (str(video_id),)

    consulta += " ORDER BY c.id DESC"

    with conectar() as conn:
        conn.row_factory = sqlite3.Row
        return [
            dict(fila)
            for fila in conn.execute(consulta, parametros)
        ]


def obtener_estadisticas():
    """Devuelve la cantidad de registros almacenados."""
    with conectar() as conn:
        perfiles = conn.execute(
            "SELECT COUNT(*) FROM perfiles"
        ).fetchone()[0]

        videos = conn.execute(
            "SELECT COUNT(*) FROM videos"
        ).fetchone()[0]

        comentarios = conn.execute(
            "SELECT COUNT(*) FROM comentarios"
        ).fetchone()[0]

    return {
        "perfiles": perfiles,
        "videos": videos,
        "comentarios": comentarios,
    }
