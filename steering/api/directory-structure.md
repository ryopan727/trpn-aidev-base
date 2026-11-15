# ディレクトリ構成

状態：決定済み（2026-11-08）

[決定済みのアーキテクチャ](architecture.md)に沿って、以下の配置を採用します。
各層内の配置、共通処理、組み立て処理、テストの置き場所を定めます。
以下は注文サブドメインを例にした構成であり、実装ファイルはまだ作成しません。

## 採用する構成

```text
apps/backend/
├── Dockerfile                      # APIイメージの構築（No.12で決定）
├── .dockerignore                   # ビルド対象から除外するファイル
├── pyproject.toml                  # 依存関係とPythonの許容範囲（No.3で決定）
├── uv.lock                         # 間接依存を含むバージョン固定
├── .python-version                 # 開発で使うPythonのバージョン
├── db/
│   └── migrations/                 # FlywayのSQLマイグレーション（No.9で決定）
│       └── V1__create_orders.sql    # 初回のテーブル作成の例
├── app/
│   ├── main.py                     # FastAPIアプリの生成・ルーター登録
│   ├── bootstrap/                  # 具体的な実装を選び、組み合わせる場所
│   │   └── orders.py               # 注文用のユースケースと保存処理の組み立て
│   ├── orders/                     # サブドメインの例
│   │   ├── presentation/
│   │   │   ├── router.py           # HTTPの受付・応答
│   │   │   └── schemas.py          # APIのリクエスト・レスポンスの型
│   │   ├── application/
│   │   │   ├── use_cases/
│   │   │   │   └── create_order.py # 注文作成の手順
│   │   │   ├── dto.py              # ユースケースの入力・出力の型
│   │   │   └── ports.py            # Unit of Workなど外部処理の契約
│   │   ├── domain/
│   │   │   ├── order.py            # 注文エンティティとその業務ルール
│   │   │   ├── value_objects.py    # 値オブジェクト
│   │   │   ├── services.py         # ドメインサービス（必要な場合）
│   │   │   ├── repositories.py     # 保存・取得の契約
│   │   │   └── exceptions.py       # 業務ルールに関する例外
│   │   └── infrastructure/
│   │       ├── repositories.py     # 保存・取得の具体的な実装
│   │       ├── unit_of_work.py     # トランザクションの開始・確定・取り消し
│   │       └── clients.py          # 外部APIへの接続（必要な場合）
│   └── shared/                     # サブドメイン共通処理
│       ├── presentation/           # 共通のHTTP処理
│       ├── application/            # 共通のユースケース支援処理・契約
│       ├── domain/                 # 共通の業務上の型・ルール
│       └── infrastructure/         # 設定の読み込み・DB接続・ログ設定など
└── tests/
    ├── orders/                     # 実装と同じサブドメイン・層で分類
    │   ├── presentation/
    │   ├── application/
    │   ├── domain/
    │   └── infrastructure/
    ├── shared/                     # 共通処理のテスト
    ├── bootstrap/                  # 組み立て処理のテスト
    └── integration/                # サブドメイン横断・アプリ全体の連携テスト
```

Pythonのパッケージとして扱う実装ディレクトリには `__init__.py` を置きます。図では省略しています。
図は配置先の例であり、使わないファイルや空の層は先に作りません。[No.9](data-storage.md)でPostgreSQLとSQLを明示する方針を選んだため、ORM用の `models.py` は設けません。SQLは `infrastructure/repositories.py` に記載し、長くなった場合は同じサブドメインの `infrastructure/sql/` へ分離します。外部APIは各機能で必要になった場合に選定します。

## 決定事項と理由

| 論点 | 決定内容と理由 |
| --- | --- |
| 各層内の分割 | 最初は役割ごとのファイルを基本にする。ユースケースは操作ごとにファイルを分け、実装の追加先を明確にする。 |
| 入出力の型 | HTTP用の `presentation/schemas.py` と、HTTPに依存しない `application/dto.py` を分ける。APIの都合を内側へ持ち込まないため。 |
| 契約と実装 | 保存・取得の契約は `domain/repositories.py`、具体的な実装は `infrastructure/repositories.py` に置く。ユースケース固有の外部処理の契約は `application/ports.py` に置く。 |
| 組み立て処理 | `app/bootstrap/` にサブドメインごとの組み立て処理を置く。`shared` に個別サブドメインへの依存を持たせないため。 |
| 共通処理 | `shared` の内部も4層で分類する。共通部品の責務と、どの層から参照できるかを判断しやすくするため。 |
| テスト | `app` の外の `tests` に置き、サブドメイン・層に対応させる。横断する連携テストは `tests/integration/` に置く。 |

DTOは処理の間でデータを受け渡すための型、portは外部処理へ依頼するための契約を指します。具体的な実装方法やライブラリはここでは決めません。
後続の決定に従い、DTOはNo.7のdataclass、契約はNo.5のProtocol、Unit of WorkはNo.9の配置を使います。設定読み込みは `shared/infrastructure/settings.py`、共通エラーハンドラーとHTTPログ処理は `shared/presentation/` に配置します。図は全ファイルを列挙するものではなく、詳細は各方針を参照してください。

## 配置するときの境界

- `bootstrap` は4層を接続する組み立て専用の場所で、業務を担当する5つ目の層ではありません。
- `main.py` とHTTPの入口から組み立て用の関数を利用します。`application`・`domain`・`infrastructure`・`shared` から `bootstrap` は参照しません。
- `presentation` で組み立て用の関数を使っても、DBの具体的な実装を直接呼び出す処理は置きません。
- `shared` の内部でも決定済みの依存方向を守り、個別サブドメインの内部は参照しません。
- ファイルが大きくなった場合は、同じ責務のパッケージへ分割します。例：`domain/value_objects.py` を `domain/value_objects/` に分ける。

依存管理ファイルは[No.3](versions-and-dependencies.md)で決定した内容を反映しています。依存性注入の仕組みと生成・破棄のタイミングは[No.5](composition.md)、Docker関連ファイルは[No.12](docker-compose.md)を参照してください。`compose.yaml`・`.env`・`.env.example` はリポジトリ直下に置きます。テストツールや実行方法は[No.13](testing.md)を参照してください。
