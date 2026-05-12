; R-GO-004 anti: unwrapped error return `return nil, err`
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: wrapcheck; errorlint
; Citation: tier-e-findings.md Part 1 / Go row 5
; Grammar: tree-sitter-go
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match `return ..., err` where `err` is the raw identifier
; (not `fmt.Errorf("...: %w", err)`). Idiomatic alternative wraps
; with context.
;
; (return_statement
;   (expression_list
;     (_)
;     (identifier) @err_id)
;   (#eq? @err_id "err")) @anti.bare_err_return
