"""
web_search.py - 100% FREE lead source (koi proxy nahi, koi API key nahi, koi paid service nahi).

Kaise kaam karta hai:
  1. Search karta hai (pehle DuckDuckGo 'ddgs' library, phir DuckDuckGo Lite, aakhir mein Google text results).
     Sirf text results - tasveerein/JavaScript nahi, isliye data kam lagta hai aur block hone ka khatra kam.
  2. Directories / social / marketplace / news sites chhor deta hai, sirf asli company websites rakhta hai.
  3. Har company website se phone nikalta hai (tel: link, Impressum/Kontakt page).
  4. Relevance filter (accept) lagata hai, duplicate hatata hai, excel mein save karta hai.
  Email / owner / social links baad mein email_finder.py nikalta hai (main.py khud chalata hai).

Akele chalane ka tareeqa:
    python web_search.py "safety gloves supplier Hamburg" --max 30 --file test_web.xlsx
"""
import argparse
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote, parse_qs, quote_plus

import httpx
from bs4 import BeautifulSoup

import config
import email_finder
from excel_store import ExcelStore, format_lead

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# Ye sites asli business website nahi hoti (directory, social, marketplace, news) - inhe chhor do
SKIP_DOMAINS = (
    "google.", "bing.com", "duckduckgo.com", "yahoo.com", "facebook.com", "instagram.com", "linkedin.com",
    "twitter.com", "x.com", "youtube.com", "tiktok.com", "pinterest.", "reddit.com", "wikipedia.org",
    "amazon.", "ebay.", "alibaba.com", "aliexpress.com", "made-in-china.com", "indiamart.com",
    "etsy.com", "kleinanzeigen", "yelp.", "tripadvisor.", "trustpilot.com", "gelbeseiten.de",
    "dasoertliche.de", "11880.com", "northdata.", "firmenwissen.de", "wlw.de", "europages.",
    "kompass.com", "yellowpages.", "cylex.", "branchenbuch", "stylight.", "idealo.", "geizhals.",
    "medium.com", "quora.com", "github.com", "mapquest.com", "foursquare.com", "glassdoor.",
    "indeed.", "xing.com", "crunchbase.com", "zoominfo.com", "dnb.com", "bloomberg.com",
)
# Title mein ye ho to list/article hai, company nahi
LISTICLE_RE = re.compile(r"\b(top\s*\d+|best\s*\d+|\d+\s*best|list of|directory|verzeichnis|vergleich|"
                         r"ranking|bestenliste|testsieger|test\s*20\d\d)\b", re.I)

COUNTRY_REGION = {"germany": "de-de", "deutschland": "de-de", "austria": "at-de", "switzerland": "ch-de",
                  "france": "fr-fr", "italy": "it-it", "spain": "es-es", "netherlands": "nl-nl",
                  "uk": "uk-en", "united kingdom": "uk-en", "usa": "us-en", "united states": "us-en",
                  "uae": "xa-en", "dubai": "xa-en", "pakistan": "pk-en", "canada": "ca-en"}

PHONE_CTX_RE = re.compile(
    r"(?:tel(?:efon|ephone)?|phone|fon|mobil|mobile|call|rufen|hotline|t)\s*[.:]?\s*"
    r"(\+?\(?\d[\d\s()/.\\-]{6,20}\d)", re.I)


class SearchBlocked(Exception):
    """Search engine ne CAPTCHA / rate-limit diya."""


