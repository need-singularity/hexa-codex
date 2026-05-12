; R-C-010 anti: signed integer overflow assumed to wrap
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: UB sanitiser; CERT INT32-C
; Citation: tier-e-findings.md Part 1 / C row 10
; Grammar: tree-sitter-c
; Status: UNVERIFIED — heuristic; severity is `warn`.
;
; Intent: match arithmetic on signed-int types with constants that
; risk overflow (e.g. INT_MAX + 1). Full detection needs value-range
; analysis; v1 captures the literal `INT_MAX` / `INT_MIN` and the
; runner narrows.
;
; (binary_expression
;   left: (identifier) @lhs
;   operator: ["+" "-" "*"]
;   right: (_)
;   (#match? @lhs "^(INT_MAX|INT_MIN|LONG_MAX|LONG_MIN)$")) @anti.signed_overflow_candidate
