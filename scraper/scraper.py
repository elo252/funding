"""
Funding Opportunity Scraper
Scrapes NIH, NSF, Grants.gov, fellowships, and private foundations.
Saves results to data/funding.json
"""

import json
import os
import time
import hashlib
import requests
import feedparser
from datetime import datetime, timezone
from bs4 import BeautifulSoup

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "funding.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; FundingBot/1.0; +https://github.com)"
    )
}

KEYWORDS = [
    "artificial intelligence", "machine learning", "deep learning",
    "biomedical", "bioinformatics", "computational biology",
    "genomics", "medical imaging", "natural language processing",
    "neural network", "AI", "PhD", "graduate", "fellowship",
    "data science", "health informatics"
]

def slugify(text):
    return hashlib.md5(text.encode()).hexdigest()[:10]

def keyword_score(text):
    text_lower = text.lower()
    return sum(1 for kw in KEYWORDS if kw.lower() in text_lower)

def clean(text):
    if not text:
        return ""
    return " ".join(text.split()).strip()

# ─────────────────────────────────────────────
# 1. NIH Grants (Reporter API - Funding Opportunity Announcements)
# ─────────────────────────────────────────────
def scrape_nih():
    print("→ NIH Reporter...")
    results = []
    try:
        url = "https://reporter.nih.gov/services/prj/Publications"
        # Use NIH Guide RSS for FOAs instead
        feed_url = "https://grants.nih.gov/funding/searchGuide/rss/rss.cfm"
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:60]:
            title = clean(entry.get("title", ""))
            link = entry.get("link", "")
            summary = clean(entry.get("summary", ""))
            pub_date = entry.get("published", "")
            score = keyword_score(title + " " + summary)
            results.append({
                "id": slugify(link or title),
                "title": title,
                "source": "NIH Guide",
                "type": "Federal Grant",
                "url": link,
                "description": summary[:400],
                "deadline": None,
                "amount": None,
                "posted": pub_date,
                "relevance_score": score,
                "tags": ["NIH", "Federal", "Biomedical"],
            })
        print(f"   NIH: {len(results)} items")
    except Exception as e:
        print(f"   NIH error: {e}")
    return results


# ─────────────────────────────────────────────
# 2. NSF Funding Opportunities
# ─────────────────────────────────────────────
def scrape_nsf():
    print("→ NSF...")
    results = []
    try:
        url = "https://www.nsf.gov/funding/pgm_list.jsp?type=new&listtype=date"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.select("table.prgmListTbl tr")[1:]
        for row in rows[:50]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            title_tag = cols[0].find("a")
            title = clean(title_tag.text) if title_tag else ""
            link = "https://www.nsf.gov" + title_tag["href"] if title_tag and title_tag.get("href") else ""
            deadline = clean(cols[1].text) if len(cols) > 1 else None
            posted = clean(cols[2].text) if len(cols) > 2 else None
            score = keyword_score(title)
            results.append({
                "id": slugify(link or title),
                "title": title,
                "source": "NSF",
                "type": "Federal Grant",
                "url": link,
                "description": "",
                "deadline": deadline,
                "amount": None,
                "posted": posted,
                "relevance_score": score,
                "tags": ["NSF", "Federal", "STEM"],
            })
        print(f"   NSF: {len(results)} items")
    except Exception as e:
        print(f"   NSF error: {e}")
    return results


# ─────────────────────────────────────────────
# 3. Grants.gov RSS
# ─────────────────────────────────────────────
def scrape_grantsgov():
    print("→ Grants.gov...")
    results = []
    try:
        # Grants.gov search RSS for AI + Biomedical
        feeds = [
            "https://www.grants.gov/rss/GG_NewOpps.xml",
            "https://www.grants.gov/rss/GG_OppCloseDate7Days.xml",
        ]
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:40]:
                title = clean(entry.get("title", ""))
                link = entry.get("link", "")
                summary = clean(entry.get("summary", ""))
                pub_date = entry.get("published", "")
                score = keyword_score(title + " " + summary)
                results.append({
                    "id": slugify(link or title),
                    "title": title,
                    "source": "Grants.gov",
                    "type": "Federal Grant",
                    "url": link,
                    "description": summary[:400],
                    "deadline": None,
                    "amount": None,
                    "posted": pub_date,
                    "relevance_score": score,
                    "tags": ["Federal", "Grants.gov"],
                })
        print(f"   Grants.gov: {len(results)} items")
    except Exception as e:
        print(f"   Grants.gov error: {e}")
    return results


