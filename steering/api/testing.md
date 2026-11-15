# テスト

状態：決定済み（2026-11-08）

pytestとFastAPIのTestClientを基本とし、SQLの検証にはテスト専用PostgreSQLを使う。今回は方針のみを定め、テストコードやComposeの実行設定はまだ作成しない。

## ツールと配置

- `pytest` と、TestClientが利用する `httpx` をuvの開発用依存に追加する。版は導入時に互換性を確認して固定する。
- テストは通常の `def` と `assert` で記述し、準備・後片付けはpytestのfixtureで共通化する。
- 配置は `apps/backend/tests/<サブドメイン>/<層>/` を基本とする。共通処理は `tests/shared/`、組み立ては `tests/bootstrap/`、横断する連携テストは `tests/integration/` に置く。
- ファイル名・関数名は `test_` で始める。共通fixtureは必要な範囲の `conftest.py` に置く。

参照：[FastAPIのテスト](https://fastapi.tiangolo.com/tutorial/testing/)、[pytestのfixture](https://docs.pytest.org/en/stable/explanation/fixtures.html)。

## 層ごとの検証範囲

| 対象 | 確認すること | DBの扱い |
| --- | --- | --- |
| domain | 業務ルール、境界値、状態の変更、許可されない操作。 | 使用しない。 |
| application | ユースケースの結果、処理条件、失敗時の動作。 | Repositoryなどの契約を満たす簡単な代替実装を使う。 |
| presentation | HTTPステータス、JSON、入力検証、例外の変換。 | 原則として依存を置き換える。 |
| infrastructure | SQL、検索条件、保存結果、DB制約、行からドメインへの変換。 | テスト専用PostgreSQLを使う。 |
| integration | APIからDBまでの主要な処理のつながり。 | テスト専用PostgreSQLを使う。 |

例えば注文作成では、domainで不正な数量、presentationで入力不備の400、infrastructureで保存・取得、integrationでPOSTの201とGETによる取得を検証する。
正常系だけでなく、必要な境界値、対象なし、競合、想定外エラーも確認する。すべてのケースを全層で重複して検証せず、各層の責務に合わせる。
既に決定した契約の確認として、未知のクエリが400になること、JSON構文エラーと通常の入力検証エラーのコード、OpenAPIに既定の422が残らないこと、PATCHの省略とnullの違いも対象にする。
DB連携では複数更新の途中失敗で全体が取り消されることを確認する。共通処理では500を含む応答とログのリクエストIDの一致、秘密情報の非出力、障害ログの重複抑止を確認する。
最初からカバレッジの数値目標は設けず、業務上重要な動作と失敗時の振る舞いを優先する。

## 外部処理と設定の置き換え

- 外部サービスへは通常のテストから接続せず、簡単な代替実装を基本に、必要な箇所でモックを使う。
- applicationではコンストラクターから依存を渡し、APIテストでは `app.dependency_overrides` を使う。差し替えはfixtureの後片付けで戻す。
- 環境変数はpytestの `monkeypatch` で差し替え、必須設定の不足や型違反も検証する。
- DB不要のテストでDBプールを起動しないよう、アプリ生成・起動時の資源の組み立てもテスト用に差し替えられるようにする。依存関数の上書きだけで起動時のDB接続も止まるとは扱わない。
- 起動・終了処理を含むAPIテストではTestClientをコンテキストマネージャーで使う。
- 500の応答本文・ヘッダーを検証するテストでは `raise_server_exceptions=False` を指定する。通常のテストでは既定の例外再送出を維持し、実装の不具合を見つけやすくする。

参照：[FastAPIの依存の上書き](https://fastapi.tiangolo.com/advanced/testing-dependencies/)、[環境変数の差し替え](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)、[TestClientの500応答・lifespanの扱い](https://starlette.dev/testclient/)。TestClientとHTTPXの対応は、初回実装で解決するFastAPI・Starletteの版に合わせて確認する。

## テスト用DBとデータ

- Composeに開発用とは別のPostgreSQLサービスを用意し、接続先・認証情報・保存領域を分離する。PostgreSQLの版は開発用と揃える。
- テスト開始前に、開発用と同じFlywayのSQLマイグレーションを適用する。適用失敗時はDBテストへ進まない。
- 各DBテストの開始前に業務テーブルを空にし、必要なデータをfixtureで用意する。Flywayの適用履歴は残す。
- データの初期化はテスト専用DBに限定する。接続先が明示されていない場合やテスト用でない場合は停止し、開発用へのフォールバックは設けない。
- API側でcommitするテストもあるため、テスト終了時のrollbackだけに後片付けを任せない。
- 最初は並列実行せず、実行順序や他のテストのデータに依存させない。

## 実行方法

後続で決定した開発フローでは、以下の実行処理をTaskから呼び出し、各領域の `operations.md` にTaskコマンドを記載します。単体・結合・E2Eの対象範囲は `testing.md` で定めます。[specsの方針](../../specs/README.md)と[AI駆動開発の進め方](../aidd/README.md)を参照してください。以下のDB準備・分離・実行条件はTask化後も維持します。

Composeにテスト用サービスを用意し、同じバックエンドコードとロック済みの開発用依存でpytestを実行する。テストコードを利用できるようにし、接続先にはテスト専用DBを明示する。
DBを使うテストにはpytestの `db` マーカーを登録・付与し、DB不要のテストと分けて実行できるようにする。DB用fixtureは対象テストだけで起動し、DB不要の実行でDB接続やマイグレーションを要求しない。

以下はリポジトリ直下から実行するコマンドの方針。テスト用サービスの作業ディレクトリはバックエンドのルートとする。DB不要のテストは次のように実行する。

```bash
docker compose run --rm --build --no-deps test uv run --locked pytest -m "not db"
```

DBテストは次の順に実行し、各段階の成功を確認してから次へ進む。

```bash
docker compose up -d --wait db-test
docker compose run --rm flyway-test migrate
docker compose run --rm --build --no-deps test uv run --locked pytest -m db
```

実行時は開発用と同じマイグレーションファイルを使い、接続先だけをテスト専用へ切り替える。具体的なComposeサービス設定は実装時に用意する。
