from urllib.parse import urljoin, urlparse, urlunparse


def normalize_url_join(base_url, relative_url):
    """Properly joins URLs while avoiding double slashes."""
    if base_url.endswith("/") and relative_url.startswith("/"):
        base_url = base_url.rstrip("/")
    return urljoin(base_url, relative_url)


def normalize_url(url: str) -> str:
    """
    Normalizes a URL by:
    - Converting scheme to HTTPS.
    - Removing 'www.' subdomain if present.
    - Removing trailing slash.
    """
    parsed_url = urlparse(url)

    # Convert scheme to https
    scheme = "https"

    # Remove 'www.' from netloc
    netloc = parsed_url.netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Remove trailing slash from path
    path = parsed_url.path.rstrip("/")

    # Reconstruct the URL
    normalized_url = urlunparse((scheme, netloc, path, parsed_url.params, parsed_url.query, parsed_url.fragment))

    return normalized_url
