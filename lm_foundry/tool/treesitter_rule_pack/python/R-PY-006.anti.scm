; R-PY-006 anti: C-style string concat in loop (s += str(x))
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: perflint PERF401 / PERF402
; Citation: tier-e-findings.md Part 1 / Python row 6
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node name `augmented_assignment` needs confirmation.
;
; Intent: match `+=` on a string-typed variable inside a for-loop.
; Idiomatic positive is `"".join(...)`.
;
; (for_statement
;   body: (block
;     (augmented_assignment
;       left: (identifier) @s_var
;       operator: "+="
;       right: (_)))) @anti.string_concat_in_loop
