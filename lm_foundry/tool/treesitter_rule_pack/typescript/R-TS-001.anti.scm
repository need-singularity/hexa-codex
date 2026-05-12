; R-TS-001 anti: `any` type annotation
;
; Matches the predefined `any` type used in non-test code. The
; runner narrows by file path (skip `*.test.ts`, `*.spec.ts`).
;
; Linter equivalent: @typescript-eslint/no-explicit-any
; Citation: tier-e-findings.md Part 1 / TS row 1
; Grammar: tree-sitter-typescript (TS dialect)
; Status: UNVERIFIED — `any` node identity in tree-sitter-typescript
;         is typically `predefined_type` with text "any"; confirm v0.1.3.

(predefined_type) @any_t
(#eq? @any_t "any")
