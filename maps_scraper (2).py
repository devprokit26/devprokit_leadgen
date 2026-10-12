"""
maps_scraper.py - Google Maps se business, phone, website, address, rating nikalta hai
aur excel_store ke zariye leads.xlsx mein save karta hai.

Chalane ka tareeqa (pehle chhota test, browser nazar aaye):
    python maps_scraper.py "glove importers Germany" --max 20 --show --file test_maps.xlsx

Asli chalane ka tareeqa:
    python maps_scraper.py "glove importers Germany" --max 100 --country Germany
"""
import argparse
import random
import time
from urllib.parse import quote

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import config
from excel_store import ExcelStore

BATCH_SIZE = 40          # itni places ke baad browser band karke dobara khulta hai (RAM bachane ke liye)


class Blocked(Exception):
    """Google ne CAPTCHA / 'unusual traffic' page dikha diya."""


# ---------------------------------------------------------------- helpers
def _pause(low=None, high=None):
    time.sleep(random.uniform(low or config.MIN_DELAY, high or config.MAX_DELAY))


def _launch(p, headless):
    browser = p.chromium.launch(headless=headless, proxy=config.PROXY)
    context = browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
    return browser, context


def _check_blocked(page):
    url = page.url
    if "google.com/sorry" in url:
        raise Blocked("Google ne CAPTCHA dikhaya (unusual traffic).")


def _accept_consent(page):
    """Cookie / consent page aaye to usay accept kar deta hai."""
    for label in ("Accept all", "Reject all", "I agree"):
        btn = page.get_by_role("button", name=label)
        if btn.count():
            try:
                btn.first.click(timeout=3000)
                page.wait_for_timeout(1500)
            except Exception:
                pass
            return


def _attr(page, selector, attr):
    loc = page.locator(selector)
    if loc.count():
        return loc.first.get_attribute(attr) or ""
    return ""


def _strip_label(text, label):
    """'Address: 12 Main St' -> '12 Main St'  (aksar aria-label ke shuru mein hota hai)"""
    text = (text or "").replace("\u00a0", " ").strip()
    if text.lower().startswith(label.lower()):
        text = text[len(label):].lstrip(": ").strip()
    return text


# ---------------------------------------------------------------- step A: results ki list
def collect_places(page, query, max_results):
    """Search kholta hai, list scroll karta hai, [(link, naam), ...] wapas deta hai."""
    url = "https://www.google.com/maps/search/" + quote(query) + "?hl=en"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    _accept_consent(page)
    _check_blocked(page)

    try:
        page.wait_for_selector('div[role="feed"]', timeout=20000)
    except PWTimeout:
        _check_blocked(page)
        page.screenshot(path="debug_maps.png")
        print("  Results ki list nahi mili. 'debug_maps.png' dekho (ya --show lagao).")
        return []

    places = {}          # link -> naam (dict, taake duplicate links na aayein)
    stagnant = 0
    while len(places) < max_results and stagnant < 4:
        found = page.eval_on_selector_all(
            'div[role="feed"] a[href*="/maps/place/"]',
            "els => els.map(e => [e.href, e.getAttribute('aria-label') || ''])",
        )
        before = len(places)
        for href, name in found:
            places.setdefault(href, name)
        stagnant = stagnant + 1 if len(places) == before else 0

        if page.get_by_text("You've reached the end of the list").count():
            break
        page.locator('div[role="feed"]').evaluate("el => el.scrollBy(0, el.scrollHeight)")
        page.wait_for_timeout(random.randint(1500, 2500))

    return list(places.items())[:max_results]


# ---------------------------------------------------------------- step B: ek place ki detail
def read_place(page, href, fallback_name=""):
    page.goto(href, wait_until="domcontentloaded", timeout=60000)
    _check_blocked(page)
    try:
        page.wait_for_selector("h1", timeout=15000)
    except PWTimeout:
        return None
    page.wait_for_timeout(1200)

    name = ""
    if page.locator("h1").count():
        name = page.locator("h1").first.inner_text().strip()
    name = name or fallback_name

    # phone: data-item-id="phone:tel:+4930123456"
    phone = ""
    item_id = _attr(page, 'button[data-item-id^="phone:tel:"]', "data-item-id")
    if item_id:
        phone = item_id.split("phone:tel:")[-1]
    else:
        phone = _strip_label(_attr(page, 'button[aria-label^="Phone:"]', "aria-label"), "Phone")

    website = _attr(page, 'a[data-item-id="authority"]', "href")
    address = _strip_label(_attr(page, 'button[data-item-id="address"]', "aria-label"), "Address")

    rating = ""
    r = page.locator('div.F7nice span[aria-hidden="true"]')
    if r.count():
        rating = r.first.inner_text().strip()

    return {
        "business_name": name,
        "phone": phone,
        "website": website,
        "address": address,
        "rating": rating,
    }


