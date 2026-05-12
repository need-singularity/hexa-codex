; R-C-003 positive: malloc followed by NULL check
;
; Matches an `if (!<var>) { return ...; }` or `if (<var> == NULL)`
; pattern. v1 captures the guard shape; runner cross-checks that
; the guarded variable is the one just assigned from malloc.
;
; Grammar: tree-sitter-c
; Status: UNVERIFIED.

(if_statement
  condition: (parenthesized_expression
    (unary_expression
      operator: "!"
      argument: (identifier) @guard_var))) @positive.null_check_bang
