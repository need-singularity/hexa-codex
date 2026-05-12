; R-RS-002 positive: `?` operator for Result propagation
;
; Matches the try-operator expression. Canonical Rust error
; propagation in library code.
;
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node name `try_expression` needs confirmation.

(try_expression) @positive.question_mark
