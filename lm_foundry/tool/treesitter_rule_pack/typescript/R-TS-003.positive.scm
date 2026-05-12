; R-TS-003 positive: type guard / type predicate function
;
; Matches a function whose return type is a type predicate
; `arg is T` — the idiomatic alternative to a forced cast.
;
; Grammar: tree-sitter-typescript
; Status: UNVERIFIED.

(function_declaration
  return_type: (type_annotation
    (type_predicate))) @positive.type_guard
