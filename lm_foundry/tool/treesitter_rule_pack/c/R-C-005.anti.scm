; R-C-005 anti: strlen() inside loop condition
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: (partial) clang-tidy bugprone-narrowing-conversions
; Citation: tier-e-findings.md Part 1 / C row 4
; Grammar: tree-sitter-c
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match a for-loop whose condition contains a call to strlen()
; — wasteful (recomputed each iteration) and signedness-incorrect
; (`int i` vs `size_t`). Idiomatic alternative is to hoist the
; length out of the loop.
;
; (for_statement
;   condition: (_
;     (call_expression
;       function: (identifier) @fn_name
;       (#eq? @fn_name "strlen")))) @anti.strlen_in_for
