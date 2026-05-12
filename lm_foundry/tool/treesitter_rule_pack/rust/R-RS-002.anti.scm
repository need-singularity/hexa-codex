; R-RS-002 anti: .unwrap() on a Result in library code
;
; Matches calls of the form `expr.unwrap()` and `expr.expect(...)`.
; The runner narrows these to library code by checking file path
; (`!main.rs`, `!tests/*`, `!benches/*`, `!examples/*`).
;
; Linter equivalent: clippy unwrap_used; clippy expect_used (restriction)
; Citation: tier-e-findings.md Part 1 / Rust row 1
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

(call_expression
  function: (field_expression
    field: (field_identifier) @method_name)
  (#match? @method_name "^(unwrap|expect)$")) @anti.unwrap_or_expect
