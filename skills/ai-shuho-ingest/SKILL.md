---
name: ai-shuho-ingest
description: AI ログを収集・一元化し、週次素材を作るスキル。初回・週次どちらでも使う。writing-setup の前に実行する。
---

# AI-Shuho Ingest

AI ログの**収集・一元化と週次素材作成**を行うスキルです。初回・週次どちらでも使います。

このスキルは週次素材ファイルを作るだけで、執筆指示の生成・週報の執筆・性格設定には進まないこと。

## このスキルが終わったら次にやること

- 初回：→ `ai-shuho-writing-setup`（収集した素材をもとに文体・性格設定を行う）
- 週次：→ `ai-shuho-generate`（週報を生成する）

## 実行手順

### 1. ルートを確認する

- `<AI-Shuho-root>`: AI-Shuho プロジェクトのルート

### 2. ログ取得元を確認する

`<AI-Shuho-root>\config\log-sources.local.json` を Read する。  
存在しない場合は `config\log-sources.local.json.example` を参照して内容を提示する。

### 3. ユーザーに**必ず**確認する

**「ログファイルを取得する AI ツールはこれでいいですか？対象期間と除外したい週があれば教えてください。」**

### 4. log-sources.local.json を作成・確認する

`config\log-sources.local.json` が存在しない場合は、ユーザーが確認した取得元で作成する。

### 5. ログを一元化する

差分のみ取り込む（2回目以降は変更ファイルのみ処理される）。

```powershell
Set-Location "<AI-Shuho-root>"
python -m ai_shuho logs-ingest
```

### 6. 対象週をユーザーに確認する

SQLite DB から利用可能な週を一覧表示し、ユーザーに確認する。

```powershell
python -m ai_shuho list-periods
```

出力された週の一覧をユーザーに提示し、**「どの週を作成しますか？除外したい週があれば教えてください。」** と確認する。

ユーザーの返答を受けてから次のステップへ進む。

### 7. 週次素材を集約する

確認した対象週ごとに実行する（複数週ある場合は繰り返す）:

```powershell
python -m ai_shuho ingest --period YYYY-WNN
```

### 8. 確認する

週数分の以下ファイルが存在すること:

- `reports\weekly\YYYY-WNN-ai-shuho-materials.json`

## Guardrails

- SQLite にデータがなかった週の素材を捏造しない
- ユーザー確認前に取得元・対象期間を確定しない
- `log-sources.local.json` はユーザーの手元の環境依存情報を含むため git にコミットしない
- 週報の執筆・公開には進まない
