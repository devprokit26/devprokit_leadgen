"""
email_finder.py - website se email aur owner/CEO ka naam nikalta hai
aur leads.xlsx ki rows mein bhar deta hai.

Kaise kaam karta hai (har website ke liye):
  1. Home page kholta hai
  2. Contact / Kontakt / Impressum / About / Team pages dhoondh kar (max 3) unhe kholta hai
  3. Email: mailto: links, page text, [at] jaisi chhupi hui emails, Cloudflare-protected emails
  4. Owner: JSON-LD data, ya "Geschaeftsfuehrer: Name", "Name, CEO" jaise patterns
  Naam na mile to khali chhorta hai (kabhi andaza nahi lagata).

Chalane ka tareeqa:
    python email_finder.py --file test_maps.xlsx            (sab pending leads)
    python email_finder.py --file test_maps.xlsx --limit 5  (sirf 5 par test)
    python email_finder.py --retry                          (jin par pehle 'not_found' aaya unhe dobara)
"""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, unquote

import httpx
from bs4 import BeautifulSoup

from excel_store import ExcelStore, COLUMNS, normalize_domain, format_lead

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "en,de;q=0.8",
}

# Kaun se links khole jayein (pehle wale ki priority zyada)
PAGE_KEYWORDS = [
    "impressum", "imprint", "kontakt", "contact", "legal-notice", "legal",
    "about", "uber-uns", "ueber-uns", "über-uns", "unternehmen", "company",
    "team", "management", "contacto", "contatto", "nosotros", "mentions-legales", "a-propos",
]

# ---------------------------------------------------------------- EMAIL
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
BAD_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js", ".woff", ".ico")
BAD_DOMAINS = {"example.com", "domain.com", "sentry.io", "wixpress.com", "email.com", "yoursite.com"}
BAD_LOCALS = {"user", "name", "email", "your", "you", "yourname", "john.doe", "max.mustermann"}

# Outreach ke liye behtar generic emails (pehla sab se behtar)
GENERIC_ORDER = ["purchasing", "procurement", "einkauf", "import", "buying", "info", "contact",
                 "kontakt", "office", "mail", "hello", "export", "sales", "vertrieb"]


def _decode_cf(hexstr):
    """Cloudflare 'email protection' ko wapas email banata hai."""
    key = int(hexstr[:2], 16)
    return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))


def _deobfuscate(text):
    text = re.sub(r"\s*[\[\(\{]\s*(?:at|AT|ät)\s*[\]\)\}]\s*", "@", text)
    text = re.sub(r"\s*[\[\(\{]\s*(?:dot|DOT|punkt)\s*[\]\)\}]\s*", ".", text)
    return text


def _emails_from_soup(soup):
    found = []
    for a in soup.select('a[href^="mailto:"]'):
        addr = unquote(a["href"][7:]).split("?")[0].strip()
        found.append(addr)
    for el in soup.select("[data-cfemail]"):
        try:
            found.append(_decode_cf(el["data-cfemail"]))
        except Exception:
            pass
    for a in soup.select('a[href*="/cdn-cgi/l/email-protection#"]'):
        try:
            found.append(_decode_cf(a["href"].split("#")[-1]))
        except Exception:
            pass
    found += EMAIL_RE.findall(_deobfuscate(soup.get_text(" ")))

    clean = []
    for e in found:
        e = e.strip().strip(".,;:<>()[]").lower()
        if not EMAIL_RE.fullmatch(e):
            continue
        local, domain = e.rsplit("@", 1)
        if e.endswith(BAD_EXT) or domain in BAD_DOMAINS or local in BAD_LOCALS:
            continue
        if "sentry" in local or "wixpress" in domain:
            continue
        clean.append(e)
    return clean


