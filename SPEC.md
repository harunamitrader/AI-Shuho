# AI-Shuho 仕様書

## 1. 概要

AI-Shuho は、複数の AI ツールのローカルログファイルを読み取り、週次活動レポート（週報）を生成するツールです。

### 主要コンポーネント

| コンポーネント | 役割 |
|-------------|------|
| Python パッケージ `ai_shuho` | ログ収集・集計・分割・バリデーション・公開 |
| SQLite DB | ログデータの一元管理（差分管理付き） |
| AI スキル (`skills/`) | 週報生成ワークフローの指示書（LLM が読んで実行） |
| 設定ファイル (`config/`) | ログソース・文体・システム設定 |

---

## 2. データフロー

```
[AIツールのログファイル]
        ↓  logs-ingest
[SQLite DB (月次シャーディング)]
        ↓  ingest
[weekly-materials.json]  ←── [writing-config.md]
        ↓  (LLMが執筆)
[draft.md]
        ↓  split-for-x
[posts-draft.json]
        ↓  validate
        ↓  publish
[published/YYYY-WNN-ai-shuho.md]
[published/YYYY-WNN-ai-shuho-posts.md]
```

---

## 3. ログソース定義

### 3.1 設定ファイル

`config/log-sources.json` — デフォルト定義（ソース ID 一覧のみ、パスは空）  
`config/log-sources.local.json` — ユーザー環境のパス設定（git 管理外）

設定は `log-sources.local.json` が `log-sources.json` を上書き（マージ）します。

### 3.2 サポートするソース ID

| ソース ID | 対象ツール | デフォルトのパスパターン例 |
|---------|-----------|------------------------|
| `claude_code_projects` | Claude Code（プロジェクト別） | `~/.claude/projects/**/*.jsonl` |
| `claude_code_history` | Claude Code（履歴） | `~/.claude/history.jsonl` |
| `codex_cli` | OpenAI Codex CLI | `~/.codex/sessions/**/*.jsonl` |
| `codex_desktop_bridge` | Codex Desktop Bridge | ベンダー固有 |
| `gemini_cli` | Gemini CLI | `~/.gemini/tmp/*/chats/session-*.json` |
| `antigravity` | Antigravity | `~/.gemini/antigravity/brain/*/.system_generated/logs/overview.txt` |
| `copilot_cli` | GitHub Copilot CLI | ベンダー固有 |

### 3.3 log-sources.local.json スキーマ

```json
{
  "sources": {
    "<source_id>": {
      "patterns": ["<glob_pattern_1>", "<glob_pattern_2>"]
    }
  }
}
```

パスには glob パターン（`**`、`*`）が使えます。

---

## 4. SQLite DB 構造

### 4.1 ファイル配置

```
data/logs/db/
├── state.db        # ファイル処理状態・実行ログ（全期間共通）
└── YYYY-MM.db      # 月次シャーディング（例: 2026-04.db）
```

### 4.2 state.db テーブル

| テーブル | 主な列 | 役割 |
|---------|-------|------|
| `sources` | `source_id`, `display_name`, `extractor_version` | ソース定義 |
| `file_states` | `source_id`, `path`, `fingerprint`, `status` | 差分管理（変更済みファイルのみ再処理） |
| `runs` | `run_id`, `command`, `status`, `stats_json` | 実行ログ |

### 4.3 月次 DB テーブル（YYYY-MM.db）

| テーブル | 主な列 | 役割 |
|---------|-------|------|
| `sessions` | `session_id`, `source_id`, `started_at`, `ended_at` | セッション単位の集計 |
| `messages` | `session_id`, `role`, `day_key`, `char_count` | ユーザー・AI のメッセージ |
| `actions` | `session_id`, `action_type`, `day_key` | ツール使用・コマンド実行等 |

`day_key` 形式: `YYYY-MM-DD`

---

## 5. CLI コマンドリファレンス

実行形式: `python -m ai_shuho <command> [options]`

### `logs-ingest`

生の AI ログファイルを SQLite DB に取り込む。

```bash
python -m ai_shuho logs-ingest [--config-dir ./config] [--base-dir .]
```

- 差分管理あり（ファイルのフィンガープリントで変更を検出）
- 2 回目以降は変更ファイルのみ処理

### `list-periods`

SQLite DB に存在するデータの期間一覧を表示する。

```bash
python -m ai_shuho list-periods [--config-dir ./config]
```

