import re
from pathlib import Path


def patch(fname, reps, marker):
    p = Path(fname)
    s = p.read_text(encoding="utf-8")
    if marker in s:
        print(fname + ": pehle se tez hai, kuch nahi badla")
        return
    for old, new in reps:
        if old not in s:
            print(fname + ": PATCH FAIL, ye hissa nahi mila:")
            print(old)
            return
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(fname + ": OK")


# ---- config.py
p = Path("config.py")
s = p.read_text(encoding="utf-8")
if "BLOCK_MEDIA" in s:
    print("config.py: pehle se tez hai, kuch nahi badla")
else:
    s2 = re.sub(r"^MIN_DELAY = 2\b", "MIN_DELAY = 1", s, flags=re.M)
    s2 = re.sub(r"^MAX_DELAY = 5\b", "MAX_DELAY = 2.5", s2, flags=re.M)
    if s2 == s:
        print("config.py: PATCH FAIL, MIN_DELAY/MAX_DELAY nahi mile")
    else:
        s2 = s2.rstrip("\n") + "\nBLOCK_MEDIA = True           # True = tasveerein/fonts load nahi hongi (tez). Masla aaye to False karo\n"
        p.write_text(s2, encoding="utf-8")
        print("config.py: OK")

# ---- maps_scraper.py
patch("maps_scraper.py", [
    ('    context = browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})\n    return browser, context\n',
     '    context = browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})\n'
     '    if getattr(config, "BLOCK_MEDIA", False):\n'
     '        context.route("**/*", lambda route: route.abort()\n'
     '                      if route.request.resource_type in ("image", "media", "font") else route.continue_())\n'
     '    return browser, context\n'),
    ("    page.wait_for_timeout(1200)\n", "    page.wait_for_timeout(600)\n"),
    ("page.wait_for_timeout(random.randint(1500, 2500))", "page.wait_for_timeout(random.randint(1000, 1800))"),
], "BLOCK_MEDIA")

# ---- main.py
patch("main.py", [
    ("time.sleep(random.uniform(5, 12))", "time.sleep(random.uniform(2, 5))"),
    ("timeout=10, verify=False)", "timeout=6, verify=False)"),
    ('ap.add_argument("--workers", type=int, default=5,', 'ap.add_argument("--workers", type=int, default=10,'),
], "random.uniform(2, 5)")
