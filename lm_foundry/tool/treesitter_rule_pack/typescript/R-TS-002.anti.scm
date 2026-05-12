; R-TS-002 anti: numeric enum with reverse mapping
;
; Matches `enum Name { A, B, C }` (numeric, no explicit values) —
; these get reverse-mapped at runtime, bloat bundles, and lose
; tree-shaking. Idiomatic alternative is a string literal union or
; `as const` object.
;
; Linter equivalent: @typescript-eslint/prefer-literal-enum-member;
;                    biome lint
; Citation: tier-e-findings.md Part 1 / TS row 2
; Grammar: tree-sitter-typescript (TS dialect)
; Status: UNVERIFIED — node names need confirmation.

(enum_declaration
  body: (enum_body
    (property_identifier))) @anti.numeric_enum
