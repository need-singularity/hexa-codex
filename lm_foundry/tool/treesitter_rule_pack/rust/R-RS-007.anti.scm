; R-RS-007 anti: `String` parameter where `&str` suffices
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: clippy ptr_arg; needless_pass_by_value
; Citation: tier-e-findings.md Part 1 / Rust row 10
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match function parameter of type `String` whose body
; never mutates the String. Detecting non-mutation requires data-flow
; analysis; v1 query captures only the parameter shape and reports
; with a `warn` severity — runner heuristic narrows from there.
;
; (function_item
;   parameters: (parameters
;     (parameter
;       type: (type_identifier) @ty
;       (#eq? @ty "String")))) @anti.string_param