出力例:
```
Available periods (4 weeks):
  2026-W14  (2026-03-30 ~ 2026-04-05, 7 days)
  2026-W15  (2026-04-07 ~ 2026-04-11, 5 days)
```

### `ingest`

指定期間の SQLite データを集約して `*-materials.json` を生成する。

```bash
python -m ai_shuho ingest --period YYYY-WNN [--reports-dir ./reports/weekly]
```

出力: `reports/weekly/YYYY-WNN-ai-shuho-materials.json`

### `split-for-x`

`draft.md` を X（Twitter）投稿用に分割して `posts-draft.json` を生成する。

```bash
python -m ai_shuho split-for-x --period YYYY-WNN [--reports-dir ./reports/weekly]
```

入力: `reports/weekly/YYYY-WNN-ai-shuho-draft.md`  
出力: `reports/weekly/YYYY-WNN-ai-shuho-posts-draft.json`

文字数上限は `system-config` の `split_char_limit`（デフォルト: 140）。

### `validate`

draft と posts-draft をバリデーションする。

```bash
python -m ai_shuho validate --period YYYY-WNN [--reports-dir ./reports/weekly]
```

出力: `reports/weekly/YYYY-WNN-ai-shuho-validation.json`  
エラー時は終了コード 1。

### `publish`

バリデーション済みの下書きを `reports/published/` にコピーして公開する。

```bash
python -m ai_shuho publish --period YYYY-WNN \
  [--reports-dir ./reports/weekly] \
  [--publish-dir ./reports/published]
```

出力:
- `reports/published/YYYY-WNN-ai-shuho.md`
- `reports/published/YYYY-WNN-ai-shuho-posts.md`

### 共通オプション

| オプション | デフォルト | 説明 |
|----------|----------|------|
| `--period` | （必須） | 期間キー（例: `2026-W17`） |
| `--config-dir` | `./config` | 設定ファイルのディレクトリ |
| `--reports-dir` | `./reports/weekly` | 中間ファイルのディレクトリ |
| `--base-dir` | カレントディレクトリ | 相対パスの基準 |

---

## 6. 設定ファイル仕様

### 6.1 system-config

`config/system-config.default.md`（デフォルト） / `config/system-config.md`（カスタム）

YAML フロントマター形式。

| キー | デフォルト | 説明 |
|-----|----------|------|
| `period_unit` | `week` | 期間単位（`week` / `day` / `month` / `custom`） |
| `period_days` | `7` | `custom` のときの日数 |
| `period_start_weekday` | `monday` | 週の開始曜日 |
| `period_start_hour` | `3` | 期間切り替え時刻（0-23） |
| `period_id_format` | `YYYY-WNN` | 期間キーのフォーマット |
| `draft_output` | `true` | 長文週報の出力有無 |
| `split_enabled` | `true` | ポスト分割の有無 |
| `split_char_limit` | `140` | 1 ポストあたりの文字数上限（ヘッダー含む） |
| `split_header_format` | `YYYY/WNN #N [TAG]` | 分割ヘッダーのフォーマット |

カスタム設定は `system-config.md` に変更したいキーのみ書きます（デフォルトと重複した行だけ上書きされます）。

### 6.2 writing-config

`config/writing-config.default.md`（デフォルト） / `config/writing-config.md`（カスタム）

YAML フロントマター + Markdown 本文の形式。

#### YAML フロントマターのキー

| キー | デフォルト | 説明 |
|-----|----------|------|
| `narrative_approach` | `spotlight_contrast` | ナレーション構造（`spotlight_contrast` / `chronological` / `theme`） |
| `opening_style` | `auto` | 書き出しスタイル（`auto` / `request` / `conclusion` / `observation`） |
| `perspective_switches_max` | `4` | 視点切り替えの最大回数 |
| `length_target_min` | `800` | 本文の最低文字数 |
| `length_target_max` | `2000` | 本文の最大文字数 |
| `tech_level` | `general_public` | 専門用語の扱い（`general_public` / `developer`） |

#### Markdown 本文の構成

- `## AIキャラクター設定` — 各 AI の表示名・一人称・口調・性格・文型パターン
- `## ナレーション構造` — 週報の構成ルール
- `## 視点切り替えルール` — AI 間の視点切り替え方法
- `## ユーザーとAIの関係性` — ユーザー名・ユーザーの扱い方
- `## トーン` — 比喩・数字の使い方
- `## 感情描写` — AI の感情表現ルール
- `## 追加ルール`（オプション） — ユーザー独自の書き方ルール

