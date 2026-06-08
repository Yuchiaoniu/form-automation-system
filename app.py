import json
import os
import sys
import tempfile

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from docx_extractor import extract_text
from gemini_analyzer import analyze_form
from forms_creator import create_form

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB 上限


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未收到檔案"}), 400

    if not file.filename.lower().endswith(".docx"):
        return jsonify({"error": "僅支援 .docx 格式，請重新上傳"}), 400

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        text, truncated = extract_text(tmp_path)
        result = analyze_form(text)
        result["truncated"] = truncated
        return jsonify(result)
    finally:
        os.unlink(tmp_path)


@app.route("/create-form", methods=["POST"])
def create_form_endpoint():
    data = request.get_json(silent=True) or {}
    fields = data.get("fields", [])
    title = data.get("title", "自動產生表單")
    if not fields:
        return jsonify({"error": "未提供欄位資料"}), 400
    result = create_form(title, fields)
    status = 500 if result.get("error") else 200
    return jsonify(result), status


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
