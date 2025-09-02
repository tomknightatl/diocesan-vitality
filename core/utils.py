from urllib.parse import urljoin

def normalize_url_join(base_url, relative_url):
    """Properly joins URLs while avoiding double slashes."""
    if base_url.endswith("/") and relative_url.startswith("/"):
        base_url = base_url.rstrip("/")
    return urljoin(base_url, relative_url)
