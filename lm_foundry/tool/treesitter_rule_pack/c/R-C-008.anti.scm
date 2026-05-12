; R-C-008 anti: upward goto (loop emulation)
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: CERT MEM12-C (manual)
; Citation: tier-e-findings.md Part 1 / C row 7
; Grammar: tree-sitter-c
; Status: UNVERIFIED — direction-of-jump needs runner-level scan.
;
; Intent: match `goto <label>;` where <label> appears earlier in the
; same function body (upward jump). Idiomatic C reserves `goto`
; for forward-only cleanup (`goto cleanup;`). v1 captures every
; goto and the runner classifies upward vs forward.
;
; (goto_statement
;   label: (statement_identifier) @lbl) @anti.goto_any
