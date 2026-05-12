; R-C-001 anti: unchecked strcpy / strcat
;
; Matches calls to `strcpy(...)` and `strcat(...)` — the unbounded
; string functions. Idiomatic safe alternatives are `strlcpy`
; (BSD) / `strncpy` (with explicit termination) / `snprintf`.
;
; Linter equivalent: clang-tidy cert-str34-c; bugprone-unsafe-functions
; Citation: tier-e-findings.md Part 1 / C row 1
; Grammar: tree-sitter-c
; Status: UNVERIFIED — node names need confirmation against
;         tree-sitter-c node-types.json in v0.1.3 G-BASE pass.

(call_expression
  function: (identifier) @fn_name
  (#match? @fn_name "^(strcpy|strcat)$")) @anti.unchecked_strcpy
