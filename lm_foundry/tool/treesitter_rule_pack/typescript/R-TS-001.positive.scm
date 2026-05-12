; R-TS-001 positive: `unknown` type annotation (forces narrowing)
;
; Matches the predefined `unknown` type — the safer alternative
; that the language team explicitly recommends over `any`.
;
; Grammar: tree-sitter-typescript
; Status: UNVERIFIED.

(predefined_type) @unknown_t
(#eq? @unknown_t "unknown")
