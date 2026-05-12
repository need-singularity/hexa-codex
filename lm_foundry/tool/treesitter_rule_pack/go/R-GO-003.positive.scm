; R-GO-003 positive: return an error instead of panicking
;
; Matches `return ..., fmt.Errorf(...)` — the idiomatic alternative
; to a runtime panic.
;
; Grammar: tree-sitter-go
; Status: UNVERIFIED.

(return_statement
  (expression_list
    (call_expression
      function: (selector_expression
        operand: (identifier) @pkg_id
        field: (field_identifier) @method)
      (#eq? @pkg_id "fmt")
      (#eq? @method "Errorf")))) @positive.return_errorf
