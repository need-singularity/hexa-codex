; R-C-001 positive: bounded string copy via strlcpy or snprintf
;
; Matches calls to `strlcpy(...)`, `strncpy(...)`, or `snprintf(...)`
; — the safe alternatives to strcpy/strcat.
;
; Grammar: tree-sitter-c
; Status: UNVERIFIED.

(call_expression
  function: (identifier) @fn_name
  (#match? @fn_name "^(strlcpy|strncpy|snprintf)$")) @positive.bounded_copy
