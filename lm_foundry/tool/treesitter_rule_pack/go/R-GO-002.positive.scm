; R-GO-002 positive: explicit `err` check
;
; Matches `x, err := f()` followed by `if err != nil { ... }` in the
; same block. v1 captures the LHS shape only; the runner cross-checks
; for the sibling check pattern.
;
; Grammar: tree-sitter-go
; Status: UNVERIFIED.

(short_var_declaration
  left: (expression_list
    (_)
    (identifier) @err_var)
  (#eq? @err_var "err")) @positive.err_named_var
