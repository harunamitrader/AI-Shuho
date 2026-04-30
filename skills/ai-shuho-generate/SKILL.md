---
name: ai-shuho-generate
description: materials と writing-config を読んで週報本文を書き、検査・公開するスキル。1週・複数週どちらでも対応。ingest 済みが前提。
---

# AI-Shuho Generate

週報の**執筆・検査・公開**を行うスキルです。1週でも複数週でも対応します。

`ai-shuho-ingest` が完了していることが前提です。初回は `ai-shuho-writing-setup` も完了していること。

## フォルダ構成

| 種別 | 保存先 |
|------|--------|
| 素材（ソース） | `reports\weekly\YYYY-WNN-ai-shuho-materials.json` |
| 中間ファイル（draft・validation等） | `reports\weekly\YYYY-WNN-ai-shuho-*.{md,json}` |
| 公開ファイル（最終成果物のみ） | `reports\published\YYYY-WNN-ai-shuho.md` `reports\published\YYYY-WNN-ai-shuho-posts.md` |

## 前提確認

実行前に以下を確認します。不足している場合は対応するスキルを先に実行するよう伝えて終了します。

- `config\writing-config.md` が存在するか（なければ `ai-shuho-writing-setup` を先に実行）
- 対象週の `reports\weekly\*-ai-shuho-materials.json` が存在するか（なければ `ai-shuho-ingest` を先に実行）

既に `reports\published\*-ai-shuho.md` が存在する週はスキップし、ユーザーに通知します。

## 実行

```powershell
Set-Location "<AI-Shuho-root>"
```

対象週を確定します。日付範囲が指定された場合は system-config の週定義（デフォルト: 月曜03:00切り替え）に従って週キーに変換します。

対象週ごとに以下を順番に実行します。

### 本文執筆

次の2ファイルを Read します。

- `reports\weekly\YYYY-WNN-ai-shuho-materials.json`
- `config\writing-config.md`

この2ファイルをもとに、あなたが Write します。出力先は `reports\weekly\` です。

- `reports\weekly\YYYY-WNN-ai-shuho-draft.md`

**draft.md の構成:**

```
## {period_label} 作業記録

| AI | セッション数 | 主な作業 |
|----|-------------|---------|
（各AIの行）

（本文：全AI統合ナレーション形式）
```

本文は字数制約なし。密度の目安は writing-config の `length_target_min`〜`length_target_max` 字。
作業記録ブロックの文字数は目安に含めない。

```powershell
python -m ai_shuho split-for-x --period YYYY-WNN --reports-dir reports/weekly
python -m ai_shuho validate --period YYYY-WNN --reports-dir reports/weekly
```

NG の場合は `reports\weekly\YYYY-WNN-ai-shuho-validation.json` を Read し、draft.md を修正してから再度 split-for-x → validate を実行します。最大3回まで繰り返します。OK なら公開します。

```powershell
python -m ai_shuho publish --period YYYY-WNN --reports-dir reports/weekly --publish-dir reports/published
```

公開コマンドは `reports\weekly\` にある draft.md と posts-draft.json を読み、`reports\published\` に最終ファイルのみ書き出します。

3回失敗した場合は `reports\weekly\YYYY-WNN-ai-shuho-review-needed.md` を作成して次の週へ進みます。

## 完了後の報告

```
完了: 2026-W15, 2026-W16
スキップ（公開済み）: 2026-W14
要レビュー: 2026-W13
```

## Guardrails

- 素材ファイルがない週の週報を捏造しない
- 既存の公開済み週報を勝手に上書きしない
- 内部パス・UUID・セッションIDを週報本文に出さない
- `...` や `…` で本文を途中省略しない
- 文体・視点・雰囲気は `config\writing-config.md` を優先する
- 週ごとに独立した文章として書く（前週との連続性を前提にしない）
