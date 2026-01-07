import re

def sanitize_order_num(raw: str) -> str:
    if raw is None:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", raw.strip()).upper()