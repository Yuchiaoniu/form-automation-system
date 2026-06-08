"""
本機執行一次的 OAuth 授權工具。
執行前：將 GCP Console 下載的 OAuth 用戶端 JSON 存為 oauth-client-credentials.json
執行後：產生 user-credentials.json，再由 Claude SCP 到 VM。
"""
import json
import os
import sys

CLIENT_FILE = "oauth-client-credentials.json"
OUTPUT_FILE = "user-credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive",
]


def main():
    if not os.path.exists(CLIENT_FILE):
        print(f"找不到 {CLIENT_FILE}，請先從 GCP Console 下載 OAuth 用戶端金鑰。")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    # 存成 google.auth.default() 可讀的 authorized_user 格式
    token_data = {
        "type": "authorized_user",
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "refresh_token": creds.refresh_token,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2)

    print(f"已儲存憑證到 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
