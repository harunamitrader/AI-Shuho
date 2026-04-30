# AI-Shuho

複数のAI CLIツールのログから、週次活動レポートを自動生成するツールです。

ログを収集・集約し、Claude Codeのスキルとして動作するワークフローで、週報の執筆・X（Twitter）投稿用への分割・公開まで一気通貫で行います。

## 対応AIツール

| ソースID | 対象ツール |
|---------|-----------|
| `codex_cli` | Codex CLI |
| `copilot_cli` | GitHub Copilot CLI |
| `gemini_cli` | Gemini CLI |
| `claude_code_history` / `claude_code_projects` | Claude Code |
| `antigravity` | Antigravity（Gemini拡張エージェント） |

## 必要なもの

- Python 3.11 以上
- [Claude Code](https://github.com/anthropics/claude-code)

## セットアップ

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

### 設定ファイルを用意する

```bash
cp config/log-sources.local.json.example config/log-sources.local.json
```

`config/log-sources.local.json` を開き、自分の環境に合わせてログファイルのパスを設定します。

## 使い方（スキルベースのワークフロー）

AI-Shuho は Claude Code のスキルとして動作します。`skills/` に各フェーズのスキルが入っています。

### 初回のみ: 文体・AIキャラ設定

```
/ai-shuho-writing-setup
```

`config/writing-config.md` を作成し、週報の文体・各AIのキャラクター設定を行います。

### 週次: ログ収集 → 素材生成

```
/ai-shuho-ingest
```

1. ログファイルを SQLite DB に取り込む（差分のみ処理）
2. 指定週の素材ファイル `reports/weekly/YYYY-WNN-ai-shuho-materials.json` を生成する

### 週次: 週報執筆 → 公開

```
/ai-shuho-generate
```

1. 素材と `config/writing-config.md` をもとに週報を執筆
2. X投稿用に140字単位で分割
3. バリデーション
4. `reports/published/` に公開ファイルを出力

### CLIを直接使う場合

```bash
# ログを SQLite に取り込む
python -m ai_shuho logs-ingest

# 利用可能な週を確認する
python -m ai_shuho list-periods

# 指定週の素材を集約する
python -m ai_shuho ingest --period 2026-W17

# X投稿用に分割する
python -m ai_shuho split-for-x --period 2026-W17

# バリデーション
python -m ai_shuho validate --period 2026-W17

# 公開
python -m ai_shuho publish --period 2026-W17 --publish-dir reports/published
```

## ディレクトリ構成

```
AI-Shuho/
├── ai_shuho/                  # Python パッケージ
├── skills/                    # Claude Code スキル
│   ├── ai-shuho-ingest/       # ログ収集・素材生成
│   ├── ai-shuho-generate/     # 週報執筆・公開
│   ├── ai-shuho-writing-setup/ # 文体・キャラ設定（初回）
│   └── ai-shuho-missing-reports/ # 欠損週の確認
├── config/
│   ├── log-sources.json              # ログソース定義（テンプレート）
│   ├── log-sources.local.json.example # ローカル設定の例
│   ├── writing-config.default.md    # 文体設定のデフォルト
│   └── system-config.default.md     # システム設定のデフォルト
├── reports/
│   ├── weekly/    # 中間ファイル（.gitignore対象）
│   └── published/ # 公開済み週報（.gitignore対象）
└── data/          # SQLite DB（.gitignore対象）
```

## 設定ファイルについて

| ファイル | 説明 | git管理 |
|---------|------|:-------:|
| `config/log-sources.local.json` | ログファイルのパス（環境依存） | ✗ |
| `config/writing-config.md` | 週報の文体・AIキャラ設定 | ✗ |
| `config/system-config.md` | 期間・分割文字数等のカスタム設定 | ✗ |
| `config/log-sources.local.json.example` | ローカル設定の記述例 | ✓ |
| `config/writing-config.default.md` | 文体設定のデフォルト値 | ✓ |
| `config/system-config.default.md` | システム設定のデフォルト値 | ✓ |

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照してください。
