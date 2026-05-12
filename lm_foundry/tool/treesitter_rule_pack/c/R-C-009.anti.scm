; R-C-009 anti: memcpy between incompatible types
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: MISRA C2012 21.15
; Citation: tier-e-findings.md Part 1 / C row 2
; Grammar: tree-sitter-c
; Status: UNVERIFIED — requires type inspection of dst/src; v1
;         captures every memcpy and the runner narrows.
;
; Intent: match `memcpy(dst, src, n)` calls. The runner checks that
; dst and src have compatible underlying types.
;
; (call_expression
;   function: (identifier) @fn_name
;   (#eq? @fn_name "memcpy")) @anti.memcpy_candidate
