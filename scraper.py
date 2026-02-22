"""
Novel Scraper Engine
Supports:
  - Tomato / MTL-style sites
  - WordPress novel sites (WP-manga, Madara theme, etc.)
  - Generic sites with next-chapter buttons
  - Sites with chapter list pages
"""
import asyncio
import re
import logging
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
    chapters:    list[Chapter] = field(default_factory=list)

# ─── HTTP Session ─────────────────────────────────────────────────────────────
async def _fetch(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as r:
            r.raise_for_status()
            return await r.text(errors="replace")
    except Exception as e:
        logger.warning(f"Fetch failed for {url}: {e}")
        return ""

# ─── Chapter Content Cleaners ─────────────────────────────────────────────────
_AD_PATTERNS = [
    re.compile(r'\bif you (?:find|want|like|enjoy)\b.*', re.I),
    re.compile(r'\bplease (?:visit|support|read on|go to)\b.*', re.I),
    re.compile(r'https?://\S+'),
    re.compile(r'\bnovel\s*full\b', re.I),
    re.compile(r'\btranslat(?:ed|ion) by\b.*', re.I),
    re.compile(r'\bchapter end\b', re.I),
    re.compile(r'\[ *TL.*?\]', re.I),
]

def _clean_content(raw: str) -> str:
    paras = [p.strip() for p in raw.split("\n") if p.strip()]
    cleaned = []
    for p in paras:
        skip = False
        for pat in _AD_PATTERNS:
            if pat.search(p):
                skip = True
                break
        if not skip and len(p) > 3:
            cleaned.append(p)
    return "\n\n".join(cleaned)

# ─── Site Detectors ───────────────────────────────────────────────────────────
def _is_wordpress_madara(soup: BeautifulSoup) -> bool:
    return bool(
        soup.select(".wp-manga-chapter") or
        soup.select(".listing-chapters_wrap") or
        soup.find("div", class_=re.compile(r"madara"))
    )

def _is_tomato_mtl(soup: BeautifulSoup) -> bool:
    return bool(
        soup.select(".chapter-list") or
        soup.find("div", id="chapter-list") or
        soup.find("ul", class_=re.compile(r"chapter.*list", re.I))
    )

def _is_generic_list(soup: BeautifulSoup) -> bool:
    links = soup.find_all("a", href=re.compile(r"chapter", re.I))
    return len(links) >= 3

# ─── Chapter List Extractors ──────────────────────────────────────────────────
def _extract_chapters_madara(soup: BeautifulSoup, base_url: str) -> list[Chapter]:
    items = soup.select(".wp-manga-chapter a") or soup.select(".listing-chapters_wrap a")
    chapters = []
    for i, a in enumerate(reversed(items)):
        href  = a.get("href", "")
        title = a.get_text(strip=True) or f"Chapter {i+1}"
        if href:
            chapters.append(Chapter(index=i, title=title, url=urljoin(base_url, href)))
    return chapters

def _extract_chapters_generic(soup: BeautifulSoup, base_url: str) -> list[Chapter]:
    links = soup.find_all("a", href=re.compile(r"chapter", re.I))
    seen, chapters = set(), []
    for i, a in enumerate(links):
        href  = urljoin(base_url, a.get("href", ""))
        title = a.get_text(strip=True) or f"Chapter {i+1}"
        if href not in seen and href != base_url:
            seen.add(href)
            chapters.append(Chapter(index=len(chapters), title=title, url=href))
    return chapters

def _extract_novel_meta(soup: BeautifulSoup, url: str) -> dict:
    title = (
        soup.select_one(".post-title h1") or
        soup.select_one("h1.entry-title") or
        soup.select_one("h1") or
        soup.find("title")
    )
    title = title.get_text(strip=True) if title else urlparse(url).netloc

    cover = None
    img = soup.select_one(".summary_image img") or soup.select_one(".book-img img")
    if img:
        cover = img.get("src") or img.get("data-src")

    desc_el = soup.select_one(".description-summary") or soup.select_one(".entry-content")
    desc = desc_el.get_text("\n", strip=True)[:1000] if desc_el else ""

    return {"title": title, "cover_url": cover, "description": desc}

# ─── Chapter Content Extractor ────────────────────────────────────────────────
def _extract_chapter_content(soup: BeautifulSoup) -> str:
    # Try common novel reading containers
    containers = [
        soup.select_one(".reading-content"),
        soup.select_one("#chapter-content"),
        soup.select_one(".entry-content"),
        soup.select_one(".chapter-content"),
        soup.select_one(".text-left"),
        soup.select_one("article"),
    ]
    el = next((c for c in containers if c), None)
    if not el:
        return ""

    # Remove junk tags
    for tag in el.select("script, style, ins, .ads, .ad, .sharedaddy, iframe"):
        tag.decompose()

    raw = el.get_text("\n")
    return _clean_content(raw)

def _extract_chapter_title(soup: BeautifulSoup) -> str:
    for sel in [".chapter-title", ".entry-title", "h1", "h2"]:
        el = soup.select_one(sel)
        if el:
            return el.get_text(strip=True)
    return "Chapter"

def _find_next_chapter_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    for a in soup.find_all("a"):
        text = a.get_text(strip=True).lower()
        if "next" in text or "→" in text or ">" in text:
            href = a.get("href", "")
            if href and "chapter" in href.lower():
                return urljoin(base_url, href)
    return None

# ─── Main Scraper Class ───────────────────────────────────────────────────────
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
        """Scrape novel metadata + chapter list from given URL."""
        html = await _fetch(self.session, url)
        if not html:
            return None

        soup  = BeautifulSoup(html, "lxml")
        meta  = _extract_novel_meta(soup, url)

        if _is_wordpress_madara(soup):
            chapters = _extract_chapters_madara(soup, url)
        else:
            chapters = _extract_chapters_generic(soup, url)

        if not chapters:
            # Maybe the URL IS already a chapter; try next-button crawl
            chapters = await self._crawl_next_buttons(soup, url)

        novel = Novel(
            title=meta["title"],
            url=url,
            cover_url=meta.get("cover_url"),
            description=meta.get("description", ""),
            chapters=chapters,
        )
        return novel

    async def _crawl_next_buttons(self, first_soup: BeautifulSoup, first_url: str) -> list[Chapter]:
        """Follow next-chapter buttons to build chapter list (max 2000)."""
        chapters = []
        soup, url = first_soup, first_url
        for i in range(2000):
            title   = _extract_chapter_title(soup)
            content = _extract_chapter_content(soup)
            chapters.append(Chapter(index=i, title=title, url=url, content=content))
            next_url = _find_next_chapter_url(soup, url)
            if not next_url or next_url == url:
                break
            html = await _fetch(self.session, next_url)
            if not html:
                break
            soup = BeautifulSoup(html, "lxml")
            url  = next_url
        return chapters

    async def fetch_chapter(self, chapter: Chapter) -> Chapter:
        """Fetch content for a single chapter (fills chapter.content)."""
        if chapter.content:
            return chapter
        html = await _fetch(self.session, chapter.url)
        if html:
            soup = BeautifulSoup(html, "lxml")
            chapter.content = _extract_chapter_content(soup)
            if not chapter.title or chapter.title == "Chapter":
                chapter.title = _extract_chapter_title(soup)
        return chapter

    async def fetch_chapters_batch(
        self,
        chapters: list[Chapter],
        progress_cb=None,
        delay: float = 0.3,
    ) -> list[Chapter]:
        """Fetch many chapters with optional progress callback."""
        total = len(chapters)
        for i, ch in enumerate(chapters):
            chapters[i] = await self.fetch_chapter(ch)
            await asyncio.sleep(delay)
            if progress_cb:
                await progress_cb(i + 1, total)
        return chapters

# ─── Search ───────────────────────────────────────────────────────────────────
SEARCH_SOURCES = [
    "https://novelpub.com/search?keywords={q}",
    "https://readnovelfull.com/novel-list/search?keyword={q}",
    "https://mtlnovel.com/?s={q}",
]

@dataclass
class SearchResult:
    title:     str
    url:       str
    cover_url: Optional[str] = None
    desc:      str = ""

async def search_novels(query: str) -> list[SearchResult]:
    results = []
    async with aiohttp.ClientSession() as session:
        for source_tmpl in SEARCH_SOURCES:
            url  = source_tmpl.format(q=query.replace(" ", "+"))
            html = await _fetch(session, url)
            if not html:
                continue
            soup  = BeautifulSoup(html, "lxml")
            cards = (
                soup.select(".novel-item") or
                soup.select(".col-novel-main") or
                soup.select("article.post") or
                soup.find_all("a", href=re.compile(r"/novel/", re.I))
            )
            for card in cards[:5]:
                a = card.find("a") if card.name != "a" else card
                if not a:
                    continue
                href  = urljoin(url, a.get("href", ""))
                title = a.get_text(strip=True) or a.get("title", "Unknown")
                img   = card.find("img")
                cover = img.get("src") if img else None
                if href and title:
                    results.append(SearchResult(title=title, url=href, cover_url=cover))
            if results:
                break
    return results[:10]
