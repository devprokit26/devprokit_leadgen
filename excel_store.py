"""
excel_store.py - leads ko Excel (leads.xlsx) mein save karta hai.

Ye file 3 kaam karti hai:
  1. leads.xlsx banati hai (agar pehle se nahi hai)
  2. duplicate check (website ya phone se) - wohi business dobara save nahi hota
  3. roz kitni leads hui, uska count (daily limit ke liye)
"""
import os
import re
from datetime import date
from urllib.parse import urlparse

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

import config

LEADS_SHEET = "Leads"
USAGE_SHEET = "Usage"

COLUMNS = [
    "id", "business_name", "phone", "website", "address", "city", "country",
    "rating", "email", "owner_name", "owner_title", "email_source",
    "ai_message", "status", "date_added",
    "facebook", "instagram", "linkedin", "twitter", "youtube", "tiktok", "social_status",
]


def normalize_domain(url):
    """'https://www.ABC.com/contact' -> 'abc.com'"""
    if not url:
        return ""
    url = str(url).strip().lower()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    host = urlparse(url).netloc
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_phone(phone):
    """'+49 (30) 1234-5678' -> '301234567' (aakhri 9 digits, country code ignore)"""
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) < 7:
        return ""
    return digits[-9:]


def format_lead(d):
    """Lead ki saari maloomat ek line mein (screen par dikhane ke liye)."""
    d = {k: (v if v not in (None, "") else "-") for k, v in d.items()}
    parts = [d.get("business_name", "-")]
    if d.get("phone", "-") != "-":
        parts.append("Tel: " + str(d["phone"]))
    if d.get("website", "-") != "-":
        parts.append("Web: " + str(d["website"]))
    parts.append("Email: " + str(d.get("email", "-")))
    if d.get("owner_name", "-") != "-":
        parts.append("Owner: %s (%s)" % (d["owner_name"], d.get("owner_title", "-")))
    for k in ("facebook", "instagram", "linkedin", "twitter", "youtube", "tiktok"):
        if d.get(k, "-") != "-":
            parts.append("%s: %s" % (k.capitalize(), d[k]))
    return " | ".join(parts)


