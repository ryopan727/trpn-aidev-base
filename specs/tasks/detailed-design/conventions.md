# 実装上の取り決め：タスク管理

文書の状態：決定済み

## 1. 適用する共通方針

[DDD4層](../../../steering/api/architecture.md)、[同期処理・DI](../../../steering/api/composition.md)、[入力検証](../../../steering/api/input-output-validation.md)、[データ保存](../../../steering/api/data-storage.md)、[コーディング規約](../../../steering/api/coding-conventions.md)を適用する。

## 2. 領域固有の取り決め

| 対象 | 守ること |
| --- | --- |
| タイトル | TASK-BR-001をdomainでも保証する。presentationで入力不備を先に検出し、勝手なtrimや型変換をしない。 |
| 完了 | 状態変更は未完了→完了のみ。同時の完了操作でも成功し、タイトル・ID・作成日時を変えない。 |
| 保存 | 書き込みのcommitはapplicationのUnit of Work経由。Repository単位でcommitしない。 |
| 一覧 | TASK-BR-003の順序を守る。全件数とitemsに同じ対象条件を使う。 |
| PATCH | 項目の省略とnullを区別する。省略は変更なし、nullは400。 |

## 3. 判断理由

タイトルと状態のルールをdomainへ集め、HTTP以外からの利用でも保持する。単方向の完了操作を繰り返せるため、再操作を競合エラーにしない。作成日時にIDを加えて順序を決め、同時刻のデータでもページ分割を安定させる。具体的なクラス数・SQL・呼び出し手順は実装時に決める。

## 4. 未決定事項

[要求仕様](../requirements.md)のTASK-Q-001〜003は2026-11-16にユーザー承認済み。独自の追加確認事項はない。
