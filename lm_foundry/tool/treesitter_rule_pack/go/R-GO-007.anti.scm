; R-GO-007 anti: unnecessary `else` after `return`
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: revive indent-error-flow; golint
; Citation: tier-e-findings.md Part 1 / Go row 9
; Grammar: tree-sitter-go
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match `if cond { return ... } else { ... }` — Go convention
; is to flatten: `if cond { return ... }` then the rest.
;
; (if_statement
;   consequence: (block
;     (return_statement) .)
;   alternative: (block)) @anti.unnecessary_else
