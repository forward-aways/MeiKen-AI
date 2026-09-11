"""CSV / TSV 解析：转为 Markdown 表格。"""
import csv

from backend.documents.parsers.base import ParsedDocument, Parser, rows_to_markdown


class CsvParser(Parser):
    extensions = (".csv", ".tsv")

    def parse(self, path: str, filename: str) -> ParsedDocument:
        delimiter = "\t" if filename.lower().endswith(".tsv") else ","
        # utf-8-sig 兼容 Excel 导出的 BOM
        with open(path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            rows = [row for row in csv.reader(f, delimiter=delimiter)]
        return ParsedDocument(
            text=rows_to_markdown(rows),
            meta={"rows": max(0, len(rows) - 1)},
        )
