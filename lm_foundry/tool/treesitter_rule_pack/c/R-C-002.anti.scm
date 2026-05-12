; R-C-002 anti: gets() call
;
; Matches every call to `gets(...)`. The function was removed from
; C11 and is a known unbounded-buffer attack vector. Severity `block`.
;
; Linter equivalent: CERT MSC24-C
; Citation: tier-e-findings.md Part 1 / C row 5
; Grammar: tree-sitter-c
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

(call_expression
  function: (identifier) @fn_name
  (#eq? @fn_name "gets")) @anti.gets_call
