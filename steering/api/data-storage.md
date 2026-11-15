# データ保存

状態：決定済み（2026-11-08）

## 決定済みの方針

- DBは **PostgreSQL** を採用し、Docker Composeで起動する。
- 初学者がSQLを読んで学べるよう、**SQL文を明示して実行する**。ORMによるSQLの組み立ては採用しない。
- DB構造の変更管理（マイグレーション）は **Flyway** を採用する。
- SQLの実行には **Psycopg 3**、接続管理には同期接続プールを採用する。
- 書き込みユースケース全体を1つのトランザクションとし、Unit of Workの契約で管理する。
- IDはアプリ側でUUIDv4を生成し、DBでは `uuid` 型に保存する。時点は `timestamptz` で保存し、アプリ・接続はUTCに揃える。
- 必須・一意・参照整合性はDB制約でも保証する。
- 既存の方針に従い、同期処理とRepositoryによる保存処理の分離を維持する。

以下に決定事項を記載し、選定時の比較も残します。DBやComposeの設定、ツールの実導入はまだ行いません。

## 1. SQLの実行・配置

| 選択肢 | 特徴 | 推奨する場面 |
| --- | --- | --- |
| Psycopg 3で直接実行（採用） | PostgreSQL用の接続ライブラリを使い、Repository内にSQL文字列を記載する。 | SQL、渡す値、取得結果を1か所で追いたい場合。追加のSQL管理ライブラリが不要。 |
| Psycopg 3＋別の `.sql` ファイル | SQLをファイルから読み込み、Psycopgで実行する。 | SQLだけを見たり編集したりしたい場合。ファイルの読み込み・配置管理が必要。 |
| aiosql＋Psycopg 3 | 名前を付けたSQLを `.sql` ファイルにまとめ、Pythonから呼び出す。 | SQLファイルが増えた場合。同期のPsycopgにも対応するが、SQLの命名記法とライブラリの使い方を学ぶ必要がある。 |

