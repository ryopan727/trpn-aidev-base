# 基本設計書：タスク管理

| 項目 | 内容 |
| --- | --- |
| サブドメイン | `tasks` |
| 文書の状態 | 決定済み |
| 要求仕様書 | [requirements.md](requirements.md) |
| データモデル | [data-model.md](data-model.md) |
| API仕様書 | [openapi.yaml](openapi.yaml) |
| 関連する技術方針 | [API共通方針](../../steering/api/README.md) |

## 1. 設計の対象・責務

TASK-REQ-001〜004を対象とする。tasksが登録・参照・完了とデータ保存を担当する。外部のHTTPクライアントから、同期のFastAPIを介してPostgreSQLを利用する。他サブドメインとの連携はない。

## 2. 機能一覧・要求との対応

| 機能ID | 機能 | 要求ID | API・operationId |
| --- | --- | --- | --- |
| TASK-FUNC-001 | 登録 | TASK-REQ-001 | `POST /api/v1/tasks` / `createTask` |
| TASK-FUNC-002 | 一覧 | TASK-REQ-002 | `GET /api/v1/tasks` / `listTasks` |
| TASK-FUNC-003 | 完了 | TASK-REQ-003 | `PATCH /api/v1/tasks/{task_id}` / `completeTask` |
| TASK-FUNC-004 | 1件取得 | TASK-REQ-004 | `GET /api/v1/tasks/{task_id}` / `getTask` |

以降、要求・受入条件・ルールの短縮IDはすべて `TASK-` 接頭辞を省略している。

## 3. 機能別の動作設計

正確な入出力と応答定義は[OpenAPI](openapi.yaml)を正とする。

| 機能 | 前提・正常時の流れと結果 | 整合性・設計理由 | 要求・受入条件 |
| --- | --- | --- | --- |
| FUNC-001 | タイトルを検証し、未完了タスクを保存して201で返す。`Location`に1件取得の相対URLを設定する。 | 登録を1トランザクションで確定してから応答。同名でも別IDで登録する。 | REQ-001、BR-001・002、AC-001・002・008 |
| FUNC-002 | 指定ページの全状態のタスクと全件数を200で返す。ページ指定省略時は共通の既定値を使う。 | 固定順序はBR-003。検索・絞り込み・並び順指定は受け付けない。 | REQ-002、BR-003、AC-003・004 |
| FUNC-003 | 対象を確認し、`status: completed`なら完了にして200で返す。既に完了でも成功。`{}`は現状を200で返す。 | 書き込みを1トランザクションで確定。同時操作でも完了を維持する。省略項目は変更しない共通PATCH方針を適用。 | REQ-003、BR-002、AC-005〜008 |
| FUNC-004 | 指定IDのタスクを200で返す。 | 登録時のLocationで参照可能にする。 | REQ-004、AC-001・007 |

| 失敗条件 | HTTP・エラーコード | データへの影響 |
| --- | --- | --- |
| 壊れたJSON | 400 `INVALID_JSON` | 変更なし |
| 必須・型・長さ・形式・範囲違反、未知の入力項目・クエリ | 400 `VALIDATION_ERROR` | 変更なし |
| ドメインでタイトル規則違反を検知 | 400 `INVALID_TASK_TITLE` | 変更なし。HTTP境界では先に入力検証する。 |
| 正しいUUID形式だが対象がない（取得・完了・空更新） | 404 `TASK_NOT_FOUND` | 変更なし |
| 想定外の保存障害・内部障害 | 500 `INTERNAL_ERROR` | 未確定の変更はrollback。commit済みの処理の応答送信障害は取り消せない。 |

ページは1以上、件数は1〜100（既定20）。一覧はオフセット方式で、並行登録をまたぐ複数の取得に同一スナップショットは保証しない。各リクエストの一覧と全件数は同じ対象集合を扱う。登録の自動再送による重複抑止は今回提供しない。

## 4. データの概念・関係

tasksがタスクの識別情報・作業名・状態・作成時点を所有する。概念ER図、論理スキーマ、項目の制約とAPIとの対応は [data-model.md](data-model.md) に定義する。

## 5. 状態・状態遷移

| 現在の状態 | 操作 | 次の状態・結果 |
| --- | --- | --- |
| 未登録 | 登録 | `pending`（未完了） |
| `pending` | 完了 | `completed`（完了） |
| `completed` | 完了 | `completed`のまま成功 |
| どちらも | 空オブジェクトで更新 | 現状のまま成功 |
| どちらも | `pending`・null・その他を更新値に指定 | 400、変更なし |

固定値の定義・参照先は[code-values.md](detailed-design/code-values.md)にまとめる。

## 6. 他サブドメイン・外部システムとの連携

業務上の連携なし。DBの接続・環境構成は[infrastructure.md](detailed-design/infrastructure.md)で扱う。

## 7. 非機能要求への対応方針

| 要求 | 対応方針・理由 | 詳細設計 |
| --- | --- | --- |
| TASK-NFR-001 | PostgreSQLの永続ボリュームと成功応答前のcommitにより、通常の停止・再起動後も保存結果を保持する。 | [architecture.md](detailed-design/architecture.md)、[testing.md](detailed-design/testing.md) |
| TASK-NFR-002 | 共通のログ・例外処理を適用し、タイトルをログ項目に加えない。 | [security.md](detailed-design/security.md) |

## 8. 未決定事項・確認事項

要求仕様のTASK-Q-001〜003は2026-11-16にユーザー承認済み。本書とOpenAPI、詳細設計は承認された内容。その他の業務判断の未決定事項はない。
