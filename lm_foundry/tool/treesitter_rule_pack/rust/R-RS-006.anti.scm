; R-RS-006 anti: `match` with single non-wildcard arm + `_ => ()`
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: clippy single_match
; Citation: tier-e-findings.md Part 1 / Rust row 9
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match `match x { Pat => body, _ => () }` shape. Idiomatic
; alternative is `if let Pat = x { body }`.
;
; (match_expression
;   body: (match_block
;     (match_arm
;       pattern: (match_pattern (_)))
;     (match_arm
;       pattern: (match_pattern (_) @wildcard)
;       value: (unit_expression))
;     (#eq? @wildcard "_"))) @anti.single_match_unit
