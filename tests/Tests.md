# Automated Testing with Pytest #

Automated tests have been created for [PyTest](https://docs.pytest.org/en/8.2.x/) using [Playwright](https://playwright.dev/).

To run the automated tests, use a Python virtual environment with the libraries from `requirements-text.txt`. *Note* that the
Search web application must be running independently while the tests are executed.

Tests for custom searches should be placed in this directory using the naming convention
`text_<search ID>.py`. These tests will be included in the custom search import and export commands.
