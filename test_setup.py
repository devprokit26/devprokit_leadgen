import openpyxl, httpx, bs4, ddgs
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com")
    print("Browser OK, page title:", page.title())
    browser.close()

print("Sab libraries theek hain")