# ─────────────────────────────────────────────
# 4. NSF Graduate Research Fellowship (GRFP)
# ─────────────────────────────────────────────
def scrape_nsf_grfp():
    print("→ NSF GRFP...")
    results = []
    try:
        url = "https://www.nsfgrfp.org/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text()
        # Build a static entry since GRFP is a known annual fellowship
        results.append({
            "id": slugify("nsf-grfp-2024"),
            "title": "NSF Graduate Research Fellowship Program (GRFP)",
            "source": "NSF GRFP",
            "type": "Fellowship",
            "url": "https://www.nsfgrfp.org/",
            "description": (
                "The NSF GRFP recognizes and supports outstanding graduate students "
                "in NSF-supported STEM disciplines. Fellows receive a 3-year annual "
                "stipend of $37,000 along with a $16,000 cost of education allowance."
            ),
            "deadline": "October (annually)",
            "amount": "$37,000/year stipend + $16,000 education allowance",
            "posted": None,
            "relevance_score": 8,
            "tags": ["NSF", "Fellowship", "Graduate", "STEM", "AI", "Biomedical"],
        })
        print(f"   GRFP: 1 item")
    except Exception as e:
        print(f"   GRFP error: {e}")
    return results


# ─────────────────────────────────────────────
# 5. Hertz Fellowship
# ─────────────────────────────────────────────
def scrape_hertz():
    print("→ Hertz Fellowship...")
    results = []
    try:
        url = "https://www.hertzfoundation.org/the-fellowship/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        desc_tag = soup.find("div", class_=lambda c: c and "content" in c.lower())
        desc = clean(desc_tag.get_text()) if desc_tag else ""
        results.append({
            "id": slugify("hertz-fellowship"),
            "title": "Hertz Graduate Fellowship Award",
            "source": "Hertz Foundation",
            "type": "Fellowship",
            "url": url,
            "description": (
                desc[:400] or
                "The Hertz Fellowship supports PhD students in the applied physical, "
                "biological, and engineering sciences. One of the most prestigious "
                "graduate fellowships in the US, offering up to 5 years of support."
            ),
            "deadline": "October (annually)",
            "amount": "~$34,000/year + tuition",
            "posted": None,
            "relevance_score": 7,
            "tags": ["Fellowship", "Graduate", "STEM", "Prestigious"],
        })
        print("   Hertz: 1 item")
    except Exception as e:
        print(f"   Hertz error: {e}")
    return results


# ─────────────────────────────────────────────
# 6. Ford Foundation Fellowship
# ─────────────────────────────────────────────
def scrape_ford():
    print("→ Ford Foundation...")
    results = []
    try:
        results.append({
            "id": slugify("ford-foundation-fellowship"),
            "title": "Ford Foundation Fellowship Programs",
            "source": "Ford Foundation",
            "type": "Fellowship",
            "url": "https://www.nationalacademies.org/our-work/ford-foundation-fellowships",
            "description": (
                "Ford Foundation Predoctoral, Dissertation, and Postdoctoral Fellowships "
                "promote diversity in academia. Open to US citizens/nationals pursuing "
                "research-based PhDs across STEM and social sciences."
            ),
            "deadline": "December (annually)",
            "amount": "$27,000/year (predoctoral)",
            "posted": None,
            "relevance_score": 6,
            "tags": ["Fellowship", "Diversity", "Graduate", "Predoctoral"],
        })
        print("   Ford: 1 item")
    except Exception as e:
        print(f"   Ford error: {e}")
    return results


# ─────────────────────────────────────────────
# 7. Simons Foundation
# ─────────────────────────────────────────────
def scrape_simons():
    print("→ Simons Foundation...")
    results = []
    try:
        url = "https://www.simonsfoundation.org/funding-opportunities/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("article, .funding-item, .card, [class*='opportunity']")
        if not cards:
            cards = soup.select("h2, h3")
        for card in cards[:15]:
            title_tag = card.find("a") or card
            title = clean(title_tag.get_text())
            link = title_tag.get("href", "") if title_tag.name == "a" else ""
            if link and not link.startswith("http"):
                link = "https://www.simonsfoundation.org" + link
            if not title or len(title) < 5:
                continue
            score = keyword_score(title)
            results.append({
                "id": slugify(link or title),
                "title": title,
                "source": "Simons Foundation",
                "type": "Private Foundation Grant",
                "url": link or url,
                "description": "",
                "deadline": None,
                "amount": None,
                "posted": None,
                "relevance_score": score,
                "tags": ["Simons", "Private", "Math", "Life Sciences", "AI"],
            })
        if not results:
            results.append({
                "id": slugify("simons-foundation-main"),
                "title": "Simons Foundation Funding Opportunities",
                "source": "Simons Foundation",
                "type": "Private Foundation Grant",
                "url": url,
                "description": "Simons Foundation supports research in mathematics, theoretical physics, and life sciences including computational biology and AI.",
                "deadline": None,
                "amount": None,
                "posted": None,
                "relevance_score": 5,
                "tags": ["Simons", "Private", "Math", "Life Sciences", "AI"],
            })
        print(f"   Simons: {len(results)} items")
    except Exception as e:
        print(f"   Simons error: {e}")
    return results


