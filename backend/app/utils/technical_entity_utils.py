import re
from typing import List

GENERIC_TECHNICAL_TOKENS = {
    "base", "main", "core", "common", "utils", "util", "client", "server",
    "manager", "service", "run", "get", "set", "config", "configuration",
    "app", "application", "src", "lib", "libs"
}

def normalize_raw_path(p: str) -> str:
    """Normalize raw path input based on the strict requirements."""
    if not p:
        return ""
    p = p.strip()
    # Strip surrounding quotes and backticks
    p = re.sub(r"^['\"`]+|['\"`]+$", "", p)
    # Strip leading ./ or .\\ or / or \\
    p = re.sub(r"^(\.[/\\]+|[/\\]+)", "", p)
    # Replace Windows separator with Unix forward slash
    p = p.replace("\\", "/")
    # Deduplicate slashes
    p = re.sub(r"/+", "/", p)
    return p.strip()

def tokenize_string(s: str) -> List[str]:
    """Helper to split CamelCase, snake_case, kebab-case, dotted module names into tokens."""
    # Split on non-alphanumeric, underscores, hyphens, and dots
    parts = re.split(r'[^a-zA-Z0-9]+', s)
    tokens = []
    for p in parts:
        if not p:
            continue
        # Split CamelCase: e.g. MyClass -> My, Class
        camel_parts = re.findall(r'[a-zA-Z][a-z0-9]*', p)
        if camel_parts:
            tokens.extend([cp.lower() for cp in camel_parts])
        else:
            tokens.append(p.lower())
    return [t for t in tokens if len(t) >= 4]
