; R-GO-002 anti: ignoring an error with `_` (blank identifier)
;
; Matches short-variable declarations `x, _ := f()` and assignments
; `x, _ = f()` — discarding the error half is one of the highest-yield
; Go anti-patterns, with errcheck flagging it across the ecosystem.
;
; Linter equivalent: errcheck; errcheck-all
; Citation: tier-e-findings.md Part 1 / Go row 3
; Grammar: tree-sitter-go
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

; (a) short_var_declaration with blank identifier as second LHS
(short_var_declaration
  left: (expression_list
    (_)
    (identifier) @blank)
  (#eq? @blank "_")) @anti.err_discarded_short

; (b) assignment_statement form
(assignment_statement
  left: (expression_list
    (_)
    (identifier) @blank)
  (#eq? @blank "_")) @anti.err_discarded_assign