def _pick_email(emails, site_domain):
    """Sab emails mein se sab se munasib ek chunta hai."""
    best, best_score = "", -1
    for e in dict.fromkeys(emails):          # duplicates hatao, order rakho
        local, domain = e.rsplit("@", 1)
        score = 0
        if site_domain and (domain == site_domain or domain.endswith("." + site_domain)
                            or site_domain.endswith("." + domain)):
            score += 100                      # website ke apne domain ki email behtar
        base = local.split(".")[0].split("-")[0]
        if base in GENERIC_ORDER:
            score += 60 - GENERIC_ORDER.index(base)
        else:
            score += 30                       # kisi insaan ka naam wali email
        if score > best_score:
            best, best_score = e, score
    return best


# ---------------------------------------------------------------- OWNER NAME
_TITLE = (r"(?:Gesch[äa]ftsf[üu]hrer(?:in)?|Gesch[äa]ftsleiter(?:in)?|Inhaber(?:in)?|Gr[üu]nder(?:in)?|"
          r"Vorstand|Prokurist(?:in)?|Managing[ ]Director|General[ ]Manager|Chief[ ]Executive[ ]Officer|"
          r"CEO|Owner|Co-?Founder|Founder|Proprietor|President|Director)")
_NOT_WORD = r"(?![A-Za-zÄÖÜäöüß])"
_TOK = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüßéèáàíóúñç'\-]+"
_NAME = (r"(?:(?:Dr|Prof|Dipl|Mag)\.?(?:[\- ](?:Ing|med|rer|nat|jur|Kfm|oec)\.?)*[ ]+)*"
         + _TOK + r"(?:[ ]+(?:von|van|de|der|zu|zur|del|da))?(?:[ ]+" + _TOK + r"){1,2}")

PAT_TITLE_NAME = re.compile(
    r"((?i:" + _TITLE + r"))" + _NOT_WORD +
    r"(?::[ ]*\n?[ ]*|[\-–—,][ ]*|[ ]+)(?:(?:Herr|Frau|Mr|Mrs|Ms)\.?[ ]+)?(" + _NAME + r")")
PAT_NAME_TITLE = re.compile(
    r"(" + _NAME + r")[ ]*[,\-–—|/(][ ]*((?i:" + _TITLE + r"))" + _NOT_WORD)
PAT_TITLE_LINE = re.compile(r"(?i:" + _TITLE + r")")
PAT_NAME_FULL = re.compile(_NAME)

PREFIX_RE = re.compile(r"(?i)(dr|prof|dipl|mag|ing|med|rer|nat|jur|kfm|oec|herr|frau)\.?(-\w+)?")
NAME_BLACKLIST = {
    "gmbh", "co", "kg", "ag", "ug", "ltd", "llc", "inc", "mbh", "ek", "e.k.", "amtsgericht",
    "handelsregister", "registergericht", "hrb", "ust", "umsatzsteuer", "telefon", "tel", "fax",
    "email", "mail", "str", "straße", "strasse", "hamburg", "berlin", "germany", "deutschland",
    "impressum", "kontakt", "contact", "haftung", "verantwortlich", "vertreten", "anschrift",
    "adresse", "sitz", "steuernummer", "und", "oder", "the", "of", "and", "for", "des", "die",
    "das", "im", "in", "operations", "management", "sales", "marketing", "services", "service",
    "solutions", "group", "holding", "international", "trading", "export", "import", "safety",
    "gloves", "products", "company", "team", "board", "office", "finance", "quality",
    "logistics", "administration", "department", "manager", "gesellschaft", "unternehmen",
    "open", "hours", "web", "design", "datenschutz", "agb", "copyright", "all", "rights", "reserved",
}