参照：[Psycopgの基本操作](https://www.psycopg.org/psycopg3/docs/basic/usage.html)、[aiosql公式](https://nackjicholson.github.io/aiosql/)。

**Psycopg 3で直接実行** を採用します。Repository内でのSQL実行部分の例です。`conn` は外から渡された接続を想定します。

```python
row = conn.execute(
    "SELECT id, status FROM orders WHERE id = %s",
    (order_id,),
).fetchone()
```

SQLは `infrastructure/repositories.py` に置き、取得した行をドメインのオブジェクトへ変換します。SQLやPsycopgの接続をapplication・domainへ持ち込みません。
SQLが長くなった場合は、そのサブドメインの `infrastructure/sql/` に `.sql` ファイルとして分離します。入力値はパラメーターとして渡し、f-stringや文字列連結でSQLに埋め込みません。並び順の列名などは値用のプレースホルダーで扱えないため、許可した列名に対応付けます。[パラメーターの渡し方](https://www.psycopg.org/psycopg3/docs/basic/params.html)を参照してください。

## 2. DB構造の変更管理

マイグレーションは、テーブル作成やカラム追加などの変更を履歴として管理し、順番に適用する仕組みです。

**Flywayを採用します（決定済み）。** テーブル作成・変更をSQLファイルで記載し、バックエンド全体で1つの変更履歴を管理します。

- 配置先：`apps/backend/db/migrations/`
- ファイル名：`V<バージョン>__<変更内容>.sql`。区切りはアンダースコア2つとし、バージョンはバックエンド全体で重複しない連番にする。
- 例：`V1__create_orders.sql`、`V2__add_order_note.sql`
- 適用済みのファイルは書き換えず、修正も新しいバージョンのSQLファイルで追加する。
- 適用は明示的な手順とし、各APIワーカーの起動時に同時実行しない。

Flywayはバージョン順に変更を適用し、適用履歴とチェックサムを管理します。[Flyway公式：Versioned migrations](https://documentation.red-gate.com/fd/versioned-migrations-273973333.html)を参照してください。

FlywayはPythonの依存としてuvに追加せず、独立したツールとして扱います。Docker Composeでの実行方法と設定の配置方針は[No.12](docker-compose.md)に従います。アプリからSQLを実行するPsycopgと接続プールのパッケージは、uvの実行用依存として管理します。

## 3. 接続とトランザクション

接続管理は「毎回接続する」「接続プールから借りる」のうち、**Psycopgの同期接続プール**を採用します。No.5の方針に従い、プールはアプリ起動時に用意し、リクエストごとに接続を借りて終了時に返します。[Psycopgの接続プール](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)を参照してください。

保存の確定単位は「Repositoryごと」「ユースケース全体」のうち、**最上位の書き込みユースケース全体で1つのトランザクション**を採用します。トランザクションは、複数の更新をまとめて成功または取り消しにする仕組みです。

- 同じ操作で使うRepositoryには同じ接続を渡し、Repository内ではcommitしない。
- application側はProtocolで定義したUnit of Work（更新をまとめる契約）を使う。Psycopgでの開始・commit・rollbackはinfrastructureで実装し、bootstrapで渡す。
- サブドメイン固有のUnit of Workの契約は `application/ports.py`、実装は `infrastructure/unit_of_work.py` に置く。共通化する場合も `shared` から個別サブドメインのRepositoryを参照しない。
- トランザクションはその操作のDBアクセス開始前に開始し、成功時に確定してからHTTP成功応答へ進む。失敗時は取り消す。`yield` 後の後片付けに保存確定を任せない。
- 既にトランザクションがある接続で `conn.transaction()` を使うとネストした扱いになり得るため、接続取得時の状態とトランザクションの所有者を実装時に明確にする。
- 外部APIやメール送信の結果はDBのrollbackでは取り消せないため、必要な機能で別途扱いを決める。

接続の貸出・返却とトランザクションの確定は別の責務です。Psycopgの `pool.connection()` は正常終了時に未完了のトランザクションをcommitするため、リクエスト終了時の自動commitに書き込みを残しません。Unit of Workを抜ける前に確定・取り消しを完了し、返却前には未完了のトランザクションがないことを保証します。読み取りでも既定ではトランザクションが始まるため、読み取り後も終了させてから接続を返します。
複数サブドメインを同一DB内で一括更新する場合も、最上位のユースケースがトランザクションを所有し、内側の操作は独立したcommitを行いません。必要な同一接続の共有はbootstrapで組み立て、サブドメイン間の公開契約を維持します。

例として「注文と明細を保存する」操作では、片方だけが確定しないようまとめます。詳細な接続動作は[Psycopgのトランザクション管理](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)を参照してください。

## 4. IDとデータの整合性

| 項目 | 選択肢 | 決定内容 |
| --- | --- | --- |
| ID生成 | DBの連番／UUIDv4／UUIDv7 | 初期構成はアプリ側でUUIDv4を生成する。DBへの保存前にIDを確定でき、ドメインをDBの採番から独立させやすい。UUIDv7は時刻情報を含む候補として、規模や要件に応じて検討する。 |
| IDの保存 | 文字列型／UUID型 | PostgreSQLの `uuid` 型を使い、APIではNo.7どおり文字列にする。 |
| 日時の保存 | タイムゾーンなし／時点を扱える型 | 時点は `timestamptz` に保存し、アプリ・接続の扱いはUTCに揃える。元の地域タイムゾーンが必要なら別項目で保持する。 |

参照：[PythonのUUID](https://docs.python.org/3/library/uuid.html)、[PostgreSQLのUUID型](https://www.postgresql.org/docs/current/datatype-uuid.html)、[日時型](https://www.postgresql.org/docs/current/datatype-datetime.html)。
必須・一意・参照整合性などは、業務ルールに加えてDB制約でも保証します。事前の存在確認だけで重複を防ごうとせず、既知の重複制約違反はNo.8の409に対応する例外へ変換します。想定外のDB障害は500として扱います。
同時更新への対応は機能の要件に合わせてロックや更新条件を設計します。トランザクションだけで、すべての競合を防げるとは扱いません。

No.9の方針はすべて決定済みです。各ツールの具体的なバージョンは導入時に最新安定版を確認して固定し、接続ライブラリはPython 3.15との互換性も確認します。Dockerの保存ボリュームは[No.12](docker-compose.md)、テスト用DBの分離は[No.13](testing.md)に従います。
