# 環境・構成：タスク管理

文書の状態：決定済み

## 1. 適用する共通構成

[Docker Compose](../../../steering/api/docker-compose.md)、[バージョン・依存管理](../../../steering/api/versions-and-dependencies.md)、[データ保存](../../../steering/api/data-storage.md)、[設定・秘密情報](../../../steering/api/settings-and-secrets.md)に従う。APIとPostgreSQLを起動し、Flywayを先に適用する。DBは永続ボリュームを使う。

## 2. 領域固有の依存・設定

追加の外部サービス・環境変数はなし。DB接続などは共通設定を利用する。マイグレーションは `apps/backend/db/migrations/` でバックエンド全体の連番として管理する。tasksのテーブルはこの領域が所有する。

## 3. 環境による違い

| 環境 | 構成・確認事項 |
| --- | --- |
| ローカル開発 | api・db・flywayを利用。`.env`からComposeが必要な変数だけを渡し、Pythonは`os.getenv()`で取得する。API公開はローカルに限定する。 |
| テスト | test・db-test・flyway-testを利用。開発DBとは接続先・認証情報・保存領域を分離し、開発DBへのフォールバックを禁止する。 |
| Git worktree | [作業分離の方針](../../../steering/aidd/modes.md)に従い、Composeのプロジェクト・公開ポート・ボリュームを他の作業と分離する。 |
| 本番 | 今回の対象外。公開運用の構成は決めない。 |

## 4. 未決定事項

[要求仕様](../requirements.md)のTASK-Q-001〜003への2026-11-16に承認済み。ツールの導入・互換性確認と具体的な依存の固定は実装時に行う。環境構築済みを意味しない。