# ---------------------------------------------------------------- poora kaam
def run(query, max_results, store, country="", city="", headless=None, accept=None):
    """accept = optional function(data) -> True/False. False par lead save nahi hoti (relevance filter)."""
    headless = config.HEADLESS if headless is None else headless
    stats = {"found": 0, "saved": 0, "duplicates": 0, "irrelevant": 0, "failed": 0,
             "limit_hit": False, "blocked": False}

    if store.remaining_today() <= 0:
        print(f"Aaj ki limit ({config.DAILY_LIMIT}) poori ho chuki hai. Kal dobara chalana.")
        stats["limit_hit"] = True
        return stats

    with sync_playwright() as p:
        browser, context = _launch(p, headless)
        page = context.new_page()
        try:
            print(f"Search: {query}")
            places = collect_places(page, query, max_results)
            stats["found"] = len(places)
            print(f"  {len(places)} businesses mili. Ab har ek ki detail nikal rahe hain...")

            done = 0
            for i, (href, list_name) in enumerate(places, start=1):
                if store.remaining_today() <= 0:
                    print(f"  Aaj ki limit ({config.DAILY_LIMIT}) poori. Ruk gaye.")
                    stats["limit_hit"] = True
                    break

                # RAM bachane ke liye har BATCH_SIZE ke baad browser dobara
                if done and done % BATCH_SIZE == 0:
                    context.close()
                    browser.close()
                    browser, context = _launch(p, headless)
                    page = context.new_page()

                try:
                    data = read_place(page, href, list_name)
                except Blocked:
                    raise
                except Exception as e:
                    stats["failed"] += 1
                    print(f"  [{i}/{len(places)}] error: {str(e)[:80]}")
                    data = None
                done += 1

                if not data or not data["business_name"]:
                    stats["failed"] += 1
                else:
                    data["country"] = country
                    data["city"] = city
                    if not data["phone"] and not data["website"]:
                        stats["irrelevant"] += 1
                        print(f"  [{i}/{len(places)}] na phone na website, skip: {data['business_name']}")
                    elif store.is_duplicate(data):
                        stats["duplicates"] += 1
                        print(f"  [{i}/{len(places)}] duplicate, skip: {data['business_name']}")
                    elif accept is not None and not accept(data):
                        stats["irrelevant"] += 1
                        print(f"  [{i}/{len(places)}] relevant nahi, skip: {data['business_name']}")
                    else:
                        store.add_lead(data)
                        store.add_usage(1)
                        stats["saved"] += 1
                        print(f"  [{i}/{len(places)}] saved: {data['business_name']} | "
                              f"{data['phone'] or '-'} | {data['website'] or '-'}")
                _pause()
        except Blocked as e:
            stats["blocked"] = True
            print(f"\nRUK GAYE: {e}")
            print("Kuch der (kam az kam 30-60 minute) ruko, ya proxy lagao (config.py mein PROXY).")
        finally:
            context.close()
            browser.close()

    print(f"\nKhulasa: mili={stats['found']}, saved={stats['saved']}, "
          f"duplicate={stats['duplicates']}, relevant nahi={stats['irrelevant']}, fail={stats['failed']}")
    print(f"Aaj ka total: {store.today_count()} / {config.DAILY_LIMIT}")
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Google Maps scraper")
    ap.add_argument("query", help='jaise "glove importers Germany"')
    ap.add_argument("--max", type=int, default=20, help="kitni businesses (default 20)")
    ap.add_argument("--country", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--show", action="store_true", help="browser nazar aaye (testing ke liye)")
    ap.add_argument("--file", default=None, help="Excel file ka naam (default: config.EXCEL_FILE)")
    args = ap.parse_args()

    store = ExcelStore(args.file)
    run(args.query, args.max, store, country=args.country, city=args.city,
        headless=not args.show)
