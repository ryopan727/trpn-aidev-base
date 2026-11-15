# コーディング規約

状態：決定済み（2026-11-08）

今回は使用ツールと命名規則を定めます。

## 使用ツール

- コード整形・lint：**Ruff**
- 型チェック：**mypy**
- No.3の方針に従い、uvの開発用依存として管理します。具体的なバージョンは導入時に最新安定版を確認して固定します。

## 命名規則

PEP 8を基本に、次の命名を採用します。

| 対象 | 規則 | 例 |
| --- | --- | --- |
| 関数・変数・ファイル | `snake_case` | `create_order`、`order_id`、`create_order.py` |
| クラス | `PascalCase` | `Order`、`CreateOrderUseCase` |
| 定数 | `UPPER_SNAKE_CASE` | `MAX_ORDER_QUANTITY` |

業務用語は英語の識別子で統一します。

## 今回定めない項目

整形の細かな設定、importの書き方、型ヒントの必須範囲、コメント・docstringの規約、検査の厳しさについては、追加の取り決めを設けません。先に提示した詳細規約の案は採用済みとして扱いません。
後続で決定した実行方法は、TaskからRuff・mypyを呼び出し、対象パスと呼び出し方を各領域の `operations.md` に記載するものです。[specsの実行手順](../../specs/README.md)と[AI駆動開発の進め方](../aidd/README.md)を参照します。これは検査の厳しさや新しい詳細規約を追加するものではありません。

ツールの導入や設定ファイルの作成はまだ行っていません。

参照：[PEP 8](https://peps.python.org/pep-0008/)、[Ruff](https://docs.astral.sh/ruff/)、[mypy](https://mypy.readthedocs.io/en/stable/)。
