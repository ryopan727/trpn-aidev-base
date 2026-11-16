# 環境・構成：タスク管理

文書の状態：決定済み

## 1. 適用する共通構成

[Docker Compose](../../../steering/api/docker-compose.md)、[バージョン・依存管理](../../../steering/api/versions-and-dependencies.md)、[データ保存](../../../steering/api/data-storage.md)、[設定・秘密情報](../../../steering/api/settings-and-secrets.md)に従う。APIとPostgreSQLを起動し、Flywayを先に適用する。DBは永続ボリュームを使う。 実装は [compose.yaml](../../../compose.yaml)・[Dockerfile](../../../apps/backend/Dockerfile) を参照する。

初回実装では、[PostgreSQL公式](https://www.postgresql.org/download/)で確認した安定版18.7と、[Flyway公式リリースノート](https://documentation.red-gate.com/fd/release-notes-for-flyway-engine-179732572.html)の13.12.2を固定した（確認日：2026-11-16）。Python・FastAPI・uvは共通方針の固定版を維持し、依存解決とDockerでの結合テストにより組み合わせを確認する。

## 2. 領域固有の依存・設定

追加の外部サービス・環境変数はなし。DB接続などは共通設定を利用する。項目名は [.env.example](../../../.env.example)、読み込み・検証は [settings.py](../../../apps/backend/app/shared/infrastructure/settings.py) を参照する。マイグレーションは `apps/backend/db/migrations/` でバックエンド全体の連番として管理する。tasksのテーブルはこの領域が所有する。

## 3. 環境による違い

| 環境 | 構成・確認事項 |
| --- | --- |
| ローカル開発 | api・db・flywayを利用。`.env`からComposeが必要な変数だけを渡し、Pythonは`os.getenv()`で取得する。API公開はローカルに限定する。 |
| テスト | test・db-test・flyway-testを利用。開発DBとは接続先・認証情報・保存領域を分離し、開発DBへのフォールバックを禁止する。 |
| Git worktree | [作業分離の方針](../../../steering/aidd/modes.md)に従い、Composeのプロジェクト・公開ポート・ボリュームを他の作業と分離する。 |
| 本番 | 今回の対象外。公開運用の構成は決めない。 |

## 4. 未決定事項

[要求仕様](../requirements.md)のTASK-Q-001〜003は2026-11-16にユーザー承認済み。依存の具体的な固定は `apps/backend/pyproject.toml`・`uv.lock`、イメージの固定はルートの `compose.yaml`・バックエンドの `Dockerfile` を参照する。