---

## 7. 中間ファイル仕様

### 7.1 weekly-materials.json

`reports/weekly/YYYY-WNN-ai-shuho-materials.json`

```json
{
  "period": "2026-W17",
  "period_label": "2026年4月21日〜4月27日",
  "days_loaded": 7,
  "actors": [
    {
      "ai_name": "claude_code_projects",
      "display_name": "Claude Code",
      "sessions_count": 12,
      "actions_count": 3450,
      "messages_count": 890,
      "active_days": ["2026-04-21", "2026-04-22"],
      "activity_level": "high",
      "daily": { ... }
    }
  ]
}
```

### 7.2 posts-draft.json

`reports/weekly/YYYY-WNN-ai-shuho-posts-draft.json`

```json
{
  "period": "2026-W17",
  "posts": [
    {
      "index": 1,
      "header": "2026/W17 #1 [Claude]",
      "body": "本文テキスト",
      "char_count": 138
    }
  ]
}
```

### 7.3 validation.json

`reports/weekly/YYYY-WNN-ai-shuho-validation.json`

```json
{
  "period": "2026-W17",
  "ok": true,
  "errors": [],
  "warnings": []
}
```

---

## 8. スキル定義

スキルは `skills/<スキル名>/SKILL.md` に YAML フロントマター + Markdown 本文で記述します。  
AI はこのファイルを読み込み、記述された手順に従って Python コマンドの実行・ファイルの読み書きを行います。

### スキル一覧

| スキル名 | ファイル | 実行タイミング |
|---------|---------|-------------|
| `ai-shuho-ingest` | `skills/ai-shuho-ingest/SKILL.md` | 初回・週次 |
| `ai-shuho-writing-setup` | `skills/ai-shuho-writing-setup/SKILL.md` | 初回のみ |
| `ai-shuho-generate` | `skills/ai-shuho-generate/SKILL.md` | 週次 |
| `ai-shuho-missing-reports` | `skills/ai-shuho-missing-reports/SKILL.md` | 任意 |

### スキルの前提条件

```
ai-shuho-ingest
    ↓ (必須)
ai-shuho-writing-setup  ← 初回のみ
    ↓ (必須)
ai-shuho-generate
```

---

## 9. 出力ファイル仕様

### 9.1 週報本文（ai-shuho.md）

`reports/published/YYYY-WNN-ai-shuho.md`

Markdown 形式。構成：

```markdown
## YYYY年MM月DD日〜MM月DD日 作業記録

| AI | セッション数 | 主な作業 |
|----|-------------|---------|
| Claude | 12 | コード実装、レビュー |
| Codex  | 5  | テスト修正 |

（本文: 各AIの視点で語るナレーション形式、800〜2000字）
```

### 9.2 X 投稿用テキスト（ai-shuho-posts.md）

`reports/published/YYYY-WNN-ai-shuho-posts.md`

```markdown
---
2026/W17 #1 [Claude]

（140字以内の投稿テキスト）

---
2026/W17 #2 [Codex]

（140字以内の投稿テキスト）
```

---

## 10. 実行フロー（スキルベース）

```
ユーザー: /ai-shuho-ingest
    ↓
AI: config/log-sources.local.json が存在するか確認
    ↓ 存在しない or パスが空の場合
AI: 各 AI ツールのデフォルト保存場所を自動探索（OS 検出 → コマンド実行）
AI: 見つかったツールの一覧とパスパターンをユーザーに提示・確認
AI: 確認済み内容で log-sources.local.json を書き込む
    ↓ 既存設定がある場合はそのまま利用（再スキャンも可）
AI: ユーザーに取得元・除外週を確認
    ↓
AI: python -m ai_shuho logs-ingest
    ↓
AI: python -m ai_shuho list-periods（週一覧をユーザーに提示）
    ↓
AI: ユーザーに対象週を確認
    ↓
AI: python -m ai_shuho ingest --period YYYY-WNN（各週）
    ↓
ユーザー: /ai-shuho-generate
    ↓
AI: writing-config.md と materials.json を読む
    ↓
AI: draft.md を執筆（Write）
    ↓
AI: python -m ai_shuho split-for-x --period YYYY-WNN
    ↓
AI: python -m ai_shuho validate --period YYYY-WNN
    ↓ NG の場合は draft.md を修正して再実行（最大3回）
AI: python -m ai_shuho publish --period YYYY-WNN --publish-dir reports/published
```
