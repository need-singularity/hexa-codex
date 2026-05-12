; R-C-004 anti: sizeof on a pointer (mistaken for array)
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: clang-tidy bugprone-sizeof-expression
; Citation: tier-e-findings.md Part 1 / C row 9
; Grammar: tree-sitter-c
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match `sizeof(<var>)` where <var> is declared as a pointer
; (e.g. `char *p`). Requires type-info from the declaration; v1
; reports candidates and the runner narrows.
;
; (sizeof_expression
;   value: (identifier) @var_name) @anti.sizeof_candidate