def _headers():
    return {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en,de;q=0.8"}


# ---------------------------------------------------------------- search backends (sab free)
def _search_ddgs(query, n, region):
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS      # purana naam
        except ImportError:
            return []
    try:
        rows = DDGS().text(query, region=region, max_results=n)
    except TypeError:
        rows = DDGS().text(query, max_results=n)
    return [(r.get("href") or r.get("url") or "", r.get("title") or "") for r in (rows or [])]


def _search_ddg_lite(query, n, region):
    r = httpx.post("https://lite.duckduckgo.com/lite/", data={"q": query, "kl": region},
                   headers=_headers(), timeout=15, follow_redirects=True)
    if r.status_code in (202, 403, 429) or "anomaly" in r.text.lower():
        raise SearchBlocked("DuckDuckGo Lite ne rok diya")
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for a in soup.select("a.result-link"):
        href = a.get("href", "")
        if "uddg=" in href:                                   # redirect link: asli URL andar hota hai
            href = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
        out.append((href, a.get_text(" ", strip=True)))
    return out[:n]


def _search_google(query, n, region):
    url = f"https://www.google.com/search?q={quote_plus(query)}&num={min(n, 50)}&hl=en"
    r = httpx.get(url, headers=_headers(), timeout=15, follow_redirects=True)
    if r.status_code != 200 or "/sorry/" in str(r.url) or "unusual traffic" in r.text:
        raise SearchBlocked("Google ne rok diya")
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for h3 in soup.find_all("h3"):
        a = h3.find_parent("a") or h3.find("a")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        if href.startswith("/url?"):
            href = parse_qs(urlparse(href).query).get("q", [""])[0]
        out.append((href, h3.get_text(" ", strip=True)))
    return out[:n]


def search(query, n=30, country=""):
    """Teeno free backends try karta hai. Wapas: ([(url, title), ...], blocked_hua_ya_nahi)."""
    region = COUNTRY_REGION.get(country.strip().lower(), "wt-wt")
    blocked = 0
    for backend in (_search_ddgs, _search_ddg_lite, _search_google):
        try:
            rows = [(u, t) for u, t in backend(query, n, region) if u.startswith("http")]
            if rows:
                return rows, False
        except SearchBlocked as e:
            blocked += 1
            print(f"  ({e})")
        except Exception as e:
            print(f"  ({backend.__name__} fail: {str(e)[:60]})")
    return [], blocked >= 2



# ---------------------------------------------------------------- galat mulk ki leads hatana
PHONE_CODES = {"pakistan": "92", "india": "91", "china": "86", "bangladesh": "880", "turkey": "90",
               "germany": "49", "united states": "1", "canada": "1", "united kingdom": "44",
               "france": "33", "italy": "39", "spain": "34", "netherlands": "31",
               "united arab emirates": "971", "australia": "61"}
TLDS = {"pakistan": ".pk", "india": ".in", "china": ".cn", "bangladesh": ".bd", "germany": ".de",
        "canada": ".ca", "united kingdom": ".uk", "france": ".fr", "italy": ".it", "spain": ".es",
        "netherlands": ".nl", "australia": ".au"}
OTHER_WORDS = {"pakistan": ["pakistan", "sialkot", "lahore", "karachi", "faisalabad"],
               "india": ["india", "jalandhar", "mumbai", "delhi"],
               "china": ["china", "shenzhen", "guangzhou", "made in china"],
               "bangladesh": ["bangladesh", "dhaka"]}


def wrong_country(data, country):
    """True agar lead ka phone / website / naam kisi aur mulk ka lagta hai."""
    c = (country or "").strip().lower()
    if not c:
        return False
    digits = re.sub(r"\D", "", str(data.get("phone") or "")).lstrip("0")
    if digits and c in PHONE_CODES:
        for other, code in PHONE_CODES.items():
            if other == c or code == PHONE_CODES[c]:
                continue
            if digits.startswith(code) and len(digits) >= 10 and (data.get("phone") or "").strip().startswith(("+", "00")):
                return True
    host = urlparse(data.get("website") or "").netloc.lower()
    for other, tld in TLDS.items():
        if other != c and (host.endswith(tld) or tld + "." in host) and tld not in (TLDS.get(c), ):
            return True
    text = ((data.get("business_name") or "") + " " + host).lower()
    for other, words in OTHER_WORDS.items():
        if other != c and any(w in text for w in words):
            return True
    return False


def _exclude_terms(country):
    c = (country or "").strip().lower()
    return " ".join("-" + w for w in ("Pakistan", "Sialkot", "India", "China") if w.lower() != c)

# ---------------------------------------------------------------- results ko companies mein badalna
def _root(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/"


def _good_site(url, title):
    host = urlparse(url).netloc.lower()
    if not host or any(s in host for s in SKIP_DOMAINS):
        return False
    return not LISTICLE_RE.search(title or "")


def _name_from_title(title, url):
    name = re.split(r"\s[-–—|:•·]\s", title or "")[0].strip()
    if len(name) < 3 or len(name) > 70:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        name = host.split(".")[0].replace("-", " ").title()
    return name


# ---------------------------------------------------------------- phone
def _valid_phone(raw):
    digits = re.sub(r"\D", "", raw)
    if not 8 <= len(digits) <= 15:
        return ""
    if re.fullmatch(r"(19|20)\d{2}[\s./\-]\d{1,2}[\s./\-]\d{1,2}", raw.strip()):   # tareekh
        return ""
    return re.sub(r"\s+", " ", raw).strip(" .-/")


def _phone_from_soup(soup):
    for a in soup.select('a[href^="tel:"]'):
        p = _valid_phone(unquote(a["href"][4:]))
        if p:
            return p
    text = soup.get_text(" ")
    for m in PHONE_CTX_RE.finditer(text):
        p = _valid_phone(m.group(1))
        if p:
            return p
    return ""


def fetch_business(client, url, title, country, city):
    """Ek company website se naam + phone. Sirf homepage — sub-pages skip (speed ke liye)."""
    root = _root(url)
    html, final = email_finder._get(client, root)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    phone = _phone_from_soup(soup)
    # Sub-page search hata di (speed 3x faster) — homepage se phone nahi mila to blank rahega
    return {"business_name": _name_from_title(title, url), "phone": phone, "website": root,
            "address": "", "rating": "", "country": country, "city": city}


# ---------------------------------------------------------------- poora kaam
def run(query, max_leads, store, country="", city="", headless=None, accept=None, workers=25):
    """
    max_leads = kitni leads SAVE karni hain (search results nahi).
    Jab tak target poora na ho, batch-by-batch search karta rahega.
    """
    stats = {"found": 0, "saved": 0, "duplicates": 0, "irrelevant": 0, "failed": 0,
             "limit_hit": False, "blocked": False}

    if store.remaining_today() <= 0:
        print(f"Aaj ki limit ({config.DAILY_LIMIT}) poori ho chuki hai. Kal dobara chalana.")
        stats["limit_hit"] = True
        return stats

    print(f"Search: {query}  |  Target: {max_leads} leads")

    # Har batch mein kitne raw results mangenge
    # (filtering ke baad actual leads kam hoti hain, isliye 4x se shuru karo)
    BATCH = max(max_leads * 4, 40)

    seen_roots = set()   # duplicate websites skip karne ke liye

    # ek baar search karo — DuckDuckGo mein offset nahi hota, isliye bade batch se kaam chalta hai
    results, blocked = search(
        (query + " " + _exclude_terms(country)).strip(), BATCH, country
    )
    stats["blocked"] = blocked
    if blocked:
        print("  Search engines ne rok diya. Kuch der (30-60 min) ruko, phir dobara chalao.")
        return stats

    stats["found"] = len(results)

    # sirf nayi company sites
    candidates = []
    for url, title in results:
        if not _good_site(url, title):
            continue
        root = _root(url)
        if root in seen_roots:
            continue
        seen_roots.add(root)
        if store.is_duplicate({"website": root}):
            stats["duplicates"] += 1
            continue
        candidates.append((url, title))

    print(f"  {len(results)} raw results mila, {len(candidates)} nayi company sites process hogi...")

    limits = httpx.Limits(max_connections=30, max_keepalive_connections=10)
    client = httpx.Client(headers=_headers(), follow_redirects=True,
                          timeout=5, verify=False, limits=limits)

    def work(item):
        url, title = item
        try:
            data = fetch_business(client, url, title, country, city)
            if data is None:
                return None, "failed"
            if wrong_country(data, country):
                return data, "wrong_country"
            if accept is not None and not accept(data):
                return data, "irrelevant"
            return data, "ok"
        except Exception:
            return None, "failed"

    try:
        # as_completed use karo taake jaise hi target poora ho, ruk jayen
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(work, item): item for item in candidates}
            processed = 0
            for future in as_completed(futures):
                if stats["saved"] >= max_leads:
                    # target poora — baaki futures cancel nahi hoti lekin save nahi karenge
                    break
                if store.remaining_today() <= 0:
                    print(f"  Aaj ki limit ({config.DAILY_LIMIT}) poori. Ruk gaye.")
                    stats["limit_hit"] = True
                    break

                data, status = future.result()
                processed += 1

                if status == "failed":
                    stats["failed"] += 1
                elif status in ("wrong_country", "irrelevant"):
                    stats["irrelevant"] += 1
                    print(f"  [{processed}] skip ({status}): {data.get('business_name','?')}")
                elif store.is_duplicate(data):
                    stats["duplicates"] += 1
                else:
                    store.add_lead(data)
                    store.add_usage(1)
                    stats["saved"] += 1
                    print(f"  [{stats['saved']}/{max_leads}] SAVED -> " + format_lead(data))

    finally:
        client.close()

    if stats["saved"] >= max_leads:
        print(f"\nTarget poora! {stats['saved']} leads save ho gayi.")
    else:
        print(f"\nSirf {stats['saved']} leads mili (target {max_leads} tha - search results kam the).")

    print(f"Khulasa: raw={stats['found']}, saved={stats['saved']}, duplicate={stats['duplicates']}, "
          f"skip={stats['irrelevant']}, fail={stats['failed']}")
    print(f"Aaj ka total: {store.today_count()} / {config.DAILY_LIMIT}")
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Free web-search lead scraper")
    ap.add_argument("query", help='jaise "safety gloves supplier Hamburg"')
    ap.add_argument("--max", type=int, default=20)
    ap.add_argument("--country", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--file", default=None, help="Excel file (default: config.EXCEL_FILE)")
    args = ap.parse_args()
    run(args.query, args.max, ExcelStore(args.file), country=args.country, city=args.city)