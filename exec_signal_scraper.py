import csv, json, io, re, requests, xml.etree.ElementTree as ET
from datetime import datetime

UA = "Dyfal Executive Signal Bot / 1.0 (Contact: support@dyfal.ai)"
EXEC_RE = re.compile(r'\b(CEO|CFO|COO|CTO|CMO|CIO|CPO|CHRO|President|Vice President|Head of|Director|General Manager)\b', re.I)

def parse_rss(xml_text: str, source: str):
    """
    Minimal RSS/Atom parser (no external deps).
    Handles Atom <entry> and RSS <item>, and Atom <link href="...">.
    """
    items = []
    root = ET.fromstring(xml_text)

    # Collect both Atom and RSS entries
    entries = list(root.findall(".//entry")) + list(root.findall(".//item"))
    for e in entries:
        # Title
        title = (e.findtext("title") or "").strip()

        # Link: try direct text first, then Atom-style href attr
        link = (e.findtext("link") or "").strip()
        if not link:
            # Atom: <link href="...">
            link_tag = e.find("link")
            if link_tag is not None and "href" in link_tag.attrib:
                link = link_tag.attrib["href"].strip()

        # Date
        posted = (e.findtext("updated") or e.findtext("pubDate") or "").strip()

        items.append({"title": title, "source": source, "url": link, "posted_at": posted})
    return items

def fetch_sec():
    """Fetch recent Form 8-K (Atom) and keep Item 5.02; never fail the whole run."""
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&count=100&output=atom"
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent": UA,
                "Accept-Encoding": "gzip, deflate",
                "Host": "www.sec.gov",
            },
            timeout=30,
        )
        r.raise_for_status()
        all_items = parse_rss(r.text, "SEC EDGAR 8-K 5.02")
        return [i for i in all_items if "Item 5.02" in (i["title"] or "")]
    except Exception as e:
        print("SEC fetch skipped:", e)
        return []

def fetch_news():
    """Leadership-change press signals via Google News RSS (public)."""
    url = (
        "https://news.google.com/rss/search?"
        "q=(appoints%20OR%20names%20OR%20hires%20OR%20search%20for)%20"
        "(CEO%20OR%20CFO%20OR%20COO%20OR%20CTO%20OR%20CMO)&hl=en-US&gl=US&ceid=US:en"
    )
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}, timeout=30)
    r.raise_for_status()
    all_items = parse_rss(r.text, "Google News")
    return [i for i in all_items if EXEC_RE.search(i["title"])]

def run_all():
    allrows = fetch_sec() + fetch_news()

    # Dedupe by URL (fallback to title if URL missing)
    seen, out = set(), []
    for r in allrows:
        key = r.get("url") or r.get("title")
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

if __name__ == "__main__":
    data = run_all()

    # Write CSV
    with open("executive_signals.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["title", "source", "url", "posted_at"])
        w.writeheader()
        w.writerows(data)

    # Write JSON
    with open("executive_signals.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote {len(data)} records → executive_signals.csv / executive_signals.json")
