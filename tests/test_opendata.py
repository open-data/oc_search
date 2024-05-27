from django.conf import settings
from playwright.sync_api import Page, expect
import re
from urllib import parse


def search_path(search: str, lang: str, path: str = "") -> str:
    return_url = ""
    if settings.SEARCH_LANG_USE_PATH:
        if lang == 'fr':
            return_url = f"{settings.SEARCH_FR_HOSTNAME}/rechercher/fr/{search}{path}"
        else:
            return_url = f"{settings.SEARCH_EN_HOSTNAME}/search/en/{search}{path}"
    else:
        if lang == 'fr':
            return_url = parse.urljoin(settings.SEARCH_FR_HOSTNAME, settings.SEARCH_HOST_PATH, f'/{search}{path}')
        else:
            return_url = parse.urljoin(settings.SEARCH_EN_HOSTNAME, settings.SEARCH_HOST_PATH, f'{search}{path}')
    return return_url


def test_page_title(page: Page):
    page.goto(search_path('data', 'en'))
    expect(page).to_have_title("Open Government Portal")


def test_uuid_search_title_en(page: Page):
    page.goto(search_path('data', 'en', path="?owner_org=tbs-sct&page=1&sort=metadata_modified+desc&search_text=009f9a49-c2d9-4d29-a6d4-1a228da335ce"))
    count = page.get_by_test_id("itemsfound")
    expect(count).to_have_text("one")


def test_uuid_search_title_fr(page: Page):
    page.goto(search_path('data', 'fr', path="?owner_org=tbs-sct&page=1&sort=metadata_modified+desc&search_text=009f9a49-c2d9-4d29-a6d4-1a228da335ce"))
    count = page.get_by_test_id("itemsfound")
    expect(count).to_have_text("un")


def test_submit_a_search(page: Page):
    page.goto(search_path('data', 'en'))
    tb = page.get_by_label("Search text")
    tb.fill('proactive disclosure travel expenses')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_nothing_found(page: Page):
    page.goto(search_path('data', 'en'))
    tb = page.get_by_label("Search text")
    tb.fill('zXcVbnmas')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    expect(count).to_contain_text("0")


def test_click_facet(page: Page):
    page.goto(search_path('data', 'en'))
    cb = page.get_by_label("facet-dataset_type-dataset")
    # Because of the way Search handles facets, need to use a clock event
    cb.dispatch_event('click')
    count = page.get_by_test_id("itemsfound")
    expect(count).to_contain_text(re.compile(r"[1-9][0-9]*"))
