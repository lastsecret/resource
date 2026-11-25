# Registry Generic Signatures

Source: https://docs.hibernate.org/orm/7.2/migration-guide/

Section: Registry Generic Signatures

Reviewed 2026-11-25. Original paraphrase; exact target patch and runtime not verified.

TypeConfiguration、JavaTypeRegistry、BasicTypeRegistry 部分泛型簽名收緊；自訂 SPI 可能編譯不相容。

Verification: 編譯實際 SPI 使用者，確認泛型與型別映射。
