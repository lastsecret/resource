# NullNode coercion / 3.1

Source: https://github.com/FasterXML/jackson-databind/issues/5558

Section: NullNode coercion / 3.1

Reviewed 2026-11-25. Original paraphrase; exact target patch and runtime not verified.

3.1 NullNode 的 asXxx(defaultValue) 回傳指定 fallback；3.0 會轉為空值或型別預設值。Opt 方法亦調整；無參數方法不變。

Verification: 確認實際 Jackson 3.0→3.1、NullNode 而非 MissingNode；2→3.1 不應假設與 3.0 相同，測試 fallback/Optional/無參數。
