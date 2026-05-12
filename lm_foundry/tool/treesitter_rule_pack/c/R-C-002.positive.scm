; R-C-002 positive: fgets with explicit size
;
; Matches `fgets(buf, sizeof buf, stdin)` (or any sized fgets call)
; — the canonical safe replacement for gets().
;
; Grammar: tree-sitter-c
; Status: UNVERIFIED.

(call_expression
  function: (identifier) @fn_name
  (#eq? @fn_name "fgets")) @positive.fgets_call
