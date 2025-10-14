import requests, csv, json, io, re, xml.etree.ElementTree as ET
from datetime import datetime

EXEC_RE = re.compile(r'\b(CEO|CFO|COO|CTO|CMO|CIO|CPO|CHRO|President|Vice President|Head of|Director|General Manager)\b', re.I)

def parse_rss(xml_text, source):
    root = ET.fromstring(xml_text)
    items = []
    for entry in root.findall(".//entry") + root.findall(".//item"):
        title = (entry.findtext("title") or "").strip()
        link  = (entry.findtext("link") or "").strip()
        pub   = (entry.findtext("updated") or entry.findtext("pubDate") or "").strip()
        items.append({"title": title, "source": source, "url": link, "posted_at": pub})
    return items

def fetch_sec():
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&count=100&output=atom"
    r = requests.get(url, headers={"User-Agent":"DYFAL-Exec-Signal"}, timeout=30)
    r.raise_for_status()
    all_items = parse_rss(r.text, "SEC EDGAR 8-K 5.02")
    return [i for i in all_items if "Item 5.02" in (i["title"] or "")]

def fetch_news():
    url = "https://news.google.com/rss/search?q=(appoints%20OR%20names%20OR%20hires%20OR%20search%20for)%20(CEO%20OR%20CFO%20OR%20COO%20OR%20CTO%20OR%20CMO)&hl=en-US&gl=US&ceid=US:en"
    r = requests.get(url, headers={"User-Agent":"DYFAL-Exec-Signal"}, timeout=30)
    r.raise_for_status()
    all_items = parse_rss(r.text, "Google News")
    return [i for i in all_items if EXEC_RE.search(i["title"])]

def run_all():
    allrows = fetch_sec() + fetch_news()
    seen, out = set(), []
    for r in allrows:
        key = (r["url"] or r["title"])
        if key in seen: continue
        seen.add(key); out.append(r)
    return out

if __name__ == "__main__":
    data = run_all()
    with open("executive_signals.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["title","source","url","posted_at"])
        w.writeheader(); w.writerows(data)
    with open("executive_signals.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {len(data)} records → executive_signals.csv / .json")
