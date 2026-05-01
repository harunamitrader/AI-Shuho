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

#### 2-a. 既存設定の確認

`config/log-sources.local.json` が存在し、1 つ以上の `patterns` が設定されていれば現在の設定を表示して Step 3（ユーザー確認）へ進む。

#### 2-b. 自動探索（初回 or 再スキャン）

`config/log-sources.local.json` が存在しない、またはすべてのソースの `patterns` が空の場合、各 AI ツールのデフォルト保存場所を自動検索する。

OS を検出して以下のコマンドを実行する。

**Windows（PowerShell）:**

```powershell
$u = $env:USERPROFILE
$checks = [ordered]@{
    claude_code_projects = "$u\.claude\projects"
    claude_code_history  = "$u\.claude"
    codex_cli            = "$u\.codex\sessions"
    gemini_cli           = "$u\.gemini\tmp"
    antigravity          = "$u\.gemini\antigravity"
    copilot_cli          = "$u\AppData\Roaming\GitHub Copilot"
}
foreach ($id in $checks.Keys) {
    $path = $checks[$id]
    if (Test-Path $path) {
        $count = (Get-ChildItem $path -Recurse -File -ErrorAction SilentlyContinue).Count
        Write-Host "FOUND: $id  ($path, $count files)"
    } else {
        Write-Host "NOT FOUND: $id  ($path)"
    }
}
```

**macOS / Linux（bash）:**

```bash
u="$HOME"
declare -A checks=(
    [claude_code_projects]="$u/.claude/projects"
    [claude_code_history]="$u/.claude"
    [codex_cli]="$u/.codex/sessions"
    [gemini_cli]="$u/.gemini/tmp"
    [antigravity]="$u/.gemini/antigravity"
)
for id in "${!checks[@]}"; do
    path="${checks[$id]}"
    if [ -d "$path" ]; then
        count=$(find "$path" -type f 2>/dev/null | wc -l | tr -d ' ')
        echo "FOUND: $id  ($path, $count files)"
    else
        echo "NOT FOUND: $id  ($path)"
    fi
done
```

#### 2-c. パスパターンの生成

`FOUND` となったソースについて、以下のデフォルトパターンを提案する（`YOUR_NAME` 部分は実際のユーザー名に置き換える）。

| ソース ID | パターン（Windows） | パターン（macOS/Linux） |
|---------|------------------|----------------------|
| `claude_code_projects` | `C:\Users\<name>\.claude\projects\**\*.jsonl` | `~/.claude/projects/**/*.jsonl` |
| `claude_code_history` | `C:\Users\<name>\.claude\history.jsonl` | `~/.claude/history.jsonl` |
| `codex_cli` | `C:\Users\<name>\.codex\sessions\**\*.jsonl` | `~/.codex/sessions/**/*.jsonl` |
| `gemini_cli` | `C:\Users\<name>\.gemini\tmp\*\chats\session-*.json` | `~/.gemini/tmp/*/chats/session-*.json` |
| `antigravity` | `C:\Users\<name>\.gemini\antigravity\brain\*\.system_generated\logs\overview.txt` | `~/.gemini/antigravity/brain/*/.system_generated/logs/overview.txt` |

探索結果と提案パターンをユーザーに表示する。

### 3. ユーザーに**必ず**確認する

**「以下の AI ツールのログが見つかりました。取得対象はこれでよいですか？除外したいものや追加したいパスがあれば教えてください。」**

確認が取れたら次のステップへ進む。

### 4. log-sources.local.json を作成・更新する

ユーザーが確認した内容で `config/log-sources.local.json` を Write する。  
既に存在する場合も、確認済みの内容で上書きする（上書き前に既存内容を表示して確認する）。

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
