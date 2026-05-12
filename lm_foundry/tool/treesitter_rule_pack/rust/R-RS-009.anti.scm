; R-RS-009 anti: `if let Some(x) = opt { x } else { default }`
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: clippy manual_unwrap_or; option_if_let_else
; Citation: tier-e-findings.md Part 1 / Rust row 6
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match `if let Some(x) = opt { x } else { default }` shape.
; Idiomatic alternative is `opt.unwrap_or(default)` or
; `opt.unwrap_or_else(|| default)`.
;
; (if_expression
;   condition: (let_condition
;     pattern: (tuple_struct_pattern
;       type: (identifier) @some_id
;       (#eq? @some_id "Some")))
;   consequence: (block (identifier))
;   alternative: (else_clause
;     (block))) @anti.if_let_some_else_default
