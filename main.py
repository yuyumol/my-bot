import os
import requests

url = os.environ["DISCORD_WEBHOOK_URL"]

response = requests.post(
    url,
    json={
        "username": "dailyreport_bot",
        "content": "🧪 dailyreport_bot 接続テスト成功！"
    },
    timeout=30
)

response.raise_for_status()

print("Discordへの送信に成功しました")