def _valid_name(name):
    tokens = name.split()
    if not 2 <= len(tokens) <= 5:
        return False
    for t in tokens:
        if any(ch.isdigit() for ch in t) or t.lower().strip(".,-") in NAME_BLACKLIST:
            return False
    real = [t for t in tokens if not PREFIX_RE.fullmatch(t)]
    return len(real) >= 2


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _owner_from_jsonld(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        for node in _walk(data):
            for key, title in (("founder", "Founder"), ("founders", "Founder"), ("owner", "Owner")):
                val = node.get(key)
                for p in (val if isinstance(val, list) else [val]):
                    name = p.get("name") if isinstance(p, dict) else None
                    if isinstance(name, str) and _valid_name(name.strip()):
                        return name.strip(), title
            job = node.get("jobTitle")
            name = node.get("name")
            if (isinstance(job, str) and isinstance(name, str) and PAT_TITLE_LINE.search(job)
                    and _valid_name(name.strip())):
                return name.strip(), job.strip()
    return "", ""


def _owner_from_text(soup):
    lines = []
    for raw in soup.get_text("\n").splitlines():
        line = re.sub(r"[ \t\u00a0]+", " ", raw).strip()
        if line:
            lines.append(line)
    text = "\n".join(lines)

    for m in PAT_TITLE_NAME.finditer(text):               # "Geschäftsführer: Hans Meier"
        if _valid_name(m.group(2)):
            return m.group(2), m.group(1)
    for m in PAT_NAME_TITLE.finditer(text):               # "Hans Meier, CEO"
        if _valid_name(m.group(1)):
            return m.group(1), m.group(2)
    for i in range(len(lines)):                           # title alag line par ho
        if len(lines[i]) > 40 or not PAT_TITLE_LINE.fullmatch(lines[i].strip(" :,-")):
            continue
        title = lines[i].strip(" :,-")
        if i > 0 and PAT_NAME_FULL.fullmatch(lines[i - 1]) and _valid_name(lines[i - 1]):
            return lines[i - 1], title                    # "Hans Meier" (upar), "CEO" (neeche)
        if i + 1 < len(lines) and PAT_NAME_FULL.fullmatch(lines[i + 1]) and _valid_name(lines[i + 1]):
            return lines[i + 1], title                    # "CEO" (upar), "Hans Meier" (neeche)
    return "", ""


def _extract_owner(soup):
    name, title = _owner_from_jsonld(soup)
    return (name, title) if name else _owner_from_text(soup)


# ---------------------------------------------------------------- PAGES
def _get(client, url):
    try:
        r = client.get(url)
        if r.status_code >= 400 or "html" not in r.headers.get("content-type", "").lower():
            return None, None
        return r.text[:1_500_000], str(r.url)
    except Exception:
        return None, None


def _candidate_links(soup, base_url, limit=3):
    base_domain = normalize_domain(base_url)
    scored = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        url = urljoin(base_url, href).split("#")[0]
        if normalize_domain(url) != base_domain:
            continue
        hay = (href + " " + a.get_text(" ")).lower()
        for idx, kw in enumerate(PAGE_KEYWORDS):
            if kw in hay:
                if url not in scored or idx < scored[url]:
                    scored[url] = idx
                break
    ordered = sorted(scored, key=scored.get)
    return [u for u in ordered if u.rstrip("/") != base_url.rstrip("/")][:limit]



# ---------------------------------------------------------------- SOCIAL MEDIA
_SOCIAL_PATTERNS = {
    "facebook":  r"https?://(?:www\.|m\.|web\.)?facebook\.com/(?!sharer|share|plugins|tr\b|dialog|login|policy|help|groups/discover)[A-Za-z0-9_.\-/%]+",
    "instagram": r"https?://(?:www\.)?instagram\.com/(?!p/|reel/|explore|accounts|about|developer)[A-Za-z0-9_.]+",
    "linkedin":  r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in|school)/[A-Za-z0-9_.\-%]+",
    "twitter":   r"https?://(?:www\.)?(?:twitter|x)\.com/(?!share|intent|home|search|i/)[A-Za-z0-9_]{2,}",
    "youtube":   r"https?://(?:www\.)?youtube\.com/(?:@[A-Za-z0-9_.\-]+|channel/[A-Za-z0-9_\-]+|c/[A-Za-z0-9_\-]+|user/[A-Za-z0-9_\-]+)",
    "tiktok":    r"https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+",
}
SOCIAL_KEYS = list(_SOCIAL_PATTERNS)


