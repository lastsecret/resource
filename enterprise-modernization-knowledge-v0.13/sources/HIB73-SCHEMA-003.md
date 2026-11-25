# Schema actions now executed even without mapped entities

Source: https://docs.hibernate.org/orm/7.3/migration-guide/

Section: Schema actions now executed even without mapped entities

Reviewed 2026-11-25. Original paraphrase; exact target patch and runtime not verified.

無 mapped entity 的 persistence unit 也會執行明確設定的 schema actions，可能執行以前被忽略的 import.sql。

Verification: 隔離 DB 檢查 entity 數、DDL、import.sql；禁止直接對正式 DB 執行。
