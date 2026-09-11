"""纯文本与代码文件解析：按 UTF-8 读取（容错）。"""
from backend.documents.parsers.base import ParsedDocument, Parser, clip_text

_TEXT_EXTS = (
    ".txt", ".md", ".markdown", ".log",
    ".json", ".yaml", ".yml", ".ini", ".cfg", ".toml",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".java", ".kt",
    ".go", ".rs", ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php",
    ".sh", ".sql",
)


class TextParser(Parser):
    extensions = _TEXT_EXTS

    def parse(self, path: str, filename: str) -> ParsedDocument:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = clip_text(f.read())
        return ParsedDocument(text=text, meta={"chars": len(text)})
