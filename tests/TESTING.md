# Testing Guide

This document outlines the testing strategy for the data project, how to run existing tests, and how to add new ones.

## Testing Framework

We use [`pytest`](https://docs.pytest.org/) as our primary testing framework for its simplicity and powerful features. For mocking external dependencies like API calls and database interactions, we use the [`pytest-mock`](https://pytest-mock.readthedocs.io/) plugin.

## Running Tests

To run the entire test suite, navigate to the root directory of the project and execute the following command:

```bash
pytest
```

`pytest` will automatically discover and run all test files (named `test_*.py` or `*_test.py`) in the `tests/` directory and its subdirectories.

## Directory Structure

-   `tests/`: This directory contains all the test code for the project.
-   `tests/__init__.py`: This file marks the `tests/` directory as a Python package, which is good practice.
-   `tests/test_*.py`: Individual test files, each typically corresponding to a module in the main codebase (e.g., `tests/test_utils.py` tests the functions in `core/utils.py`).

## Writing New Tests

To add new tests, follow these steps:

1.  **Create a Test File:** If you are testing a new module (e.g., `new_module.py`), create a corresponding test file in the `tests/` directory named `test_new_module.py`.

2.  **Import Dependencies:** Import `pytest` and any modules or functions you need to test.

3.  **Write Test Functions:** Create functions whose names start with `test_`. Each function should test a specific piece of functionality. Use the `assert` keyword to check for expected outcomes.

### Example:

Here is an example of a simple test function in `tests/test_utils.py`:

```python
import pytest
from core.utils import normalize_url_join

def test_normalize_url_join():
    """
    Tests that the normalize_url_join function correctly joins URLs.
    """
    assert normalize_url_join("http://example.com", "/path") == "http://example.com/path"
    assert normalize_url_join("http://example.com/", "/path") == "http://example.com/path"
```

## Next Steps for Testing

The current test suite is just a starting point. Future improvements should include:

-   **Mocking External Services:** Writing tests for functions that interact with the Supabase database or external APIs by using `pytest-mock` to simulate responses.
-   **Testing Data Extraction Logic:** Creating tests for the parsing functions in `extract_dioceses.py` and `parish_extractors.py` to ensure they correctly handle different HTML structures.
-   **Integration Tests:** Developing tests for the main pipeline (`run_pipeline.py`) to ensure the different steps work together as expected.
