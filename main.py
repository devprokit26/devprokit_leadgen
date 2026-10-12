"""
main.py - poora pipeline ek command mein.

  1. searches.txt se keywords x shehar ke saare combinations banata hai
  2. Har search free web search se chalata hai (web_search.py - koi proxy/API key nahi).
     Chaho to --source maps se purana Google Maps scraper bhi chal sakta hai.
  3. Sirf gloves se related businesses rakhta hai (relevance filter)
  4. Aakhir mein sab leads ki email + owner naam nikalta hai (email_finder)
  5. Roz ki limit (config.DAILY_LIMIT) par ruk jata hai. Kal dobara chalane par wahin se aage barhta hai.

Chalane ka tareeqa:
    python main.py --dry-run                 (sirf dikhata hai kaun si searches hongi)
    python main.py --file test_run.xlsx --max-per-search 15 --show     (chhota test)
    python main.py                           (asli run, leads.xlsx mein)
"""
import argparse
import random
import re
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

import config
import email_finder
from excel_store import ExcelStore, format_lead


# ---------------------------------------------------------------- searches.txt
def _read_text(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def load_searches(path):
    keywords, places, words, exclude = [], [], [], []
    section = None
    for raw in _read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip().lower()
            continue
        if section == "keywords":
            keywords.append(line)
        elif section == "places":
            places.append(line)
        elif section == "relevant_words":
            words.append(line.lower())
        elif section == "exclude_words":
            exclude.append(line.lower())
    return keywords, places, words, exclude


def build_queries(keywords, places):
    """Har shehar ke liye saare keywords (taake limit par bhi har shehar cover ho)."""
    queries = []
    for place in places:
        city, _, country = place.partition(",")
        for kw in keywords:
            queries.append((f"{kw} {place}", city.strip(), country.strip()))
    return queries


# ---------------------------------------------------------------- relevance filter
def make_relevance_checker(words, exclude=()):
    """
    Lead tab relevant maani jaati hai jab:
      - naam ya website ke address mein koi relevant lafz ho, YA
      - uski website ke home page ke text mein koi relevant lafz ho.
    Chhote lafz (4 harf ya kam, jaise 'ppe') poora lafz hone chahiye; baqi substring match hote hain
    (taake 'Arbeitshandschuhe' mein 'handschuh' mil jaye).
    """
    short = [re.compile(r"\b" + re.escape(w) + r"\b", re.I) for w in words if len(w) <= 4]
    long_ = [w for w in words if len(w) > 4]
    client = httpx.Client(headers=email_finder.HEADERS, follow_redirects=True,
                          timeout=6, verify=False)

    def has_words(text):
        low = (text or "").lower()
        return any(w in low for w in long_) or any(r.search(text or "") for r in short)

    def has_excluded(text):
        low = (text or "").lower()
        return any(w in low for w in exclude)

    def accept(data):
        # Naam ya website ke address mein exclude lafz ho (golf, sport, baumarkt...) to seedha reject
        if has_excluded(data.get("business_name")) or has_excluded(data.get("website")):
            return False
        if has_words(data.get("business_name")) or has_words(data.get("website")):
            return True
        site = data.get("website")
        if not site:
            return False
        html, _ = email_finder._get(client, site if "://" in site else "http://" + site)
        if not html:
            return False
        soup = BeautifulSoup(html, "html.parser")
        meta = " ".join(m.get("content", "") for m in soup.find_all("meta")
                        if m.get("name", "").lower() in ("description", "keywords"))
        title = soup.title.get_text(" ") if soup.title else ""
        if has_excluded(title + " " + meta):          # sirf title/meta, body nahi (body mein sab kuch hota hai)
            return False
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return has_words(soup.get_text(" ") + " " + meta)

    return accept


# ---------------------------------------------------------------- done list (kal wahin se aage)
def _done_path(excel_file):
    return Path(excel_file).with_name(Path(excel_file).stem + "_done.txt")


def load_done(excel_file):
    p = _done_path(excel_file)
    return set(p.read_text(encoding="utf-8").splitlines()) if p.exists() else set()


def mark_done(excel_file, query):
    with open(_done_path(excel_file), "a", encoding="utf-8") as f:
        f.write(query + "\n")


# ---------------------------------------------------------------- pipeline
def print_report(store):
    """Aaj ki SAARI leads ki poori maloomat screen par."""
    rows = store.leads_added_today()
    print(f"\n================ AAJ KI SAARI LEADS ({len(rows)}) ================")
    for i, d in enumerate(rows, start=1):
        print(f"{i:>3}. " + format_lead(d))


def run_pipeline(args):
    keywords, places, words, exclude = load_searches(args.searches)
    if not keywords or not places:
        print(f"'{args.searches}' mein [keywords] aur [places] dono sections chahiye.")
        return
    queries = build_queries(keywords, places)
    excel_file = args.file or config.EXCEL_FILE

    if args.dry_run:
        print(f"{len(queries)} searches banengi:")
        for q, _, _ in queries:
            print("  -", q)
        print(f"\nRelevant lafz ({len(words)}):", ", ".join(words) or "(koi nahi, filter band)")
        print(f"Exclude lafz ({len(exclude)}):", ", ".join(exclude) or "(koi nahi)")
        return

    store = ExcelStore(excel_file)
    done = load_done(excel_file)
    accept = make_relevance_checker(words, exclude) if words else None

    source = args.source or config.SOURCE
    if source == "maps":
        import maps_scraper as scraper
    else:
        import web_search as scraper
    print(f"Source: {source} (100% free)")

    pending = [q for q in queries if q[0] not in done]
    print(f"Searches: kul {len(queries)}, pehle se ho chuki {len(queries) - len(pending)}, "
          f"baqi {len(pending)}")
    print(f"Aaj ki limit: {store.today_count()} / {config.DAILY_LIMIT} istemal ho chuki\n")

    totals = {"saved": 0, "duplicates": 0, "irrelevant": 0}
    for n, (query, city, country) in enumerate(pending, start=1):
        if store.remaining_today() <= 0:
            print("Aaj ki limit poori. Kal dobara chalana, wahin se aage barhega.")
            break
        print(f"=== Search {n}/{len(pending)} ===")
        stats = scraper.run(query, args.max_per_search, store, country=country, city=city,
                                 headless=not args.show, accept=accept)
        for k in totals:
            totals[k] += stats[k]
        if stats["blocked"]:
            print("Search engine ne block kiya, aaj ke liye searches band.")
            break
        if not stats["limit_hit"] and stats["found"] > 0:
            mark_done(excel_file, query)
        # Insani rafter: bina proxy ke IP ko bachane ke liye searches ke beech aaram
        time.sleep(random.uniform(config.SEARCH_MIN_DELAY, config.SEARCH_MAX_DELAY))

    if not args.no_email:
        print("\n=== Email aur owner naam ===")
        email_finder.process_file(store, workers=args.workers)

    if not args.no_report:
        print_report(store)

    print("\n================ AAKHRI KHULASA ================")
    print(f"Nayi leads saved : {totals['saved']}")
    print(f"Duplicate        : {totals['duplicates']}")
    print(f"Relevant nahi    : {totals['irrelevant']}")
    print(f"Aaj ka total     : {store.today_count()} / {config.DAILY_LIMIT}")
    print(f"File             : {excel_file}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gloves lead-gen pipeline")
    ap.add_argument("--searches", default="searches.txt")
    ap.add_argument("--file", default=None, help="Excel file (default: config.EXCEL_FILE)")
    ap.add_argument("--max-per-search", type=int, default=60)
    ap.add_argument("--workers", type=int, default=10, help="email dhoondne ke liye ek saath websites")
    ap.add_argument("--source", choices=["web", "maps"], default=None,
                    help="web = free search (default), maps = Google Maps browser")
    ap.add_argument("--no-report", action="store_true", help="aakhir mein saari leads ki list na dikhao")
    ap.add_argument("--show", action="store_true", help="(maps ke liye) browser nazar aaye")
    ap.add_argument("--no-email", action="store_true", help="email/owner step chhor do")
    ap.add_argument("--dry-run", action="store_true", help="sirf searches dikhao, chalao mat")
    run_pipeline(ap.parse_args())
