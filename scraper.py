"""
Novel Scraper Engine
Supports:
  - TomatoMTL (tomatotl.com)
  - MTLNovel (mtlnovel.com)
  - WordPress / Madara theme sites
  - ReadNovelFull, NovelPub, LightNovelPub
  - Generic sites with chapter lists or next-chapter buttons
"""
import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ─── Data Models ──────────────────────────────────────────────────────────────
@dataclass
class Chapter:
    index:   int
    title:   str
    url:     str
    content: str = ""

@dataclass
class Novel:
    title:       str
    url:         str
    cover_url:   Optional[str] = None
    description: str = ""
    author:      str = ""
    chapters:    list = field(default_factory=list)


# ─── HTTP ─────────────────────────────────────────────────────────────────────
async def _fetch(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(
            url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30),
            allow_redirects=True
        ) as r:
            r.raise_for_status()
            return await r.text(errors="replace")
    except Exception as e:
        logger.warning(f"Fetch failed {url}: {e}")
        return ""


# ─── Content Cleaner ──────────────────────────────────────────────────────────
_AD_PATTERNS = [
    re.compile(r'if you (find|want|like|enjoy)\b.*', re.I),
    re.compile(r'please (visit|support|read on|go to)\b.*', re.I),
    re.compile(r'https?://\S+'),
    re.compile(r'novel\s*full', re.I),
    re.compile(r'translat(ed|ion) by\b.*', re.I),
    re.compile(r'chapter end', re.I),
    re.compile(r'\[.*?TL.*?\]', re.I),
    re.compile(r'^\s*\*{3,}\s*$'),
    re.compile(r'sponsored.*content', re.I),
    re.compile(r'advertisement', re.I),
]

def _clean(raw: str) -> str:
    paras = [p.strip() for p in raw.split("\n") if p.strip()]
    out = []
    for p in paras:
        if any(pat.search(p) for pat in _AD_PATTERNS):
            continue
        if len(p) > 3:
            out.append(p)
    return "\n\n".join(out)


# ─── Site-Specific Scrapers ───────────────────────────────────────────────────

def _parse_tomato(soup: BeautifulSoup, base_url: str) -> tuple[dict, list]:
    """TomatoMTL / tomatotl.com"""
    title_el = (
        soup.select_one(".novel-title") or
        soup.select_one("h1.title") or
        soup.select_one("h1")
    )
    title = title_el.get_text(strip=True) if title_el else "Unknown"

    cover = None
    img = soup.select_one(".novel-cover img") or soup.select_one(".book-cover img")
    if img:
        cover = img.get("src") or img.get("data-src")

    desc_el = soup.select_one(".novel-summary") or soup.select_one(".description")
    desc = desc_el.get_text("\n", strip=True)[:800] if desc_el else ""

    # Chapter list
    chapters = []
    for a in soup.select(".chapter-list a, .chapters-list a, ul.chapter-list li a"):
        href  = urljoin(base_url, a.get("href", ""))
        title_ch = a.get_text(strip=True) or f"Chapter {len(chapters)+1}"
        if href and href != base_url:
            chapters.append(Chapter(index=len(chapters), title=title_ch, url=href))

    return {"title": title, "cover_url": cover, "description": desc}, chapters


def _parse_mtlnovel(soup: BeautifulSoup, base_url: str) -> tuple[dict, list]:
    """mtlnovel.com"""
    title_el = soup.select_one(".entry-title") or soup.select_one("h1")
    title    = title_el.get_text(strip=True) if title_el else "Unknown"

    cover = None
    img   = soup.select_one(".nov-head img")
    if img:
        cover = img.get("src")

    desc_el = soup.select_one(".desc")
    desc    = desc_el.get_text("\n", strip=True)[:800] if desc_el else ""

    chapters = []
    for a in soup.select(".ch-list a, .chapter-list a"):
        href  = urljoin(base_url, a.get("href", ""))
        t     = a.get_text(strip=True) or f"Chapter {len(chapters)+1}"
        if href and href != base_url:
            chapters.append(Chapter(index=len(chapters), title=t, url=href))

    return {"title": title, "cover_url": cover, "description": desc}, chapters


def _parse_madara(soup: BeautifulSoup, base_url: str) -> tuple[dict, list]:
    """WordPress Madara theme"""
    title_el = soup.select_one(".post-title h1") or soup.select_one("h1")
    title    = title_el.get_text(strip=True) if title_el else "Unknown"

    cover = None
    img   = soup.select_one(".summary_image img") or soup.select_one(".book-img img")
    if img:
        cover = img.get("src") or img.get("data-src") or img.get("data-lazy-src")

    desc_el = soup.select_one(".description-summary") or soup.select_one(".summary__content")
    desc    = desc_el.get_text("\n", strip=True)[:800] if desc_el else ""

    # Madara lists chapters newest-first → reverse
    items = list(reversed(soup.select(".wp-manga-chapter a")))
    chapters = []
    for a in items:
        href = urljoin(base_url, a.get("href", ""))
        t    = a.get_text(strip=True) or f"Chapter {len(chapters)+1}"
        if href and href != base_url:
            chapters.append(Chapter(index=len(chapters), title=t, url=href))

    return {"title": title, "cover_url": cover, "description": desc}, chapters


