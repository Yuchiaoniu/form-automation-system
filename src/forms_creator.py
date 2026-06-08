import logging

import google.auth
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive",
]

SHARE_EMAIL = "yuchiao.niu@gmail.com"

TYPE_MAP = {
    "text":     "TEXT",
    "textarea": "PARAGRAPH_TEXT",
    "number":   "TEXT",
    "date":     "DATE",
    "radio":    "MULTIPLE_CHOICE",
    "checkbox": "CHECKBOX",
    "select":   "DROP_DOWN",
}


def _build_services():
    creds, _ = google.auth.default(scopes=SCOPES)
    forms_svc = build("forms", "v1", credentials=creds, cache_discovery=False)
    drive_svc = build("drive", "v3", credentials=creds, cache_discovery=False)
    return forms_svc, drive_svc


def _field_to_item(field, index):
    q_type = TYPE_MAP.get(field.get("field_type", "text"), "TEXT")
    question = {"required": bool(field.get("required", False))}

    if q_type == "TEXT":
        question["textQuestion"] = {"paragraph": False}
    elif q_type == "PARAGRAPH_TEXT":
        question["textQuestion"] = {"paragraph": True}
    elif q_type == "DATE":
        question["dateQuestion"] = {"includeTime": False, "includeYear": True}
    elif q_type in ("MULTIPLE_CHOICE", "CHECKBOX", "DROP_DOWN"):
        options = [{"value": o} for o in field.get("options", []) if o]
        if not options:
            options = [{"value": "選項 1"}]
        choice_q = {"options": options}
        if q_type == "MULTIPLE_CHOICE":
            question["choiceQuestion"] = {**choice_q, "type": "RADIO"}
        elif q_type == "CHECKBOX":
            question["choiceQuestion"] = {**choice_q, "type": "CHECKBOX"}
        else:
            question["choiceQuestion"] = {**choice_q, "type": "DROP_DOWN"}

    return {
        "createItem": {
            "item": {
                "title": field.get("field_name", f"欄位 {index + 1}"),
                "questionItem": {"question": question},
            },
            "location": {"index": index},
        }
    }


def create_form(title: str, fields: list) -> dict:
    try:
        forms_svc, drive_svc = _build_services()
    except Exception as e:
        return {"form_id": None, "edit_url": None, "respond_url": None, "error": str(e)}

    try:
        form = forms_svc.forms().create(body={"info": {"title": title}}).execute()
        form_id = form["formId"]
        respond_url = form.get("responderUri", f"https://docs.google.com/forms/d/{form_id}/viewform")
        edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    except Exception as e:
        return {"form_id": None, "edit_url": None, "respond_url": None, "error": f"建立表單失敗：{e}"}

    if fields:
        requests_body = [_field_to_item(f, i) for i, f in enumerate(fields)]
        try:
            forms_svc.forms().batchUpdate(
                formId=form_id, body={"requests": requests_body}
            ).execute()
        except Exception as e:
            logging.warning("batchUpdate 部分失敗：%s", e)

    try:
        drive_svc.permissions().create(
            fileId=form_id,
            body={"type": "user", "role": "writer", "emailAddress": SHARE_EMAIL},
            sendNotificationEmail=False,
        ).execute()
    except Exception as e:
        logging.warning("分享失敗（不影響結果）：%s", e)

    return {"form_id": form_id, "edit_url": edit_url, "respond_url": respond_url, "error": None}
