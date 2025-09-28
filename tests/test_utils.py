import pytest

from core.utils import normalize_url_join


@pytest.mark.parametrize(
    "base_url, relative_url, expected",
    [
        ("http://example.com", "/path", "http://example.com/path"),
        ("http://example.com/", "/path", "http://example.com/path"),
        ("http://example.com", "path", "http://example.com/path"),
        ("http://example.com/", "path", "http://example.com/path"),
    ],
)
def test_normalize_url_join(base_url, relative_url, expected):
    assert normalize_url_join(base_url, relative_url) == expected
