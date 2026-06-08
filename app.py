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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
