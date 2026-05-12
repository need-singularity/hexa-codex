; R-TS-002 positive: string literal union type alias
;
; Matches `type Mode = "fast" | "slow";` — the idiomatic alternative
; to a numeric enum.
;
; Grammar: tree-sitter-typescript
; Status: UNVERIFIED.

(type_alias_declaration
  value: (union_type
    (literal_type
      (string)))) @positive.string_literal_union
