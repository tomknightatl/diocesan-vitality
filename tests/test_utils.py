import pytest
from core.utils import normalize_url_join

def test_normalize_url_join():
    assert normalize_url_join("http://example.com", "/path") == "http://example.com/path"
    assert normalize_url_join("http://example.com/", "/path") == "http://example.com/path"
    assert normalize_url_join("http://example.com", "path") == "http://example.com/path"
    assert normalize_url_join("http://example.com/", "path") == "http://example.com/path"
    assert normalize_url_join("http://example.com/folder/", "../path") == "http://example.com/path"
