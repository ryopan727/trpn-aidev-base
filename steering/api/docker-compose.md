# Docker Compose・起動方法

状態：決定済み（2026-11-08）

ローカル開発ではAPI・PostgreSQL・FlywayをDocker Composeで管理する。本番用の起動構成は別途扱う。今回は方針のみを定め、DockerfileやComposeファイルはまだ作成しない。

## ファイルとサービスの配置

```text
リポジトリ直下/
├── compose.yaml
├── .env                       # 実際の設定値。Git管理対象外
├── .env.example               # 項目名とダミー値
└── apps/backend/
    ├── Dockerfile
    ├── .dockerignore
    ├── pyproject.toml
    ├── uv.lock
    ├── app/
    └── db/migrations/
```

| サービス | 役割・動作 |
| --- | --- |
| `api` | FastAPIをUvicornで起動する。 |
| `db` | PostgreSQLを起動し、named volumeへデータを保存する。 |
| `flyway` | SQLマイグレーションを明示的に実行する。処理終了後に終了し、常駐しない。 |
| `db-test` | テスト専用PostgreSQL。開発用と認証情報・保存領域を分離する。 |
| `flyway-test` | 同じSQLマイグレーションをテスト専用DBへ適用する。 |
| `test` | 開発用依存とテストコードを使ってpytestを実行する。APIサーバーは起動しない。 |

通常の開発で常駐するのは `api` と `db` です。Flywayとテスト関連サービスはprofilesで通常起動から外し、対象サービスを明示して実行します。`test` から開発用 `api`・`db` への依存は設けません。DB不要のテストは `--no-deps` で実行し、テスト専用DBも起動しません。

Composeファイルと `.env` はリポジトリ直下に置き、コマンドも同じ場所から実行する。APIのビルド対象は `apps/backend/` とする。
`.env` の値はComposeの `environment` でサービスごとに必要な変数へ対応付ける。PythonではNo.11どおり `os.getenv()` で取得する。FlywayにはFlyway用の接続設定を渡す。
初回は `.env.example` を `.env` へコピーして必要な値を設定する。テスト用は `TEST_DB_*` など開発用と区別した項目から渡し、値が欠けた場合に開発用へ代替しない。`.env` の変更はコンテナの再作成で反映する。単なる `docker compose restart` では環境変数は更新されない。

## イメージとAPIの起動

- PythonはNo.3で決定した版の公式slimイメージを使う。uvも決定した版を固定し、ビルド時に `uv sync --locked` で依存をインストールする。
- PostgreSQL・Flywayは導入時に最新安定版と組み合わせを確認し、具体的なイメージタグを固定する。通常の起動ごとに最新版へ更新しない。
- Uvicornを直接依存として宣言する。開発時は単一のサーバープロセスと自動リロードを使う。
- コンテナ内の作業ディレクトリをバックエンドのルートにし、その仮想環境の `uvicorn` で次のように起動する。

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --no-access-log
```

`app/main.py` にFastAPIの `app` を用意する想定。`--no-access-log` は[No.14](logging.md)の共通アクセスログとの二重出力を避けるために指定する。Uvicornの起動方法は[FastAPI公式](https://fastapi.tiangolo.com/deployment/manually/)、依存の構築は[uv公式](https://docs.astral.sh/uv/guides/integration/docker/)を参照。

## コード変更・接続・保存

- 開発時はホストの `apps/backend/app/` をコンテナのアプリディレクトリへbind mountし、コード変更を自動リロードで反映する。ホストの `.venv` は共有しない。
- `pyproject.toml` や `uv.lock` を変更した場合はAPIイメージを再ビルドする。
- APIはホストの `127.0.0.1:8000` に公開する。DBのポートはホストへ公開せず、Compose内ではサービス名 `db` で接続する。
- PostgreSQLのデータはnamed volumeで保持する。マウント先は選定したPostgreSQLイメージの仕様に合わせる。
- Flywayからは `apps/backend/db/migrations/` のSQLを読み取れるようにマウントする。
- DBに `pg_isready` のヘルスチェックを設定し、API・FlywayはDBが接続を受け付けられる状態になってから開始する。

単なるコンテナの起動とDBの準備完了は区別する。Composeでは `depends_on` の `service_healthy` で待機する。[Docker公式：起動順序](https://docs.docker.com/compose/how-tos/startup-order/)を参照。

## 起動と確認

初回起動・SQL変更時は次の順に実行する。各段階の成功を確認してから次へ進み、Flywayが失敗した場合はAPIの起動へ進まない。API起動だけでマイグレーションが適用される仕組みにはしない。

```bash
docker compose up -d --wait db
docker compose run --rm flyway migrate
docker compose up -d --build api
```

DB変更がなく既に適用済みの場合は、DBとAPIを起動する。SQL変更を稼働中のAPIへ適用する際は、開発用APIを停止してから上記の手順を実行する。
`--wait` はDBの準備完了を待ち、`run --rm` は単発実行したコンテナを終了後に削除する。[Compose up](https://docs.docker.com/reference/cli/docker/compose/up/)、[Compose run](https://docs.docker.com/reference/cli/docker/compose/run/)を参照。

起動確認は `docker compose ps` と `/docs` で行い、DB接続を含む確認はDBを使うAPIで行う。APIのログは `docker compose logs -f api` で確認する。
通常の停止・コンテナ削除は `docker compose down` とし、データを削除する `-v` は通常の手順に含めない。

テスト専用DBとテスト実行環境は[No.13](testing.md)を参照する。開発用とは別にテスト専用DBとテスト用サービスを用意する。

通常の起動からの除外は[Compose profiles](https://docs.docker.com/compose/how-tos/profiles/)、設定変更の反映は[Compose restartの注意点](https://docs.docker.com/reference/cli/docker/compose/restart/)を参照。
