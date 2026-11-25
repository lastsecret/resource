# Result deduplication

Source: https://docs.hibernate.org/orm/7.3/migration-guide/

Section: Result deduplication

Reviewed 2026-11-25. Original paraphrase; exact target patch and runtime not verified.

getSingleResult / getSingleResultOrNull 遇多個結果時一致拋錯；既有重複結果可能不再被消除。

Verification: 測試零、一、重複及不同結果；只在原契約要求時評估去重。