class ExcelStore:
    def __init__(self, path=None):
        self.path = path or config.EXCEL_FILE
        self._create_if_missing()
        self.wb = load_workbook(self.path)
        self.ws = self.wb[LEADS_SHEET]
        self.usage = self.wb[USAGE_SHEET]
        self._add_missing_headers()
        self.domains = set()
        self.phones = set()
        self.row_of = {}          # id -> excel row number
        self.next_id = 1
        self._load_index()

    # ---------- file setup ----------
    def _add_missing_headers(self):
        """Purani file mein naye (social) columns ke headers na hon to laga deta hai."""
        for i, name in enumerate(COLUMNS, start=1):
            if self.ws.cell(row=1, column=i).value is None:
                self.ws.cell(row=1, column=i, value=name)

    def _create_if_missing(self):
        if os.path.exists(self.path):
            return
        wb = Workbook()
        ws = wb.active
        ws.title = LEADS_SHEET
        ws.append(COLUMNS)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        ws.freeze_panes = "A2"
        widths = {"business_name": 30, "phone": 18, "website": 30, "address": 35,
                  "email": 28, "owner_name": 22, "ai_message": 50}
        for i, col in enumerate(COLUMNS, start=1):
            letter = ws.cell(row=1, column=i).column_letter
            ws.column_dimensions[letter].width = widths.get(col, 14)
        us = wb.create_sheet(USAGE_SHEET)
        us.append(["date", "count"])
        for cell in us[1]:
            cell.font = Font(bold=True)
        wb.save(self.path)

    def _load_index(self):
        """Purani rows se duplicate-check wali list aur next id tayyar karta hai."""
        col = {name: i for i, name in enumerate(COLUMNS)}
        for r in range(2, self.ws.max_row + 1):
            row = [c.value for c in self.ws[r]]
            if not row or row[0] is None:
                continue
            lead_id = int(row[col["id"]])
            self.row_of[lead_id] = r
            self.next_id = max(self.next_id, lead_id + 1)
            d = normalize_domain(row[col["website"]])
            p = normalize_phone(row[col["phone"]])
            if d:
                self.domains.add(d)
            if p:
                self.phones.add(p)

    def save(self):
        """Save karta hai. Agar Excel mein file khuli ho to band karne ko kehta hai."""
        while True:
            try:
                self.wb.save(self.path)
                return
            except PermissionError:
                input(f"'{self.path}' Excel mein khuli hai. Usay band karo, phir Enter dabao...")

    # ---------- duplicate check ----------
    def is_duplicate(self, lead):
        d = normalize_domain(lead.get("website"))
        p = normalize_phone(lead.get("phone"))
        return (bool(d) and d in self.domains) or (bool(p) and p in self.phones)

    # ---------- leads ----------
    def add_lead(self, lead):
        """
        lead = dict, jaise {"business_name": "...", "phone": "...", "website": "..."}
        Naya ho to save karke id wapas deta hai, duplicate ho to None.
        """
        if self.is_duplicate(lead):
            return None
        lead = dict(lead)
        lead["id"] = self.next_id
        lead.setdefault("status", "new")
        lead.setdefault("date_added", date.today().isoformat())
        self.ws.append([lead.get(c, "") for c in COLUMNS])
        self.row_of[self.next_id] = self.ws.max_row
        d = normalize_domain(lead.get("website"))
        p = normalize_phone(lead.get("phone"))
        if d:
            self.domains.add(d)
        if p:
            self.phones.add(p)
        self.next_id += 1
        self.save()
        return lead["id"]

    def update_lead(self, lead_id, **fields):
        """Maujood lead mein columns bharna, jaise update_lead(5, email="a@b.com")."""
        row = self.row_of[lead_id]
        for name, value in fields.items():
            if name in COLUMNS:
                self.ws.cell(row=row, column=COLUMNS.index(name) + 1, value=value)
        self.save()

    def leads_added_today(self):
        """Aaj ki saari leads (dict ki list) - poori maloomat ke sath."""
        today = date.today().isoformat()
        out = []
        for r in range(2, self.ws.max_row + 1):
            row = [c.value for c in self.ws[r]]
            if not row or row[0] is None:
                continue
            d = dict(zip(COLUMNS, row))
            if str(d.get("date_added")) == today:
                out.append(d)
        return out

    # ---------- daily limit ----------
    def _usage_row(self):
        today = date.today().isoformat()
        for r in range(2, self.usage.max_row + 1):
            if str(self.usage.cell(row=r, column=1).value) == today:
                return r
        self.usage.append([today, 0])
        return self.usage.max_row

    def today_count(self):
        return int(self.usage.cell(row=self._usage_row(), column=2).value or 0)

    def remaining_today(self):
        return max(0, config.DAILY_LIMIT - self.today_count())

    def add_usage(self, n=1):
        r = self._usage_row()
        current = int(self.usage.cell(row=r, column=2).value or 0)
        self.usage.cell(row=r, column=2, value=current + n)
        self.save()


# ---------- chhota self-test ----------
if __name__ == "__main__":
    test_file = "test_leads.xlsx"
    if os.path.exists(test_file):
        os.remove(test_file)
    store = ExcelStore(test_file)

    a = store.add_lead({"business_name": "ABC Gloves", "phone": "+49 30 1234567",
                        "website": "https://www.abcgloves.com/contact", "country": "Germany"})
    b = store.add_lead({"business_name": "ABC Gloves (dobara)", "phone": "0049301234567",
                        "website": "abcgloves.com"})
    c = store.add_lead({"business_name": "XYZ Safety", "phone": "+44 20 7946 0958",
                        "website": "xyzsafety.co.uk", "country": "UK"})
    store.update_lead(c, email="info@xyzsafety.co.uk", email_source="website")
    store.add_usage(2)

    print("Lead A id:", a)
    print("Lead B (duplicate, None aana chahiye):", b)
    print("Lead C id:", c)
    print("Aaj ka count:", store.today_count(), "| Baqi:", store.remaining_today())

    # file se dobara kholke check
    again = ExcelStore(test_file)
    print("Dobara kholne par duplicate pakda gaya?",
          again.is_duplicate({"website": "www.abcgloves.com"}))
    os.remove(test_file)
    print("Self-test theek hai")