# 整理・削除候補ファイル一覧

作成日: 2026-09-18
目的: フォルダ分析で見つかった、目的が不明瞭・役割が重複しているファイルの棚卸し。実際の削除は行わず、判断材料として記録する。

## 1. archive/ フォルダ（旧 above/、レガシー試作コード一式）

`git log` の最初のコミット（first comit）で追加された、現行アプリからは参照されていない実験・プロトタイプ群。2026-09-18に `above/` から `archive/` へリネームされた。
- `GazoHakoTools.py`, `GazoTest001.py`, `GazoTest002Ai.py`, `GazoTest003Ai.py`, `GazoToolsLib2.py`, `HonkakuGazouAtari3.py`, `Test004.py`, `TestTimer001.py`, `Setting.ini`
- `flet_gazo006syoki.py`: GUIをflet(Web系UI)で試作していた名残。現行はtkinterに移行済み。
- `test_GazoHakoTools.py`, `__pycache__/`

**判断材料**: 現行コード(`GazoToolsApp.py`, `lib/`)から一切import・参照されていない。過去の設計検証の記録として残す価値はあるが、アプリの動作には不要。アーカイブ用ブランチ/zipに退避して本体から削除するのも一案。

## 2. ルート直下の単発検証・ベンチマークスクリプト

- `GazoToolsTest005.py` (577行): 2025-09-29作成、2026-01-01修正。用途がdocstringだけでは判別しづらく、`tests/`にもGitにも属さない孤立ファイル。
- `benchmark_ai.py`: AI処理（単一/バッチ/キャッシュ）のベンチマーク用。開発時のワンショット計測スクリプトで、CIやテストスイートには組み込まれていない。
- `runtime_checks.py`: `load_config`/`save_config`/`AppState`などの動作を手動確認するアドホックスクリプト。
- `test_output.txt`: 中身が0バイトの空ファイル。何らかのコマンドのリダイレクト先が放置されたものと推測される。

**判断材料**: いずれも「一度だけ動かして確認する」性質のツールで、正式なテストスイート(`tests/`)とは別物。残すなら `tools/` や `scripts/` ディレクトリを切って移動し、ルート直下を主要アプリファイルだけにするのが望ましい。`test_output.txt` は空なので削除して問題ない。

## 3. ルートの `code_analysis.md` と `docs/code_analysis.md`

同名だが中身は別物（root: プロジェクト全体のコード分析レポート、docs: `GazoToolsAI.py`のAI観点の詳細解説）。今回の統合対象（hister/task/errorlog）には含めなかったが、同じ紛らわしさがあるため次の整理候補にすべき。ファイル名を変えて役割を明確にする（例: `docs/AI_MODEL_ANALYSIS.md`）か、どちらかをdocs配下に一本化することを推奨。

## 4. プロジェクトと直接関係のないメモファイル（ルート直下・未コミット）

- `claude_code_vscode_guide.md`, `claude_code_vscode_guide_nvm.md`: VS CodeでClaude Codeを使うための環境構築メモ（GazoTools自体の仕様とは無関係）。
- `proto_skill.md`: GazoTools開発用のClaude Codeスキル定義の下書き（frontmatterに`name: gazo-tools-development`あり）。こちらはプロジェクトに関連するため削除候補ではないが、正式に使うなら `.claude/skills/` 等の所定の場所へ移動するのが望ましい。

**判断材料**: 前者2つは個人の環境構築ログであり、リポジトリのルートに置く必然性がない。ホームディレクトリのメモ置き場や別リポジトリへの移動を検討。

## まとめ（削除ではなく移動・整理の提案）

| ファイル/フォルダ | 提案 |
|---|---|
| `archive/` | 現状維持（リネーム済み） or 本体リポジトリから完全除外 |
| `GazoToolsTest005.py`, `benchmark_ai.py`, `runtime_checks.py` | `scripts/` 等へ移動し役割を明示 |
| `test_output.txt` | 削除可（空ファイル） |
| `code_analysis.md` / `docs/code_analysis.md` | 名前を分けて重複感を解消 |
| `claude_code_vscode_guide*.md` | プロジェクト外（個人メモ置き場）へ移動 |
| `proto_skill.md` | `.claude/skills/` 等の正式な場所へ移動して活用 |

実際にどれを削除/移動するかはユーザー判断が必要なため、本ドキュメントでは提案のみに留めています。
