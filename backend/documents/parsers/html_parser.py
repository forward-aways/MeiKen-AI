"""HTML 解析：去除脚本/样式后，按标题、段落、列表、表格转为 Markdown。"""
from bs4 import BeautifulSoup

from backend.documents.parsers.base import ParsedDocument, Parser, clip_text, rows_to_markdown


class HtmlParser(Parser):
    extensions = (".html", ".htm")

    def parse(self, path: str, filename: str) -> ParsedDocument:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        parts: list[str] = []
        head_title = soup.title.get_text(strip=True) if soup.title else ""
        if head_title:
            parts.append(f"# {head_title}")

        for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table"]):
            if el.name.startswith("h"):
                t = el.get_text(" ", strip=True)
                if t:
                    parts.append("#" * int(el.name[1]) + " " + t)
            elif el.name == "p":
                t = el.get_text(" ", strip=True)
                if t:
                    parts.append(t)
            elif el.name == "li":
                t = el.get_text(" ", strip=True)
                if t:
                    parts.append(f"- {t}")
            elif el.name == "table":
                rows = [
                    [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                    for tr in el.find_all("tr")
                ]
                if rows:
                    parts.append(rows_to_markdown(rows))
        return ParsedDocument(text=clip_text("\n\n".join(parts)), meta={})