def _parse_generic(soup: BeautifulSoup, base_url: str) -> tuple[dict, list]:
    """Fallback generic parser"""
    title_el = soup.select_one("h1") or soup.find("title")
    title    = title_el.get_text(strip=True) if title_el else urlparse(base_url).netloc

    cover = None
    for sel in [".book-img img", ".novel-cover img", ".cover img", "img.cover"]:
        img = soup.select_one(sel)
        if img:
            cover = img.get("src") or img.get("data-src")
            break

    desc_el = soup.select_one(".description") or soup.select_one(".summary")
    desc    = desc_el.get_text("\n", strip=True)[:800] if desc_el else ""

    seen, chapters = set(), []
    links = soup.find_all("a", href=re.compile(r"chapter|ch-|chap", re.I))
    for a in links:
        href = urljoin(base_url, a.get("href", ""))
        t    = a.get_text(strip=True) or f"Chapter {len(chapters)+1}"
        if href and href not in seen and href != base_url:
            seen.add(href)
            chapters.append(Chapter(index=len(chapters), title=t, url=href))

    return {"title": title, "cover_url": cover, "description": desc}, chapters


def _detect_and_parse(soup: BeautifulSoup, url: str) -> tuple[dict, list]:
    domain = urlparse(url).netloc.lower()

    if "tomato" in domain:
        return _parse_tomato(soup, url)
    if "mtlnovel" in domain:
        return _parse_mtlnovel(soup, url)
    if soup.select(".wp-manga-chapter"):
        return _parse_madara(soup, url)
    if soup.select(".chapter-list a") or soup.select(".chapters-list a"):
        return _parse_tomato(soup, url)  # same structure

    return _parse_generic(soup, url)


# ─── Chapter Content Extractor ────────────────────────────────────────────────
_CONTENT_SELECTORS = [
    ".chapter-content",
    ".reading-content",
    "#chapter-content",
    ".text-left",
    ".entry-content",
    ".novel-content",
    ".chapter-body",
    "article",
]

def _extract_content(soup: BeautifulSoup) -> str:
    for sel in _CONTENT_SELECTORS:
        el = soup.select_one(sel)
        if el:
            for junk in el.select("script,style,ins,.ads,.ad,iframe,.sharedaddy"):
                junk.decompose()
            return _clean(el.get_text("\n"))
    return ""

def _extract_chapter_title(soup: BeautifulSoup) -> str:
    for sel in [".chapter-title", ".entry-title", "h1", "h2"]:
        el = soup.select_one(sel)
        if el:
            return el.get_text(strip=True)
    return "Chapter"

def _find_next_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    for a in soup.find_all("a"):
        t = a.get_text(strip=True).lower()
        if any(w in t for w in ["next", "→", "next chapter", ">"]):
            href = a.get("href", "")
            if href and re.search(r"chapter|chap|ch-", href, re.I):
                return urljoin(base_url, href)
    return None


# ─── Main Scraper ─────────────────────────────────────────────────────────────
class NovelScraper:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *_):
        if self.session:
            await self.session.close()

    async def scrape_novel(self, url: str) -> Optional[Novel]:
        html = await _fetch(self.session, url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        meta, chapters = _detect_and_parse(soup, url)

        # If no chapter list found, this might already be a chapter page
        if not chapters:
            chapters = await self._crawl_next(soup, url)

        return Novel(
            title=meta["title"],
            url=url,
            cover_url=meta.get("cover_url"),
            description=meta.get("description", ""),
            chapters=chapters,
        )

    async def _crawl_next(self, first_soup: BeautifulSoup, first_url: str) -> list:
        chapters, seen = [], set()
        soup, url = first_soup, first_url

        for i in range(2000):
            if url in seen:
                break
            seen.add(url)
            title   = _extract_chapter_title(soup)
            content = _extract_content(soup)
            chapters.append(Chapter(index=i, title=title, url=url, content=content))

            next_url = _find_next_url(soup, url)
            if not next_url or next_url in seen:
                break

            html = await _fetch(self.session, next_url)
            if not html:
                break
            soup = BeautifulSoup(html, "lxml")
            url  = next_url

        return chapters

    async def fetch_chapter(self, chapter: Chapter) -> Chapter:
        if chapter.content:
            return chapter
        html = await _fetch(self.session, chapter.url)
        if html:
            soup = BeautifulSoup(html, "lxml")
            chapter.content = _extract_content(soup)
            if not chapter.title or chapter.title in ("Chapter", ""):
                chapter.title = _extract_chapter_title(soup)
        return chapter

    async def fetch_chapters_batch(
        self, chapters: list, progress_cb=None, delay: float = 0.3
    ) -> list:
        total = len(chapters)
        for i, ch in enumerate(chapters):
            chapters[i] = await self.fetch_chapter(ch)
            await asyncio.sleep(delay)
            if progress_cb:
                await progress_cb(i + 1, total)
        return chapters


# ─── Search ───────────────────────────────────────────────────────────────────
@dataclass
class SearchResult:
    title:     str
    url:       str
    cover_url: Optional[str] = None
    desc:      str = ""

_SEARCH_SOURCES = [
    ("https://tomatotl.com/?s={q}",              ".novel-item a", ".novel-item img"),
    ("https://mtlnovel.com/?s={q}",              ".box-novel a", ".box-novel img"),
    ("https://novelpub.com/search?keywords={q}", ".novel-item a", ".novel-item img"),
    ("https://readnovelfull.com/novel-list/search?keyword={q}", ".col-novel-main h3 a", ".col-novel-main img"),
]

async def search_novels(query: str) -> list:
    q = query.replace(" ", "+")
    results = []

    async with aiohttp.ClientSession() as session:
        for tmpl, link_sel, img_sel in _SEARCH_SOURCES:
            url  = tmpl.format(q=q)
            html = await _fetch(session, url)
            if not html:
                continue

            soup = BeautifulSoup(html, "lxml")
            links = soup.select(link_sel)

            for a in links[:5]:
                href  = urljoin(url, a.get("href", ""))
                title = a.get_text(strip=True)
                if href and title:
                    results.append(SearchResult(title=title, url=href))

            if results:
                break

    return results[:10]
