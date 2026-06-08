import os

from google import genai
from google.genai import types

FORM_FIELD_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "field_name": {"type": "string"},
            "field_type": {
                "type": "string",
                "enum": ["text", "number", "date", "checkbox", "radio", "select", "textarea"],
            },
            "required": {"type": "boolean"},
            "options": {"type": "array", "items": {"type": "string"}},
            "value": {"type": "string"},
        },
        "required": ["field_name", "field_type", "required", "options", "value"],
    },
}

PROMPT_TEMPLATE = """\
以下是一份表單文件的純文字內容（含表格）。請分析這份文件，找出所有需要填寫的欄位。

對每個欄位，請依照 schema 回傳：
- field_name: 欄位名稱
- field_type: 類型（text / number / date / checkbox / radio / select / textarea）
- required: 是否必填
- options: checkbox/radio/select 的選項陣列，其他為空陣列
- value: 預設值或空字串

文件內容：
---
{text}
---
"""


def analyze_form(text: str) -> dict:
    """
    呼叫 Gemini API（gemini-2.5-flash + Structured Output）分析表單文字。
    回傳格式：{"fields": [...], "error": null}
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"fields": [], "error": "未設定 GEMINI_API_KEY 環境變數"}

    try:
        client = genai.Client(api_key=api_key)
        prompt = PROMPT_TEMPLATE.format(text=text)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FORM_FIELD_SCHEMA,
            ),
        )

        import json
        fields = json.loads(response.text)
        if not isinstance(fields, list):
            fields = []
        return {"fields": fields, "error": None}

    except Exception as e:
        return {"fields": [], "error": str(e)}
