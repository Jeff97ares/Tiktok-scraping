"""Metadatos públicos adicionales de TikTok presentes en HTML/JSON."""
import json
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

COUNT_RE = re.compile(r'^\s*\d+(?:[.,]\d+)?\s*[KMB]?\s*$', re.I)


def clean_description(value):
    """Devuelve solo texto descriptivo, nunca contadores de visualizaciones."""
    if not isinstance(value, str):
        return None
    value = ' '.join(value.split()).strip()
    if not value or value.lower() in ('descripción no disponible', 'descripcion no disponible'):
        return None
    if COUNT_RE.fullmatch(value):
        return None
    return value[:1000]


def _scripts_json(html):
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup.find_all('script'):
        raw = (script.string or script.get_text() or '').strip()
        if raw.startswith(('{', '[')):
            try:
                yield json.loads(raw)
            except (ValueError, TypeError):
                continue


def _walk(node, depth=0):
    if depth > 25:
        return
    if isinstance(node, dict):
        yield node
        for val in node.values():
            if isinstance(val, (dict, list)):
                yield from _walk(val, depth + 1)
    elif isinstance(node, list):
        for val in node:
            if isinstance(val, (dict, list)):
                yield from _walk(val, depth + 1)


def _date(value):
    try:
        stamp = int(value)
        if stamp > 10**12:
            stamp //= 1000
        if 946684800 <= stamp <= 4102444800:
            return datetime.fromtimestamp(stamp, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        pass
    return None


def extract_profile_extras(html, username, video_ids=None):
    """Obtiene biografía y metadatos de publicaciones vinculadas al usuario.

    Solo asocia fechas/descripciones a IDs existentes y no inventa datos ausentes.
    """
    username = str(username).lstrip('@').lower()
    allowed = {str(x) for x in (video_ids or [])}
    bio, dates, descriptions = None, {}, {}
    for data in _scripts_json(html):
        for node in _walk(data):
            user = node.get('user')
            if isinstance(user, dict) and str(user.get('uniqueId', '')).lstrip('@').lower() == username:
                bio = clean_description(user.get('signature')) or bio
            if str(node.get('uniqueId', '')).lstrip('@').lower() == username:
                bio = clean_description(node.get('signature')) or bio

            # Formatos habituales: itemModule[id] o registros con campo id.
            candidates = []
            video_id = str(node.get('id') or '')
            if video_id in allowed:
                candidates.append((video_id, node))
            module = node.get('itemModule')
            if isinstance(module, dict):
                candidates.extend((str(k), v) for k, v in module.items() if str(k) in allowed and isinstance(v, dict))
            for vid, item in candidates:
                author = item.get('author')
                if isinstance(author, dict):
                    author = author.get('uniqueId')
                if author and str(author).lstrip('@').lower() != username:
                    continue
                published = _date(item.get('createTime'))
                if published:
                    dates[vid] = published
                desc = clean_description(item.get('desc')) or clean_description(item.get('description'))
                if desc:
                    descriptions[vid] = desc
    return {'biografia': bio, 'fechas_videos': dates, 'descripciones_videos': descriptions}
