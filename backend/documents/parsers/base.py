"""解析器协议与公共工具。

所有解析器输出 Markdown 化文本（标题层级 / 表格），
供知识库切分、技能解析与文件预览共用。
"""
from dataclasses import dataclass, field


# 单文档解析文本上限（约 200 万字符），防止异常文档撑爆内存
MAX_TEXT_CHARS = 2_000_000


class UnsupportedFormatError(ValueError):
    """没有对应解析器时抛出。"""


@dataclass
class ParsedDocument:
    """解析结果：Markdown 化正文 + 结构元信息（页数 / 表数等）。"""

    text: str
    meta: dict = field(default_factory=dict)


class Parser:
    """文档解析器基类：子类声明 extensions 并实现 parse。"""

    extensions: tuple[str, ...] = ()

    def parse(self, path: str, filename: str) -> ParsedDocument:
        raise NotImplementedError


def rows_to_markdown(rows: list[list], max_rows: int = 500) -> str:
    """二维数据转 Markdown 表格（超出行数截断并提示）。"""
    rows = [r for r in rows if r is not None]
    if not rows:
        return ""

    def cell(v) -> str:
        s = "" if v is None else str(v)
        return s.strip().replace("|", "\\|").replace("\n", " ")

    header = rows[0]
    lines = [
        "| " + " | ".join(cell(c) for c in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for r in rows[1:max_rows + 1]:
        lines.append("| " + " | ".join(cell(c) for c in r) + " |")
    if len(rows) - 1 > max_rows:
        lines.append(f"| …（其余 {len(rows) - 1 - max_rows} 行已省略） |")
    return "\n".join(lines)


def clip_text(text: str) -> str:
    """超长文本截断保护。"""
    if len(text) <= MAX_TEXT_CHARS:
        return text
    return text[:MAX_TEXT_CHARS] + "\n\n…（文档过长，已截断）"
