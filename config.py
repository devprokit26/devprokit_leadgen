"""
config.py - saari settings ek jagah.
100% FREE version: koi API key nahi, koi proxy nahi, koi paid service nahi.
"""

# ---- Limits ----
DAILY_LIMIT = 500            # roz maximum itni nayi leads (potential buyers)

# ---- Files ----
EXCEL_FILE = "leads.xlsx"    # data yahan save hoga (leadgen folder ke andar)

# ---- Source ----
# "web"  = free web search (DuckDuckGo, Google text fallback) -> tez, block hone ka khatra kam. (Default)
# "maps" = Google Maps browser scraper -> zyada block hota hai, proxy ke baghair 500/din mushkil.
SOURCE = "web"

# ---- Scraping settings ----
HEADLESS = True              # (sirf maps ke liye) True = browser nazar nahi aayega
MIN_DELAY = 1                # requests ke beech kam az kam itne second ruko
MAX_DELAY = 2.5              # aur zyada se zyada itne second
BLOCK_MEDIA = True           # (sirf maps ke liye) tasveerein/fonts load nahi hongi (tez)

# Web search ke liye insani rafter (Google/DDG ko bot na lage, bina proxy ke)
SEARCH_MIN_DELAY = 3         # do searches ke beech kam az kam itne second
SEARCH_MAX_DELAY = 7         # aur zyada se zyada itne second

# ---- Web UI login (app.py) ----
APP_USERNAME = "admin"       # login username - apni marzi se badlo
APP_PASSWORD = "admin123"    # login password - zaroor badlo
APP_SECRET = "change-this-secret-key"
