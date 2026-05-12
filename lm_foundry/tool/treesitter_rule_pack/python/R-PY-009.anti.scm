; R-PY-009 anti: string-typed pseudo-enum
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: partial via ruff PLR2004 (magic value)
; Citation: tier-e-findings.md Part 1 / Python row 10
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — heuristic; severity is `info`.
;
; Intent: match module-level assignments of the form
; `MODE = "value"` where the comment or doc-string suggests a
; discrete set ("or" pattern). Best matched at the runner level
; by scanning for comments like `# or "slow"` adjacent to a string
; literal assignment. This .scm captures the assignment shape.
;
; (module
;   (expression_statement
;     (assignment
;       left: (identifier) @const_name
;       right: (string) @const_value))) @anti.string_pseudo_enum
