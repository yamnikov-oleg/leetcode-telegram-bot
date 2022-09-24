from datetime import datetime
from zoneinfo import ZoneInfo


def now():
    return datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))


def escape_html(s: str) -> str:
    return s.replace("<", "&lt;").replace(">", "&gt;")
