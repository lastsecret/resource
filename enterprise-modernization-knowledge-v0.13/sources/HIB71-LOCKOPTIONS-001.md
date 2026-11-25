# LockOptions

Source: https://docs.hibernate.org/orm/7.1/migration-guide/

Section: LockOptions

Reviewed 2026-11-25. Original paraphrase; exact target patch and runtime not verified.

LockOptions 的部分常數及 alias-specific lock mode API 已移除；其他 API 可能僅 deprecated。

Verification: 確認精確符號及鎖語意；測試鎖模式、timeout、交易與 SQL。