def _socials_from_html(html):
    """Page ke HTML (links + JSON-LD sameAs) se social profile links. Wapas: dict."""
    found = {}
    if not html:
        return found
    html = html.replace("\\/", "/")
    for key, pat in _SOCIAL_PATTERNS.items():
        for m in re.finditer(pat, html, flags=re.I):
            url = m.group(0).rstrip("/.")
            url = re.sub(r"[?#].*$", "", url)
            if url.lower().rstrip("/").endswith(("facebook.com", "instagram.com", "linkedin.com")):
                continue
            found[key] = url
            break
    return found

def find_contacts(website):
    """Ek website se email + owner. Wapas: dict (khali string = nahi mila)."""
    result = {"email": "", "email_source": "not_found", "owner_name": "", "owner_title": ""}
    result.update({k: "" for k in SOCIAL_KEYS})
    result["social_status"] = "not_found"
    socials = {}
    url = website if "://" in website else "http://" + website

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=10, verify=False) as client:
        html, final = _get(client, url)
        if not html:
            return result
        site_domain = normalize_domain(final)
        soup = BeautifulSoup(html, "html.parser")
        emails = _emails_from_soup(soup)
        owner, title = _extract_owner(soup)
        socials.update(_socials_from_html(html))

        if not (emails and owner and len(socials) >= 2):
            for link in _candidate_links(soup, final):
                html2, _ = _get(client, link)
                if not html2:
                    continue
                soup2 = BeautifulSoup(html2, "html.parser")
                emails += _emails_from_soup(soup2)
                for k, v in _socials_from_html(html2).items():
                    socials.setdefault(k, v)
                if not owner:
                    owner, title = _extract_owner(soup2)
                if emails and owner and len(socials) >= 2:
                    break

    email = _pick_email(emails, site_domain)
    if email:
        result["email"] = email
        result["email_source"] = "website"
    result["owner_name"], result["owner_title"] = owner, title
    result.update(socials)
    result["social_status"] = "found" if socials else "not_found"
    return result


# ---------------------------------------------------------------- EXCEL KE SATH
def process_file(store, workers=5, limit=None, retry=False):
    col = {n: i for i, n in enumerate(COLUMNS)}
    todo = []
    for r in range(2, store.ws.max_row + 1):
        row = [c.value for c in store.ws[r]]
        if not row or row[0] is None:
            continue
        website, email, src = row[col["website"]], row[col["email"]], row[col["email_source"]]
        pending = (not src) or (retry and src == "not_found")
        social_pending = not row[col["social_status"]]
        if website and ((not email and pending) or social_pending):
            todo.append((int(row[col["id"]]), str(website), row[col["business_name"]], bool(email)))
    if limit:
        todo = todo[:limit]
    if not todo:
        print("Koi pending lead nahi mili (website wali + email khali).")
        return

    print(f"{len(todo)} websites check hongi ({workers} ek saath)...")
    got_email = got_owner = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(find_contacts, w): (lid, w, name, has_email) for lid, w, name, has_email in todo}
        for n, fut in enumerate(as_completed(futures), start=1):
            lid, w, name, has_email = futures[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {"email": "", "email_source": "not_found", "owner_name": "", "owner_title": "", "social_status": "not_found"}
                print(f"  error {w}: {str(e)[:60]}")
            if has_email:   # email pehle se hai: usay mat chhedo, sirf social bharo
                for k in ("email", "email_source", "owner_name", "owner_title"):
                    res.pop(k, None)
            res = {k: v for k, v in res.items() if v != "" or k in ("email_source", "social_status")}
            store.update_lead(lid, **res)
            got_email += bool(res.get("email"))
            got_owner += bool(res.get("owner_name"))
            full = dict(res); full["business_name"] = name; full["website"] = w
            print(f"  [{n}/{len(todo)}] " + format_lead(full))
    print(f"\nKhulasa: email mili={got_email}/{len(todo)}, owner naam mila={got_owner}/{len(todo)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Website se email + owner naam")
    ap.add_argument("--file", default=None, help="Excel file (default: config.EXCEL_FILE)")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--retry", action="store_true", help="'not_found' wali leads dobara try karo")
    args = ap.parse_args()
    process_file(ExcelStore(args.file), workers=args.workers, limit=args.limit, retry=args.retry)