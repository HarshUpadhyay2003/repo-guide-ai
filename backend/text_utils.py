def truncate_text(text: str, max_length: int) -> str:
    """
    Truncates text to the specified maximum length.
    Appends '...' if the text was truncated.
    """
    if not text:
        return ""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text