import docx

MAX_CHARS = 8000


def extract_text(path: str) -> tuple[str, bool]:
    """
    從 .docx 提取段落與表格內容，回傳 (文字, 是否截斷)。
    表格每列以 | 分隔，每行以換行結束。
    """
    doc = docx.Document(path)
    parts = []

    for block in _iter_blocks(doc):
        if isinstance(block, docx.text.paragraph.Paragraph):
            text = block.text.strip()
            if text:
                parts.append(text)
        elif isinstance(block, docx.table.Table):
            parts.append(_table_to_text(block))

    full_text = "\n".join(parts)

    if len(full_text) > MAX_CHARS:
        return full_text[:MAX_CHARS] + "\n\n[警告：文件內容過長，已截斷至前 8000 字元]", True

    return full_text, False


def _iter_blocks(doc):
    """依文件順序交錯回傳段落與表格。"""
    from docx.oxml.ns import qn
    body = doc.element.body
    for child in body:
        if child.tag == qn("w:p"):
            yield docx.text.paragraph.Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield docx.table.Table(child, doc)


def _table_to_text(table) -> str:
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)
