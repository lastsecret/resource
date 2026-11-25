# HQL current date and local date on Oracle

Source: https://docs.hibernate.org/orm/7.4/migration-guide/

Section: HQL current date and local date on Oracle

Reviewed 2026-11-25. Original paraphrase; exact target patch and runtime not verified.

Oracle 方言下 HQL current date / local date 現翻譯為 trunc(current_date)，時間部分歸零；不等於 JDBC DATE mapping 變更。

Verification: 確認 Oracle dialect、HQL 非 native SQL、比較日期值及 generated SQL。
