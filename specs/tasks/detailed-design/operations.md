# 実行手順：タスク管理

文書の状態：決定済み

## 1. 共通手順・Taskの実行前提

以下は実装時にリポジトリ直下の `Taskfile.yml` へ定義する予定のコマンド。**現時点では未実装・未実行**。ルートからGo TaskとDocker Composeを使って実行する。利用前に `.env.example` から開発専用の `.env` を用意する。実行の内部手順はTask定義に集約し、[Compose](../../../steering/api/docker-compose.md)・[テスト共通方針](../../../steering/api/testing.md)に合わせる。

検証対象は[testing.md](testing.md)。失敗は非ゼロ終了にし、テストが0件の場合を成功扱いにしない。実装後に各Taskの動作を確認し、未実装の記載を更新する。

## 2. テストのTask一覧

| 段階 | コマンド（予定） | 対象・準備 | 定義先（予定） |
| --- | --- | --- | --- |
| 単体 | `task test:unit` | domain・applicationとHTTP境界のDB不要テスト。testコンテナで実行。 | `Taskfile.yml` |
| 結合 | `task test:integration` | 実PostgreSQLとのRepository・Unit of Workの確認。db-test起動・Flyway適用後に実行。 | `Taskfile.yml` |
| E2E | `task test:e2e` | TestClientによるHTTP境界→実DBの一連の操作。db-test起動・Flyway適用後に実行。 | `Taskfile.yml` |

結合・E2Eはテスト用DBだけを初期化し、共通方針どおり直列実行する。通常の停止・再起動による永続化は、下表の開発用TaskとAPI呼び出しによる受入確認で補う。

## 3. 静的解析・その他のTask一覧

| 用途 | コマンド（予定） | 対象・準備・完了条件 | 定義先（予定） |
| --- | --- | --- | --- |
| Lint | `task lint` | backendのRuff checkが成功する。 | `Taskfile.yml` |
| フォーマット確認 | `task format:check` | backendのRuff format --checkが成功する。 | `Taskfile.yml` |
| 型検査 | `task typecheck` | backendのmypyが成功する。 | `Taskfile.yml` |
| OpenAPI出力 | `task openapi:export` | FastAPI生成スキーマを比較用ファイルへ出力する。手書き仕様を上書きしない。 | `Taskfile.yml` |
| ビルド・起動 | `task dev:up` | APIイメージのビルド、DB待機、Flyway適用、API起動の順。途中失敗は起動成功にしない。 | `Taskfile.yml` |
| 停止 | `task dev:down` | 開発用Composeを停止する。保存ボリュームは削除しない。 | `Taskfile.yml` |

OpenAPIの出力成功だけで整合確認完了とはしない。[照合方針](../../README.md)に従い、4操作と参照スキーマ・応答ヘッダー・400応答などを手書き仕様と照合し、PRに結果を記録する。

## 4. 未決定事項

[要求仕様](../requirements.md)のTASK-Q-001〜003への2026-11-16に承認済み。Taskの内部構成・比較用ファイルの出力先は実装時に具体化する。
