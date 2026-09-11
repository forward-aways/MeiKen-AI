"""解析器注册表：扩展名 → 解析器实例。

新增文件格式只需：
1. 实现 ``Parser`` 子类（独立文件）；
2. 在 ``_PARSER_CLASSES`` 注册一行。
"""
import os

from backend.documents.parsers.base import (
    ParsedDocument, Parser, UnsupportedFormatError,
)
from backend.documents.parsers.csv_parser import CsvParser
from backend.documents.parsers.docx_parser import DocxParser
from backend.documents.parsers.html_parser import HtmlParser
from backend.documents.parsers.pdf_parser import PdfParser
from backend.documents.parsers.pptx_parser import PptxParser
from backend.documents.parsers.text import TextParser
from backend.documents.parsers.xlsx_parser import XlsParser, XlsxParser

_PARSER_CLASSES = (
    TextParser,
    CsvParser,
    PdfParser,
    DocxParser,
    XlsxParser,
    XlsParser,
    PptxParser,
    HtmlParser,
)


def _build_registry() -> dict[str, Parser]:
    reg: dict[str, Parser] = {}
    for cls in _PARSER_CLASSES:
        inst = cls()
        for ext in inst.extensions:
            reg[ext] = inst
    return reg


_REGISTRY = _build_registry()

# 全部支持的扩展名（供上传校验使用）
SUPPORTED_EXTS = frozenset(_REGISTRY)

__all__ = [
    "ParsedDocument", "Parser", "UnsupportedFormatError",
    "SUPPORTED_EXTS", "extract_document", "get_parser",
]


def get_parser(filename: str) -> Parser | None:
    ext = os.path.splitext(filename or "")[1].lower()
    return _REGISTRY.get(ext)


def extract_document(path: str, filename: str) -> ParsedDocument:
    """按扩展名选择解析器并解析为 Markdown 文本。"""
    parser = get_parser(filename)
    if not parser:
        ext = os.path.splitext(filename or "")[1] or "(无扩展名)"
        raise UnsupportedFormatError(f"不支持的格式：{ext}")
    return parser.parse(path, filename)
