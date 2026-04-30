# AI-Shuho

Claude Code・Codex CLI・Gemini CLI などの AI ツールの使用記録を自動で集め、週報を作成するツールです。

作った週報は X（Twitter）投稿用に 140 字ずつ自動分割されます。

## できること

- 複数の AI ツールのログを一か所に集める（差分のみ処理するので 2 回目以降は速い）
- 週ごとの活動サマリーを素材として整理する
- AI ごとのキャラクター・文体を設定して週報を自動執筆する
- X（Twitter）投稿用に 140 字単位で分割する
- バリデーション → 公開まで一気通貫で行う

## 対応 AI ツール

| ソース ID | 対象ツール |
|---------|-----------|
| `claude_code_history` / `claude_code_projects` | Claude Code |
| `codex_cli` | Codex CLI |
| `gemini_cli` | Gemini CLI |
| `antigravity` | Antigravity（Gemini 拡張エージェント） |
| `copilot_cli` | GitHub Copilot CLI |

## 必要なもの

- Python 3.11 以上
- 上記の AI ツールのいずれか（ログファイルが存在すれば動きます）
- Claude Code、または SKILL.md を読んでコマンドを実行できる AI ツール

---

## セットアップ

### 1. リポジトリを取得してインストールする

```bash
git clone https://github.com/harunamitrader/AI-Shuho.git
cd AI-Shuho

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e .
```

### 2. ログの場所を設定する

```bash
cp config/log-sources.local.json.example config/log-sources.local.json
```

`config/log-sources.local.json` を開き、各 AI ツールのログファイルがある場所を書きます。

```json
{
  "sources": {
    "claude_code_projects": {
      "patterns": ["C:\\Users\\あなたのユーザー名\\.claude\\projects\\**\\*.jsonl"]
    },
    "codex_cli": {
      "patterns": ["C:\\Users\\あなたのユーザー名\\.codex\\sessions\\**\\*.jsonl"]
    },
    "gemini_cli": {
      "patterns": ["C:\\Users\\あなたのユーザー名\\.gemini\\tmp\\*\\chats\\session-*.json"]
    }
  }
}
```

使っていないツールは書かなくて構いません。

---

## AI へのスキル登録

AI-Shuho の週報生成は「スキル」という指示書（Markdown ファイル）を使って動きます。  
スキルは `skills/` フォルダに入っています。

| スキル名 | ファイル | 役割 |
|---------|---------|------|
| `/ai-shuho-ingest` | `skills/ai-shuho-ingest/SKILL.md` | ログ収集・素材生成 |
| `/ai-shuho-writing-setup` | `skills/ai-shuho-writing-setup/SKILL.md` | 文体・キャラ設定（初回のみ） |
| `/ai-shuho-generate` | `skills/ai-shuho-generate/SKILL.md` | 週報執筆・公開 |
| `/ai-shuho-missing-reports` | `skills/ai-shuho-missing-reports/SKILL.md` | 未作成週の一括生成 |

### Claude Code の場合

AI-Shuho フォルダを作業ディレクトリとして Claude Code を起動すると、`skills/` 内のスキルが使えるようになります。

```
/ai-shuho-ingest
```

のように入力するだけで動きます。スキルの中身や Python コマンドは Claude Code が自動で読んで実行します。

### その他の AI ツール（Gemini、Copilot 等）の場合

各スキルの SKILL.md ファイルの内容をそのままプロンプトとして AI に貼り付けると、同じワークフローを実行できます。

例：Gemini に `/ai-shuho-ingest` 相当の処理をさせる場合

```
以下の手順でAI-Shuhoのログ収集と素材生成を行ってください。
---
（skills/ai-shuho-ingest/SKILL.md の内容をここに貼り付ける）
---
AI-Shuho のルートディレクトリ: C:\path\to\AI-Shuho
```

---

## 使い方

ワークフローは「初回のみ行うセットアップ」と「毎週繰り返す作業」の 2 段階です。

---

### 初回のセットアップ

初めて使うときは、以下の順番で実行します。

#### Step 1: ログを収集して素材を作る

Claude Code または AI ツールに入力：

```
/ai-shuho-ingest
```

AI が以下を確認してきます：

> 「ログを取得する AI ツールはこれでよいですか？対象期間と除外したい週があれば教えてください。」

問題なければそのまま進めます。完了すると `reports/weekly/YYYY-WNN-ai-shuho-materials.json` が作られます。

#### Step 2: 文体・AI キャラクターを設定する

```
/ai-shuho-writing-setup
```

収集した素材から各 AI の活動傾向を自動分析し、キャラクター設定の初期案を提示します。

AI がヒアリングしてきます：

> 「各 AI のキャラクター設定はこれでよいですか？週報に登場させるあなたの名前を教えてください。」

設定が完了すると `config/writing-config.md` が作成されます。

#### Step 3: 週報を生成する

```
/ai-shuho-generate
```

素材と文体設定をもとに週報を自動執筆し、X 投稿用に分割して公開ファイルを出力します。

完了すると以下のファイルが作られます：
- `reports/published/YYYY-WNN-ai-shuho.md` — 週報本文
- `reports/published/YYYY-WNN-ai-shuho-posts.md` — X 投稿用分割テキスト

---

### 毎週の作業（2 回目以降）

毎週は Step 1 → Step 3 の 2 ステップだけです。

```
/ai-shuho-ingest
```

↓

```
/ai-shuho-generate
```

---

### 過去の週をまとめて作りたい場合

```
/ai-shuho-missing-reports
```

素材はあるが週報がまだの週を自動検出して、一括生成します。

---

## カスタマイズ

`config/system-config.md`（なければ新規作成）に以下を書くと動作を変えられます。

```yaml
# 3日ごとに集計する場合
period_unit: custom
period_days: 3
period_id_format: "YYYY-MM-DD"

# Threads 向け 500 字に変える
split_char_limit: 500

# 長文週報を出力しない
draft_output: false
```

デフォルトは週次（月曜 03:00 切り替え）・140 字分割です。

---

## ディレクトリ構成

```
AI-Shuho/
├── ai_shuho/           # Python パッケージ（ログ収集・集計・出力）
├── skills/             # AI スキル（ワークフロー指示書）
│   ├── ai-shuho-ingest/
│   ├── ai-shuho-generate/
│   ├── ai-shuho-writing-setup/
│   └── ai-shuho-missing-reports/
├── config/
│   ├── log-sources.json              # ログソース定義
│   ├── log-sources.local.json.example
│   ├── system-config.default.md     # 期間・分割設定のデフォルト
│   └── writing-config.default.md    # 文体設定のデフォルト
├── reports/
│   ├── weekly/    # 中間ファイル（.gitignore 対象）
│   └── published/ # 公開済み週報（.gitignore 対象）
└── data/          # SQLite DB（.gitignore 対象）
```

## 設定ファイル一覧

| ファイル | 説明 | git 管理 |
|---------|------|:-------:|
| `config/log-sources.local.json` | ログファイルのパス（環境依存） | ✗ |
| `config/writing-config.md` | 週報の文体・AI キャラ設定 | ✗ |
| `config/system-config.md` | 期間・分割文字数等のカスタム設定 | ✗ |
| `config/log-sources.local.json.example` | ローカル設定の記述例 | ✓ |
| `config/writing-config.default.md` | 文体設定のデフォルト値 | ✓ |
| `config/system-config.default.md` | システム設定のデフォルト値 | ✓ |

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照してください。
