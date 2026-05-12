; R-C-007 anti: ignored return value of fread / fwrite / write / read
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: clang-tidy bugprone-unused-return-value
; Citation: tier-e-findings.md Part 1 / C row 8
; Grammar: tree-sitter-c
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match an expression_statement whose entire expression is
; a call to fread/fwrite/read/write (return value not bound or
; checked).
;
; (expression_statement
;   (call_expression
;     function: (identifier) @fn_name
;     (#match? @fn_name "^(fread|fwrite|read|write)$"))) @anti.ignored_io_return
