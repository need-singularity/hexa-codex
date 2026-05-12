; R-C-003 anti: malloc result dereferenced without NULL check
;
; Matches `<var> = malloc(...);` followed by a dereference of <var>
; without an intervening NULL check. v1 query captures the
; assignment shape; the runner cross-checks the next statement(s)
; for an `if (!<var>)` guard within the same scope.
;
; Linter equivalent: clang-tidy clang-analyzer-unix.Malloc
; Citation: tier-e-findings.md Part 1 / C row 3
; Grammar: tree-sitter-c
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

(declaration
  declarator: (init_declarator
    declarator: (identifier) @var_name
    value: (call_expression
      function: (identifier) @fn_name
      (#match? @fn_name "^(malloc|calloc|realloc)$")))) @anti.malloc_assign
