from common.util import search_path
from playwright.sync_api import Page, expect
import re


def test_page_title(page: Page):
    page.goto(search_path('data', 'en'))
    expect(page).to_have_title("Open Government Portal")


def test_uuid_search_title_en(page: Page):
    page.goto(search_path('data', 'en'))
    tb = page.get_by_label("Search text")
    tb.fill('009f9a49-c2d9-4d29-a6d4-1a228da335ce')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    expect(count).to_have_text("one")



def test_uuid_search_title_fr(page: Page):
    page.goto(search_path('data', 'fr'))
    tb = page.get_by_label("Recherche")
    tb.fill('009f9a49-c2d9-4d29-a6d4-1a228da335ce')
    bt = page.get_by_label("Search button")
    bt.click()
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
