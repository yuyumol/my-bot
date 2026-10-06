# Daily Organic Chemistry News

毎朝7時（日本時間、GitHub Actionsの混雑で遅れることがあります）、直近3日間の有機化学・合成・触媒関連論文をOpenAlexで検索します。要旨のある論文を優先し、公開日の新しい順に最大3本を紹介。そのうち要旨のある1本をOpenAIで日本語解説し、Discordに投稿します。おすすめ一覧と解説は別メッセージです。

選定は要旨の有無と公開日による簡易的なものです。専門家による品質評価ではありません。候補が少ない日は3本未満になります。同じ論文が翌日の候補にもなることがあります（検索期間が重なるため）。

解説は「研究内容・新規性・研究への意義・要旨だけではわからない点」の4項目です。本文全体は取得しません。AIの誤りを完全には排除できないため、原論文と照合してください。要旨がない場合やAPI設定・生成に問題がある場合は解説を捏造せず、理由を通知します。

## GitHub Actionsの設定

リポジトリの Settings → Secrets and variables → Actions に登録してください。キーやWebhook URLをコードに書かないでください。

- `DISCORD_WEBHOOK_URL`（Secret、必須）：投稿先のDiscord Webhook URL。
- `OPENAI_API_KEY`（Secret、解説に必須）：OpenAI APIキー。API利用には料金が発生します。
- `OPENALEX_API_KEY`（Secret）：OpenAlex APIキー。APIが認証を要求する場合に設定してください。
- `OPENAI_MODEL`（Variable、任意）：既定は `gpt-4.1-mini`。

Actionsの「Daily Organic Chemistry News」→「Run workflow」でも実行できます。これは実際にDiscordへ投稿します。テストは投稿せず、API利用料金も発生しません。

## ローカル開発

Python 3.12を使用します。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python main.py --dry-run
```

`--dry-run` はDiscordには投稿しません。ただしOpenAlexへ接続し、`OPENAI_API_KEY` が設定されていれば解説生成APIも呼び出すため料金が発生します。必要な環境変数は安全な手段で注入してください。

通常実行は `python main.py` です。接続先は `api.openalex.org`、`api.openai.com`、Discord Webhookのホストです。クラウド環境ではこれらの通信許可が必要です。
