import pytest
from bs4 import BeautifulSoup

from find_parishes import find_candidate_urls


def test_find_candidate_urls():
    with open("tests/fixtures/sample.html") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    candidate_urls = find_candidate_urls(soup, "http://example.com")

    assert len(candidate_urls) == 3
    assert candidate_urls[0]["href"] == "http://example.com/parishes"
    assert candidate_urls[1]["href"] == "http://example.com/directory"
    assert candidate_urls[2]["href"] == "http://example.com/locations"
