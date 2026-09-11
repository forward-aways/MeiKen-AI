"""Word（.docx）解析：段落与表格按文档顺序输出，标题样式转为 Markdown 标题。"""
from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from backend.documents.parsers.base import ParsedDocument, Parser, clip_text, rows_to_markdown


def _iter_blocks(doc):
    """按文档顺序遍历段落与表格。"""
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


class DocxParser(Parser):
    extensions = (".docx",)

    def parse(self, path: str, filename: str) -> ParsedDocument:
        doc = DocxDocument(path)
        parts: list[str] = []
        tables = 0
        for block in _iter_blocks(doc):
            if isinstance(block, Paragraph):
                t = block.text.strip()
                if not t:
                    continue
                style = (block.style.name or "").lower()
                if style.startswith("heading"):
                    try:
                        level = int(style.replace("heading", "").strip() or 1)
                    except ValueError:
                        level = 1
                    parts.append("#" * min(max(level, 1), 6) + " " + t)
                else:
                    parts.append(t)
            else:
                rows = [[cell.text for cell in row.cells] for row in block.rows]
                parts.append(rows_to_markdown(rows))
                tables += 1
        return ParsedDocument(
            text=clip_text("\n\n".join(parts)),
            meta={"tables": tables},
        )
