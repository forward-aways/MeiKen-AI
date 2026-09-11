"""PDF 解析：逐页提取文本，页间以分隔线连接。"""
from pypdf import PdfReader

from backend.documents.parsers.base import ParsedDocument, Parser, clip_text


class PdfParser(Parser):
    extensions = (".pdf",)

    def parse(self, path: str, filename: str) -> ParsedDocument:
        reader = PdfReader(path)
        pages = []
        for page in reader.pages:
            t = (page.extract_text() or "").strip()
            if t:
                pages.append(t)
        text = clip_text("\n\n---\n\n".join(pages))
        return ParsedDocument(text=text, meta={"pages": len(reader.pages)})
