# Automated Testing with Pytest #

Automated tests have been created for [PyTest](https://docs.pytest.org/en/8.2.x/) using [Playwright](https://playwright.dev/).

To run the automated tests, use a Python virtual environment with the libraries from `requirements-text.txt`. *Note* that the
Search web application must be running independently while the tests are executed.

```shell
python -m venv testenv
pip install -r requirements-test.txt
playwright install
```
This will install Playwright and the PyTest plugins for Django and Playwright.

Tests are written using the PyTest format and are saved to the `tests` folder.
To run tests, activate the Test virtual environment and use the pytest command-line
utility to execute the entire test suite or individual test files.

```shell
 > pytest # run all tests
 > pytest test/test_opendata.py
```

The tests use Django's standard `settings.py` file to determine the URL to search pages.
To enable this, set the `DJANGO_SETTINGS_MODULE` value in the `pytest.ini` file located
in the project's base directory.





