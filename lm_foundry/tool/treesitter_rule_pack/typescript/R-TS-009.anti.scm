; R-TS-009 anti: barrel index.ts using `export * from "./x"`
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: (manual; some custom plugins exist)
; Citation: tier-e-findings.md Part 1 / TS row 10
; Grammar: tree-sitter-typescript (TS dialect)
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match `export * from "..."` re-export statements. Encourages
; explicit named exports for tree-shakeability.
;
; (export_statement
;   "*"
;   source: (string)) @anti.barrel_export_star
