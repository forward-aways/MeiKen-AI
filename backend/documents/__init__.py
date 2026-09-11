"""文档解析层：多格式文件 → Markdown 文本。

对外统一入口（知识库 / 技能上传 / 文件预览共用）：
    from backend.documents import extract_document, SUPPORTED_EXTS
"""
from backend.documents.parsers import (
    ParsedDocument, Parser, UnsupportedFormatError,
    SUPPORTED_EXTS, extract_document, get_parser,
)

__all__ = [
    "ParsedDocument", "Parser", "UnsupportedFormatError",
    "SUPPORTED_EXTS", "extract_document", "get_parser",
]
