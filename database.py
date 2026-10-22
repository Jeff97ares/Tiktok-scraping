import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tiktok_data.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perfiles (
                username TEXT PRIMARY KEY,
                seguidores TEXT,
                seguidos TEXT,
                fecha_extraccion TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                username TEXT,
                url TEXT,
                FOREIGN KEY (username) REFERENCES perfiles(username)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                autor TEXT,
                texto TEXT,
                fecha_extraccion TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(video_id)
            )
        """)

        conn.commit()


def guardar_comentarios(video_id, comentarios):
    with get_connection() as conn:
        for comentario in comentarios:
            conn.execute(
                """
                INSERT INTO comentarios (video_id, autor, texto)
                VALUES (?, ?, ?)
                """,
                (
                    video_id,
                    comentario.get("autor", ""),
                    comentario.get("texto", "")
                )
            )

        conn.commit()


def obtener_comentarios():
    with get_connection() as conn:
        return conn.execute("""
            SELECT video_id, autor, texto
            FROM comentarios
            WHERE TRIM(texto) != ''
        """).fetchall()