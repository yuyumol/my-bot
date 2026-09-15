import os
import requests
from datetime import date, timedelta

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

# 直近3日を検索
today = date.today()
from_date = today - timedelta(days=3)

# OpenAlexで「organic chemistry」に関連する新着論文を取得
params = {
    "search": "organic chemistry synthesis catalysis",
    "filter": f"from_publication_date:{from_date},to_publication_date:{today},type:article",
    "sort": "publication_date:desc",
    "per-page": 10,
}

response = requests.get(
    "https://api.openalex.org/works",
    params=params,
    timeout=30,
)

response.raise_for_status()
works = response.json()["results"]

if not works:
    message = "🧪 直近3日では候補論文が見つかりませんでした。"
else:
    lines = [
        "🧪 **有機化学・新着論文テスト**",
        f"検索期間：{from_date} ～ {today}",
        ""
    ]

    for i, work in enumerate(works[:5], start=1):
        title = work.get("display_name", "タイトル不明")
        pub_date = work.get("publication_date", "日付不明")
        doi = work.get("doi")

        lines.append(f"**{i}. {title}**")
        lines.append(f"公開日：{pub_date}")

        if doi:
            lines.append(f"DOI：{doi}")

        lines.append("")

    message = "\n".join(lines)

# Discordは1メッセージ2000文字までなので念のため制限
message = message[:1900]

discord_response = requests.post(
    WEBHOOK_URL,
    json={
        "username": "dailyreport_bot",
        "content": message,
    },
    timeout=30,
)

discord_response.raise_for_status()

print(f"OpenAlexから {len(works)} 件取得")
print("Discordへの送信成功")
