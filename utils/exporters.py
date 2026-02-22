"""Export chapters to TXT, PDF, and EPUB formats."""
import os
import re
import tempfile
from typing import List

from scraper import Chapter, Novel


def export_txt(novel: Novel, chapters: List[Chapter]) -> str:
    """Write novel to a temp TXT file, return path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False,
        encoding="utf-8",
        prefix=f"{_safe(novel.title)}_",
    )
    tmp.write(f"{novel.title}\n")
    tmp.write("=" * 60 + "\n\n")
    for ch in chapters:
        tmp.write(f"Chapter {ch.index + 1}: {ch.title}\n")
        tmp.write("-" * 40 + "\n")
        tmp.write(ch.content + "\n\n")
    tmp.close()
    return tmp.name


def export_pdf(novel: Novel, chapters: List[Chapter]) -> str:
    """Write novel to a temp PDF file, return path."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title page
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, _truncate(novel.title, 80), ln=True, align="C")
    pdf.ln(10)

    for ch in chapters:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        title_line = f"Chapter {ch.index + 1}: {_truncate(ch.title, 80)}"
        pdf.cell(0, 10, title_line, ln=True)
        pdf.ln(4)
        pdf.set_font("Helvetica", size=11)
        for para in ch.content.split("\n\n"):
            para = para.strip()
            if para:
                try:
                    pdf.multi_cell(0, 7, para)
                    pdf.ln(3)
                except Exception:
                    pass

    path = os.path.join(
        tempfile.gettempdir(),
        f"{_safe(novel.title)}.pdf",
    )
    pdf.output(path)
    return path


def export_epub(novel: Novel, chapters: List[Chapter]) -> str:
    """Write novel to a temp EPUB file, return path."""
    import ebooklib
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("zero-novel-scraper")
    book.set_title(novel.title)
    book.set_language("en")
    book.add_author(novel.author or "Unknown")

    spine = ["nav"]
    toc   = []

    for ch in chapters:
        c = epub.EpubHtml(
            title=ch.title,
            file_name=f"chap_{ch.index:05d}.xhtml",
            lang="en",
        )
        body = "".join(
            f"<p>{para}</p>"
            for para in ch.content.split("\n\n")
            if para.strip()
        )
        c.set_content(
            f"<html><body>"
            f"<h2>Chapter {ch.index + 1}: {ch.title}</h2>"
            f"{body}"
            f"</body></html>"
        )
        book.add_item(c)
        spine.append(c)
        toc.append(epub.Link(c.file_name, ch.title, f"chap_{ch.index}"))

    book.toc   = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    path = os.path.join(
        tempfile.gettempdir(),
        f"{_safe(novel.title)}.epub",
    )
    epub.write_epub(path, book)
    return path


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _safe(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip().replace(" ", "_")[:50]

def _truncate(text: str, n: int) -> str:
    return text[:n] + "…" if len(text) > n else text
