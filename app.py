import os
import sys
import tempfile
from datetime import datetime, timezone

import bcrypt
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from db import get_forms, get_user, init_db, save_form
from docx_extractor import extract_text
from forms_creator import create_form
from gemini_analyzer import analyze_form

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True

init_db()


def _user_id():
    return session.get("user_id")


@app.route("/")
def index():
    return "", 200


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    user = get_user(username)
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "帳號或密碼錯誤"}), 401
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return jsonify({"ok": True, "username": user["username"]})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/history", methods=["GET"])
def history():
    if not _user_id():
        return jsonify({"error": "未登入"}), 401
    records = get_forms(_user_id())
    return jsonify({"records": records})


@app.route("/analyze", methods=["POST"])
def analyze():
    if not _user_id():
        return jsonify({"error": "未登入"}), 401

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未收到檔案"}), 400
    if not file.filename.lower().endswith(".docx"):
        return jsonify({"error": "僅支援 .docx 格式，請重新上傳"}), 400

    file_name = file.filename.replace(".docx", "").replace(".DOCX", "")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        text, truncated = extract_text(tmp_path)
        result = analyze_form(text)
        if result.get("error"):
            return jsonify(result)

        form_result = create_form(file_name, result["fields"])
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        if not form_result.get("error"):
            save_form(
                _user_id(), file_name,
                form_result.get("form_id"), form_result.get("edit_url"),
                form_result.get("respond_url"), created_at,
            )

        return jsonify({
            "fields": result["fields"],
            "truncated": truncated,
            "form_id": form_result.get("form_id"),
            "edit_url": form_result.get("edit_url"),
            "respond_url": form_result.get("respond_url"),
            "form_error": form_result.get("error"),
            "error": None,
        })
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
