---
# ---- 期間設定 ----
period_unit: week
# week   : 週単位（デフォルト）
# day    : 日単位
# month  : 月単位
# custom : period_days で日数を指定

period_days: 7
# period_unit: custom のときのみ使用

period_start_weekday: monday
# week のとき有効（monday / sunday / ...）

period_start_hour: 3
# 切り替え時刻（0〜23、ローカル時刻）
# 例: 3 → 月曜日 03:00 に週が切り替わる

# ---- 識別子形式 ----
period_id_format: "YYYY-WNN"
# YYYY-WNN  : 2026-W15（週単位デフォルト）
# YYYY-MM-DD: 2026-04-07（日単位向け）
# YYYY-MM   : 2026-04（月単位向け）

# ---- 長文出力 ----
draft_output: true
# 長文週報の出力（true / false）

# ---- ポスト分割 ----
split_enabled: true
# ポスト分割の有無（true / false）

split_char_limit: 140
# 1ポストあたりの文字数上限（ヘッダー含む）

split_header_format: "YYYY/WNN #N [TAG]"
# ヘッダーのフォーマット
# YYYY/WNN : period_id に連動
# #N       : ポスト番号
# [TAG]    : タグ（なければ省略）
---

このファイルはデフォルト設定です。上書き禁止。
カスタマイズは `system-config.md` に書いてください。

## 設定例

**3日ごと運用:**
```yaml
period_unit: custom
period_days: 3
period_id_format: "YYYY-MM-DD"
```

**月次・ポスト分割なし:**
```yaml
period_unit: month
period_id_format: "YYYY-MM"
split_enabled: false
```

**Threads向け500字分割:**
```yaml
split_enabled: true
split_char_limit: 500
```