# ─────────────────────────────────────────────
# 8. Wellcome Trust
# ─────────────────────────────────────────────
def scrape_wellcome():
    print("→ Wellcome Trust...")
    results = []
    try:
        url = "https://wellcome.org/grant-funding/schemes"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        links = soup.select("a[href*='/grant-funding/schemes/']")
        seen = set()
        for a in links[:20]:
            title = clean(a.get_text())
            href = a.get("href", "")
            if not href.startswith("http"):
                href = "https://wellcome.org" + href
            if not title or href in seen or len(title) < 5:
                continue
            seen.add(href)
            score = keyword_score(title)
            results.append({
                "id": slugify(href),
                "title": title,
                "source": "Wellcome Trust",
                "type": "Private Foundation Grant",
                "url": href,
                "description": "",
                "deadline": None,
                "amount": None,
                "posted": None,
                "relevance_score": score,
                "tags": ["Wellcome", "Biomedical", "Global Health", "Private"],
            })
        print(f"   Wellcome: {len(results)} items")
    except Exception as e:
        print(f"   Wellcome error: {e}")
    return results


# ─────────────────────────────────────────────
# 9. HHMI (Howard Hughes Medical Institute)
# ─────────────────────────────────────────────
def scrape_hhmi():
    print("→ HHMI...")
    results = []
    try:
        url = "https://www.hhmi.org/programs"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("a[href*='/programs/']")
        seen = set()
        for a in cards[:20]:
            title = clean(a.get_text())
            href = a.get("href", "")
            if not href.startswith("http"):
                href = "https://www.hhmi.org" + href
            if not title or href in seen or len(title) < 5:
                continue
            seen.add(href)
            score = keyword_score(title)
            results.append({
                "id": slugify(href),
                "title": title,
                "source": "HHMI",
                "type": "Private Foundation Grant",
                "url": href,
                "description": "",
                "deadline": None,
                "amount": None,
                "posted": None,
                "relevance_score": score,
                "tags": ["HHMI", "Biomedical", "Life Sciences"],
            })
        if not results:
            results.append({
                "id": slugify("hhmi-main"),
                "title": "HHMI Investigator & Fellowship Programs",
                "source": "HHMI",
                "type": "Private Foundation Grant",
                "url": url,
                "description": "HHMI supports exceptional biomedical scientists through investigator programs and various fellowship opportunities.",
                "deadline": None,
                "amount": None,
                "posted": None,
                "relevance_score": 5,
                "tags": ["HHMI", "Biomedical", "Life Sciences"],
            })
        print(f"   HHMI: {len(results)} items")
    except Exception as e:
        print(f"   HHMI error: {e}")
    return results


# ─────────────────────────────────────────────
# 10. ProFellow (Fellowship aggregator)
# ─────────────────────────────────────────────
def scrape_profellow():
    print("→ ProFellow...")
    results = []
    try:
        url = "https://www.profellow.com/fellowships/field/stem/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select(".fellowship-card, article, .entry, [class*='fellowship']")
        for card in cards[:20]:
            title_tag = card.find("h2") or card.find("h3") or card.find("a")
            title = clean(title_tag.get_text()) if title_tag else ""
            link_tag = card.find("a")
            link = link_tag.get("href", "") if link_tag else ""
            if not link.startswith("http"):
                link = "https://www.profellow.com" + link
            desc_tag = card.find("p")
            desc = clean(desc_tag.get_text()) if desc_tag else ""
            if not title or len(title) < 5:
                continue
            score = keyword_score(title + " " + desc)
            results.append({
                "id": slugify(link or title),
                "title": title,
                "source": "ProFellow",
                "type": "Fellowship",
                "url": link,
                "description": desc[:300],
                "deadline": None,
                "amount": None,
                "posted": None,
                "relevance_score": score,
                "tags": ["Fellowship", "STEM", "Aggregator"],
            })
        print(f"   ProFellow: {len(results)} items")
    except Exception as e:
        print(f"   ProFellow error: {e}")
    return results


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def deduplicate(items):
    seen = set()
    out = []
    for item in items:
        if item["id"] not in seen:
            seen.add(item["id"])
            out.append(item)
    return out

def run():
    all_items = []

    scrapers = [
        scrape_nih,
        scrape_nsf,
        scrape_grantsgov,
        scrape_nsf_grfp,
        scrape_hertz,
        scrape_ford,
        scrape_simons,
        scrape_wellcome,
        scrape_hhmi,
        scrape_profellow,
    ]

    for scraper in scrapers:
        try:
            items = scraper()
            all_items.extend(items)
        except Exception as e:
            print(f"   !! Scraper {scraper.__name__} failed: {e}")
        time.sleep(1)  # polite delay between scrapers

    all_items = deduplicate(all_items)
    all_items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "count": len(all_items),
        "items": all_items,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done! {len(all_items)} funding opportunities saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    run()
