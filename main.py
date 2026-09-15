import os
import requests

webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

if not webhook_url:
    raise RuntimeError(
        "DISCORD_WEBHOOK_URL が設定されていません。GitHub Secretsを確認してください。"
    )

response = requests.post(
    webhook_url,
    json={
        "username": "dailyreport_bot",
        "content": "🧪 GitHub Actions → Discord 接続成功！"
    },
    timeout=30
)

response.raise_for_status()

print("Discordへの送信に成功しました！")
