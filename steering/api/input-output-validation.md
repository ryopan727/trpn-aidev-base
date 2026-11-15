# 入出力・入力検証

状態：決定済み（2026-11-08）

公式情報の確認日：2026-11-08。以下の推奨方針を採用しました。選定時の比較も残しています。実装やパッケージの追加はまだ行いません。

## 1. 入出力モデル

| 項目 | 選択肢 | 採用方針と理由 |
| --- | --- | --- |
| APIの型・検証 | Pydantic／辞書を受け取り手動検証 | Pydanticを使う。型・必須項目・制約をモデルにまとめ、FastAPIの入力検証とAPI仕様の生成に利用する。 |
| モデルの用途 | 1つを使い回す／作成・更新・応答を分ける | `OrderCreateRequest`・`OrderUpdateRequest`・`OrderResponse` のように分ける。必須項目や公開項目の違いを明確にする。 |
| applicationのDTO | 通常のクラス／標準のdataclass／Pydantic | 標準の `dataclass` を使う。受け渡すデータを明記しつつ、API用モデルから独立させる。 |

API用モデルを `presentation/schemas.py`、ユースケースのDTOを `application/dto.py` に分ける方針はNo.2で決定済みです。APIモデル・DTO・ドメインモデルの変換は各境界で明示的に行い、入力モデルをそのままドメインやDBの更新に流し込みません。
API応答は公開する項目だけをモデルに定義し、FastAPIの `response_model` を使います。DBモデルや内部の例外情報を直接返しません。

参照：[FastAPIの入力モデル](https://fastapi.tiangolo.com/tutorial/body/)、[応答モデル](https://fastapi.tiangolo.com/tutorial/response-model/)、[Pythonのdataclass](https://docs.python.org/3/library/dataclasses.html)。標準のdataclass自体は、型に基づく実行時の入力検証を自動では行いません。

## 2. JSONの表現

| 項目 | 選択肢 | 採用方針と理由 |
| --- | --- | --- |
| 通常の入出力 | JSON／フォームなど | JSONを基本とする。ファイルアップロードなどは必要な機能で別途定義する。 |
| フィールド名 | `snake_case`／`camelCase` | Python側と揃う `snake_case`。例：`order_id`、`created_at`。 |
| 単件応答 | オブジェクトを直接返す／`data` で包む | オブジェクトを直接返す。必要のない共通の包みを増やさない。 |
| 一覧応答 | 配列だけ／データとページ情報を返す | `items`・`page`・`page_size`・`total` を持つオブジェクトを返す。ページ番号方式に合わせ、総ページ数を計算できるようにする。 |
| ID | JSONの数値／文字列 | 文字列を使う。クライアント側に数値の桁数や計算上の意味を持たせない。[No.9](data-storage.md)に従い、アプリ側でUUIDv4を生成し、DBでは `uuid` 型に保存する。 |
| 日時 | タイムゾーンなし／オフセット付き／数値のタイムスタンプ | RFC 3339形式のオフセット付き文字列を入力し、応答はUTCの `Z` 表記に揃える。例：`2026-11-08T09:00:00Z`。 |

日時はタイムゾーンなしの値や数値のタイムスタンプを受け付けません。Pydanticの既定の変換だけに任せず、入力形式の検証とUTCへの変換を明示します。[Pydanticの日時型](https://docs.pydantic.dev/latest/api/standard_library_types/#datetimes)を参照してください。時刻を持たない日付は `YYYY-MM-DD` とし、日時とは分けます。

一覧が空の場合の応答例です。No.6で決めたとおり、ステータスは `200` です。

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

`total` は、同じ絞り込み条件に一致する全件数です。総件数の取得には追加の処理が必要なため、規模が大きくなった際は一覧方式と合わせて見直します。`204` の削除応答には本文を付けません。

## 3. 必須・省略・null

「送信を省略できるか」と「値に `null` を指定できるか」は別に定義します。
作成時の必須項目には既定値を置かず、省略されたら入力エラーにします。省略可能な項目には、必要に応じて既定値を定めます。Pydanticで `T | None` と書くだけでは、省略可能になるとは限りません。[フィールドと既定値](https://docs.pydantic.dev/latest/concepts/fields/#default-values)を参照してください。

PATCHは次の意味に揃えます。

| 送信内容 | 意味 |
| --- | --- |
| 項目を省略 | 現在の値を変更しない。 |
| `{"note": null}` | `null` を許可する項目だけ、値を消す。 |
| `{"note": "変更後"}` | 指定した値に更新する。 |

例えば数量など `null` 不可の項目は、PATCHで省略できても明示的な `null` は拒否します。
`model_dump(exclude_unset=True)` などで送信された項目を取り出し、DTOへ変換した後も省略と明示的な `null` の区別を保持します。`exclude_none=True` では明示的な `null` も消えてしまうため、同じ目的には使いません。[FastAPIの部分更新](https://fastapi.tiangolo.com/tutorial/body-updates/)を参照してください。
応答では定義した項目を基本的に返し、値がない項目は仕様で許可した場合に `null` とします。PATCHの省略ルールをそのまま応答へ適用しません。

## 4. 入力検証の厳しさ

| 項目 | 選択肢 | 採用方針と理由 |
| --- | --- | --- |
| 未定義の入力項目 | 無視／許可／拒否 | リクエストの未定義項目は `extra="forbid"` で拒否する。綴りの間違いや更新できない項目の送信を見つけやすくする。 |
| 型変換 | 広く許可／全体を厳密にする／項目ごとに設定 | 項目ごとに設定する。JSONの整数・真偽値は厳密に検証し、URLのパス・クエリは文字列から宣言した型への変換を許可する。 |
| 値の制約 | 型だけ／値の範囲も定義 | 必須、文字数、数値の範囲、選択肢など、仕様で定まった制約をモデルへ記載する。 |

例えばJSONの整数に `"3"` や `true` が届いた場合は拒否し、クエリの `?page=3` は整数として解釈します。日時やIDの文字列を扱うため、全モデルへの一律のstrict設定はせず、フィールドごとに定義します。
`extra="forbid"` は入力用のモデルに適用し、ネストした入力モデルにも同じ方針を適用します。サーバーが発行する作成対象自身のIDや作成日時など、利用者が指定できない項目は作成・更新の本文モデルに含めません。更新対象を指定するパスのIDや、商品IDなど参照先のIDは、API仕様に応じて受け付けます。
クエリもPydanticのクエリモデルなどで受信した項目全体を検証し、未知のキーを400にします。個別のクエリ引数を宣言するだけでは未知のキーを拒否できません。この方針は業務APIの本文・クエリに適用し、一般的なHTTPヘッダーを一律に拒否するものではありません。[FastAPIのクエリモデル](https://fastapi.tiangolo.com/tutorial/query-param-models/#forbid-extra-query-parameters)を参照してください。

参照：[Pydanticのextra設定](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra)、[厳密な型検証](https://docs.pydantic.dev/latest/concepts/strict_mode/)。

## 5. 検証する層

決定済みのDDD方針に沿って、APIでは型・形式・必須項目を検証し、ドメインでは業務ルールを保証します。
例として、「数量が整数」はAPIで検証し、「注文数量は正数」「確定済みの注文は変更不可」はドメインでも保証します。既存データの取得などが必要な検証は、ユースケースがデータを揃えてドメインへ渡します。
APIの検証に成功したことだけを理由に、業務ルールの検証を省略しません。具体的なエラー本文とHTTPへの変換は[No.8](error-handling.md)に従います。
