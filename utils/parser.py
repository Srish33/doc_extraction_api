import html
from . import formatter as formatter_mod

def clean_text(text_input: str) -> str:
    """Sanitizes raw text strings coming from PDFs to strip malicious characters."""
    if not text_input:
        return ""

    raw_text_string = str(text_input)
    sanitized = html.escape(raw_text_string)

    malicious_phrases = [
        "ignore previous instructions",
        "system override",
        "you are now an admin",
    ]
    for phrase in malicious_phrases:
        if phrase in sanitized.lower():
            sanitized = sanitized.replace(phrase, "[REDACTED INJECTION INTERCEPT]")

    return formatter_mod._normalize_line(sanitized)