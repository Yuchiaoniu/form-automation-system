import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone

import bcrypt
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, session

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from db import get_doc, get_docs, get_forms, get_user, init_db, save_doc, save_form
from docx_builder import build_docx
from docx_extractor import extract_text
from forms_creator import create_form
from gemini_analyzer import analyze_form
from image_handler import analyze_image

DOCX_DIR = os.path.join(os.path.dirname(__file__), "data", "docx")
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
MIME_MAP = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
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


@app.route("/me", methods=["GET"])
def me():
    if not _user_id():
        return jsonify({"error": "未登入"}), 401
    return jsonify({"username": session.get("username")})


@app.route("/history", methods=["GET"])
def history():
    if not _user_id():
        return jsonify({"error": "未登入"}), 401
    forms = get_forms(_user_id())
    docs = get_docs(_user_id())
    return jsonify({"forms": forms, "docs": docs})


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


@app.route("/convert-image", methods=["POST"])
def convert_image():
    if not _user_id():
        return jsonify({"error": "未登入"}), 401

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未收到檔案"}), 400

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({"error": "僅支援 JPG、PNG 格式"}), 400

    mime_type = MIME_MAP[ext]
    original_filename = os.path.splitext(file.filename)[0]
    image_bytes = file.read()

    try:
        table_json = analyze_image(image_bytes, mime_type)
    except Exception as e:
        return jsonify({"error": f"圖片分析失敗：{e}"}), 500

    os.makedirs(DOCX_DIR, exist_ok=True)
    docx_filename = f"{uuid.uuid4().hex}.docx"
    docx_path = os.path.join(DOCX_DIR, docx_filename)

    try:
        build_docx(table_json, docx_path)
    except Exception as e:
        return jsonify({"error": f"文件建立失敗：{e}"}), 500

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    record_id = save_doc(_user_id(), original_filename, docx_path, created_at)

    return jsonify({
        "record_id": record_id,
        "original_filename": original_filename,
        "download_url": f"/download/{record_id}",
        "created_at": created_at,
    })


@app.route("/download/<int:record_id>", methods=["GET"])
def download(record_id):
    if not _user_id():
        return jsonify({"error": "未登入"}), 401

    doc = get_doc(record_id)
    if not doc:
        return jsonify({"error": "找不到記錄"}), 404
    if doc["user_id"] != _user_id():
        return jsonify({"error": "無權限"}), 403

    return send_file(
        doc["docx_path"],
        as_attachment=True,
        download_name=f"{doc['original_filename']}.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
