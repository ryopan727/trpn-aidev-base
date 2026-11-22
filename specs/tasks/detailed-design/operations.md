# 実行手順：タスク管理

文書の状態：決定済み

> 2026-11-22：タグ名の直接指定による付与・解除・一覧取得と、その制約・API・データモデルをユーザー承認済み（TASK-Q-004）。

## 1. 共通手順・Taskの実行前提

以下はリポジトリ直下の [Taskfile.yml](../../../Taskfile.yml) に定義したコマンド。ルートからGo TaskとDocker Composeを使って実行する。利用前に `.env.example` から開発専用の `.env` を用意する。実行の内部手順はTask定義に集約し、[Compose](../../../steering/api/docker-compose.md)・[テスト共通方針](../../../steering/api/testing.md)に合わせる。

検証対象は[testing.md](testing.md)。失敗は非ゼロ終了にし、テストが0件の場合を成功扱いにしない。実行結果はPRへ記録する。

## 2. テストのTask一覧

| 段階 | コマンド | 対象・準備 | 定義先 |
| --- | --- | --- | --- |
| 単体 | `task test:unit` | domain・applicationとHTTP境界のDB不要テスト。testコンテナで実行。 | `Taskfile.yml` |
| 結合 | `task test:integration` | 実PostgreSQLとのRepository・Unit of Workの確認。db-test起動・Flyway適用後に実行。 | `Taskfile.yml` |
| E2E | `task test:e2e` | db-test起動→Flyway適用→api-testのビルド・起動・healthcheck待機→実HTTPテスト。終了時は成功・失敗にかかわらずapi-testを停止する。 | `Taskfile.yml` |

結合・E2Eはテスト用DBだけを初期化する。通常の停止・再起動による永続化は、下表の開発用TaskとAPI呼び出しによる受入確認で補う。結合は `tests/tasks/infrastructure/`、E2Eは `tests/e2e/` を直列に実行し、同じテストDBに対して同時実行しない。E2E開始時にもapi-testを停止し、稼働中のAPIへマイグレーションを適用しない。起動・マイグレーション・テストの失敗は非ゼロ終了として返す。api-testのホスト向けポートは公開せず、Compose内部の通信を使う。開発用api・dbは操作しない。

## 3. 静的解析・その他のTask一覧

| 用途 | コマンド | 対象・準備・完了条件 | 定義先 |
| --- | --- | --- | --- |
| Lint | `task lint` | backendのRuff checkが成功する。 | `Taskfile.yml` |
| フォーマット確認 | `task format:check` | backendのRuff format --checkが成功する。 | `Taskfile.yml` |
| 型検査 | `task typecheck` | backendのmypyが成功する。 | `Taskfile.yml` |
| OpenAPI出力 | `task openapi:export` | FastAPI生成スキーマを比較用ファイルへ出力する。手書き仕様を上書きしない。 | `Taskfile.yml` |
| ビルド・起動 | `task dev:up` | APIイメージのビルド、DB待機、Flyway適用、API起動の順。途中失敗は起動成功にしない。 | `Taskfile.yml` |
| 停止 | `task dev:down` | 開発用Composeを停止する。保存ボリュームは削除しない。 | `Taskfile.yml` |

OpenAPIの出力成功だけで整合確認完了とはしない。[照合方針](../../README.md)に従い、既存4操作とタグ追加3操作、および参照スキーマ・応答ヘッダー・400応答などを手書き仕様と照合し、PRに結果を記録する。

タグ追加の実装・テストも既存Taskを利用する。新規3操作の生成OpenAPI照合と各段階のテスト結果はPRに記録する。

## 4. 未決定事項

[要求仕様](../requirements.md)のTASK-Q-001〜003は2026-11-16にユーザー承認済み。比較用の生成結果は `artifacts/openapi.generated.json`（Git管理外）に出力する。
\nタグ追加部分は[要求仕様](../requirements.md)のTASK-Q-004で承認済み。\n