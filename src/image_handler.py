import json
import os

from google import genai
from google.genai import types

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


SCHEMA = {
    "type": "object",
    "properties": {
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cells": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text":    {"type": "string"},
                                "rowspan": {"type": "integer"},
                                "colspan": {"type": "integer"},
                            },
                            "required": ["text", "rowspan", "colspan"],
                        },
                    }
                },
                "required": ["cells"],
            },
        }
    },
    "required": ["rows"],
}

_PROMPT = """你是一個表格識別系統。請分析圖片中的表格，回傳 JSON 格式的結構化資料。

規則：
1. 每個 cell 必須包含 text（字串）、rowspan（整數，預設 1）、colspan（整數，預設 1）
2. 若某格是合併格的「被合併區域」（即不是左上角主格），請跳過該格，不要重複列出
3. 手寫與打字填入的內容都要照實回傳
4. 若看不清楚的文字請以 "" 表示

範例格式：
{
  "rows": [
    {"cells": [{"text": "姓名", "rowspan": 1, "colspan": 1}, {"text": "王小明", "rowspan": 1, "colspan": 2}]},
    {"cells": [{"text": "部門", "rowspan": 2, "colspan": 1}, {"text": "工程部", "rowspan": 1, "colspan": 1}]}
  ]
}
"""


def analyze_image(image_bytes: bytes, mime_type: str) -> dict:
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            _PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SCHEMA,
        ),
    )
    raw = response.text
    data = json.loads(raw)
    # 補全缺漏的 rowspan/colspan
    for row in data.get("rows", []):
        for cell in row.get("cells", []):
            cell.setdefault("rowspan", 1)
            cell.setdefault("colspan", 1)
    return data
