# Removed @Columns

Source: https://docs.hibernate.org/orm/7.3/migration-guide/

Section: Removed @Columns

Reviewed 2026-11-25. Original paraphrase; exact target patch and runtime not verified.

Hibernate 自有 @Columns 已移除；不等同 JPA @Column。

Verification: 解析 annotation 型別，編譯及比對實際多欄位 mapping。
