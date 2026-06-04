def clean_text(text):
    """Normalize whitespace while preserving document line structure."""
    if not text:
        return ""

    cleaned_lines = []
    for line in text.splitlines():
        normalized_line = line.strip()
        if normalized_line:
            cleaned_lines.append(normalized_line)

    return "\n".join(cleaned_lines)
