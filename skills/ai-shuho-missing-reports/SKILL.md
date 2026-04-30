---
name: ai-shuho-missing-reports
description: 素材はあるが週報がまだ作られていない週を見つけ、まとめて生成するスキル。
---

# AI-Shuho Missing Reports

**未作成週報だけを埋める**専用スキルです。

`*-ai-shuho-cleaned-materials.json` が存在するのに公開済みファイル (`*-ai-shuho.md`) がない週を対象にします。

## 実行方針

- 週報本文はあなたが書く
- プログラムは素材整理・形式検査・公開だけを担当する
- 文体・視点・雰囲気は `config\writing-config.md` を優先する
- ユーザーの依頼が短くても、最大3回リトライ・失敗時レビュー待ちを既定動作にする
- `...` や `…` でプロンプトを途中省略しない
- 検査NGでも draft は捨てない

## 手順

```powershell
Set-Location "<AI-Shuho-root>"
```

`reports\weekly\` を確認し、`*-ai-shuho-cleaned-materials.json` が存在するが `*-ai-shuho.md` が存在しない週キーを列挙します。

**対象週がない場合は終了します。**

対象週ごとに以下を順番に実行します。

### Step 1: ingest（cleaned-materials.json が未作成の場合のみ）

```powershell
python -m ai_shuho ingest --period YYYY-WNN --daily-materials-dir "<daily-materials-dir>"
python -m ai_shuho clean-materials --period YYYY-WNN
```

### Step 2: generate（本文執筆）

次の2ファイルを Read します。

- `reports\weekly\YYYY-WNN-ai-shuho-cleaned-materials.json`
- `config\writing-config.md`（なければ `config\writing-config.default.md`）

この2ファイルをもとに、あなたが Write します。

- `reports\weekly\YYYY-WNN-ai-shuho-draft.md`

```powershell
python -m ai_shuho split-for-x --period YYYY-WNN
python -m ai_shuho validate --period YYYY-WNN
```

NG の場合は最大3回まで draft を書き直します。OK なら公開します。

```powershell
python -m ai_shuho publish --period YYYY-WNN
```

3回失敗した場合は `reports\weekly\YYYY-WNN-ai-shuho-review-needed.md` を作成して次の週へ進みます。

## 確認ファイル

- `reports\weekly\YYYY-WNN-ai-shuho.md`
- `reports\weekly\YYYY-WNN-ai-shuho-posts.json`
- `reports\weekly\YYYY-WNN-ai-shuho-validation.json`
- `reports\weekly\YYYY-WNN-ai-shuho-review-needed.md`（失敗時のみ）

## Guardrails

- 素材ファイルがない週の週報を捏造しない
- 既に公開済みの週報を勝手に上書きしない
- 内部パス・UUID・セッションIDを週報本文に出さない
